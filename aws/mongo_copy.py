#!/usr/bin/env python

import boto, time
from random import choice
from string import ascii_uppercase, digits
from fabric.api import *
from fabric.exceptions import *
from fabric.colors import red, green, yellow
from fabric.contrib import files


AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None
APPLY_ONLY = ['mongodb-0.stage.project.int', 'mongodb-1.stage.project.int', 'mongodb-2.stage.project.int']
VOLUME_TAGS = {'tag:backup': 'project-mongo-prod'}
INSTANCE_TAGS = {'tag:env': 'stage', 'tag:appname': 'project', 'tag:role': 'mongodb'}
SNAP_COUNTER = -1 # -1 means the most recent, -2 one step older etc..
DEBUG = True
MOUNT_POINT = '/data'
MONGO_PATH = '/data/mongo'
MONGO_USER = 'mongod'
DRY = False
DELETEOLD = True
SLEEP = 120
VOLUME_DEFAULTS = {
    'dev_path_int': '/dev/xvdg',
    'dev_path_ext': '/dev/sdg',
    'volume_size': 600,
    'volume_iops': 6000,
    'volume_type': 'io1',
    'vg_name': 'data'
}
KEYFILE = '''
'''
KEYFILE_PATH = '/data/mongo/mongodb-keyfile'
OLD_RSNAME = 'project-prod'
NEW_RSNAME = 'project-stage'
RS_RENAME = '''
var cfg=db.system.replset.findOne()
cfg._id='%s'
db.system.replset.insert(cfg)
db.system.replset.remove({_id: '%s'})
db = db.getSiblingDB('local')
db.me.insert({host: '%s'})
db.me.remove({host: 'mongodb-2.prod.project.int'})
'''
ADD_USERS = '''
db = db.getSiblingDB('admin')
db.runCommand( { dropAllUsersFromDatabase: 1 } )
db.createUser( { user: 'admin', pwd: 'project-stage-admin', roles: [ { role: 'root', db: 'admin' } ] } )
db.createUser( { user: 'project', pwd: 'project-stage', roles: [ { role: 'clusterMonitor', db: 'admin' }, { role: 'readAnyDatabase', db: 'admin' } ] } )
db = db.getSiblingDB('project')
db.runCommand( { dropAllUsersFromDatabase: 1 } )
db.createUser( { user: 'project', pwd: 'project-stage', roles: [ { role: 'dbAdmin', db: 'project' }, { role: 'readWrite', db: 'project' } ] } )
'''


def connect():
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        conn = boto.connect_ec2( aws_access_key_id=AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    else:
        conn = boto.connect_ec2()
    return conn


def getinstances(conn):
    instances = [r.instances[0] for r in conn.get_all_instances(filters=INSTANCE_TAGS)]
    instances = filter(lambda x: x.state == 'running', instances)
    if DEBUG:
        print 'Found {0} running instances:'.format(len(instances))
        for instance in instances:
            print '\t' + instance.tags['Name']
    return instances


class Instance(object):
    def __init__(self, conn, instance):
        self.conn = conn
        self.instance = instance

    def getNameIp(self):
        self.ip = self.instance.private_ip_address
        self.name = self.instance.tags['Name']

    def checkInstanceConn(self):
        env.use_ssh_config = True
        if DEBUG: print green('Checking ssh access to {0}...'.format(self.name)),
        try:
            with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only = True, host_string = self.ip):
                run('hostname')
        except Exception as e:
            raise
        if DEBUG: print green(' works!')
        self.ok = True


    def getVolumeInfo(self):
        try:
            self.old_volume_id = self.instance.block_device_mapping[VOLUME_DEFAULTS['dev_path_ext']].volume_id
        except KeyError:
            self.old_volume_id = None


    def mongoProcess(self, stop=None, start=None):
        env.use_ssh_config = True
        try:
            # with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only = True, host_string = self.ip):
            with settings(warn_only = True, host_string = self.ip):
                if start:
                    if not DRY:
                        sudo('systemctl start mongod')
                elif stop:
                    if not DRY:
                        sudo('systemctl stop mongod')
        except Exception as e:
            raise


    def oldVolumeDetach(self):
        env.use_ssh_config = True
        try:
            with settings(warn_only = True, host_string = self.ip):
                if not DRY and self.old_volume_id:
                    sudo('umount {0}'.format(MOUNT_POINT))

                    ## comment out old record in fstab
                    uuid = sudo('lsblk -l -o NAME,UUID,MOUNTPOINT |grep "{0}" | cut -f2 -d" "'.format(MOUNT_POINT))
                    if len(uuid) == 36:
                        files.comment('/etc/fstab', 'UUID={0}.*'.format(uuid), use_sudo=True, char='# ')
                    sudo('vgchange -an {0}'.format(VOLUME_DEFAULTS['vg_name']))

                    volume = self.conn.get_all_volumes(volume_ids=(self.old_volume_id))[0]
                    volume.detach()

                    if DELETEOLD:
                        n = 0
                        while n < SLEEP:
                            try:
                                volume.delete()
                                break
                            except boto.exception.EC2ResponseError:
                                n += 10
                                time.sleep(10)
                                continue
                        return

                    volume.add_tags({'instance': self.name, 'date': time.strftime('%Y-%m-%d-%H:%M')})
        except Exception as e:
            raise


    def newVolumeAttach(self, snapshot):
        zone = self.instance.placement
        
        try:
            volume = self.conn.create_volume(VOLUME_DEFAULTS['volume_size'], zone, snapshot=snapshot, 
                volume_type=VOLUME_DEFAULTS['volume_type'], iops=VOLUME_DEFAULTS['volume_iops'])
        except boto.exception.EC2ResponseError:
            print red('Error creating volume for {0}'.format(self.name))
            return
        print green('Created new volume {0}'.format(volume.id))
        print green('Attaching... '),

        n = 0
        res = 0
        while n < SLEEP:
            try:
                res = volume.attach(self.instance.id, device=VOLUME_DEFAULTS['dev_path_ext'])
                break
            except boto.exception.EC2ResponseError:
                n += 10
                time.sleep(10)
                continue
        volume.add_tags({'instance': self.name})
        
        if res:
            print green('attached new volume {0}'.format(volume.id))
        else:
            print red('attachment of volume {0} failed'.format(volume.id))


    def mountVolume(self):
        env.use_ssh_config = True

        try:
            with settings(hide('warnings', 'stderr'), warn_only = True, host_string = self.ip):
                if not DRY:
                    sudo('vgchange -ay data')
                    time.sleep(10)
                    uuid, fstype = sudo('blkid |grep "mapper/data" |cut -f2,3 -d" "').split()
                    fstype = fstype.split('"')[1]
                    files.append('/etc/fstab', '{0}\t{1}\t{2}\tnoatime\t0\t0'.format(uuid, MOUNT_POINT, fstype), 
                        use_sudo=True)
                    sudo('mount {0}'.format(MOUNT_POINT))
                if DEBUG:
                    print 'Mounted {0} on {1}'.format(MOUNT_POINT, self.name)
        except Exception as e:
            raise


    def renameRS(self):
        tmpfile = '/tmp/' + ''.join(choice(ascii_uppercase + digits) for _ in range(10))
        env.use_ssh_config = True
        try:
            with settings(hide('warnings', 'stderr'), warn_only = True, host_string = self.ip):
                if not DRY:
                    # sudo('cp /root/.mongorc.js {0}'.format(tmpfile))
                    files.append(tmpfile, RS_RENAME % (NEW_RSNAME, OLD_RSNAME, self.name), use_sudo=True)
                    sudo('mongo 127.1:27017/local {0}'.format(tmpfile))
                    sudo('rm -f {0}'.format(tmpfile))
                if DEBUG:
                    print 'Run eval on %s' % self.name
        except Exception as e:
            raise


    def addUsers(self):
        tmpfile = '/tmp/' + ''.join(choice(ascii_uppercase + digits) for _ in range(10))
        env.use_ssh_config = True
        try:
            with settings(hide('warnings', 'stderr'), warn_only = True, host_string = self.ip):
                if not DRY:
                    files.append(tmpfile, ADD_USERS)
                    sudo('mongo 127.1:27017/local {0}'.format(tmpfile))
                    sudo('rm -f {0}'.format(tmpfile))
                if DEBUG:
                    print 'Run eval on %s' % self.name
        except Exception as e:
            raise


    def resetOwner(self):
        env.use_ssh_config = True
        try:
            with settings(warn_only = True, host_string = self.ip):
                if not DRY:
                    sudo('chown -R {0}:{0} {1}'.format(MONGO_USER, MONGO_PATH))
                    sudo('restorecon -Rv {0}'.format(MONGO_PATH))
        except Exception as e:
            raise


    def putKeyfile(self):
        env.use_ssh_config = True
        try:
            with settings(warn_only = True, host_string = self.ip):
                if not DRY:
                    if not files.exists(KEYFILE_PATH, use_sudo=True):
                        files.append(KEYFILE_PATH, KEYFILE, use_sudo=True)
                        sudo('chmod 400 %s' % KEYFILE_PATH)
        except Exception as e:
            raise


    def switchRS(self, enabled=None, disabled=None):
        env.use_ssh_config = True
        try:
            with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only = True, host_string = self.ip):
                if disabled:
                    if not DRY:
                        files.comment('/etc/mongod.conf', '.*replSetName\:.*', use_sudo=True, backup='.bak')
                        files.comment('/etc/mongod.conf', '.*security\:.*', use_sudo=True, backup='')
                        files.comment('/etc/mongod.conf', '.*authorization\:.*', use_sudo=True, backup='')
                        files.comment('/etc/mongod.conf', '.*keyFile\:.*', use_sudo=True, backup='')
                    print 'Disabled replicaset in config on %s' % self.name
                elif enabled:
                    if not DRY:
                        sudo('mv /etc/mongod.conf.bak /etc/mongod.conf')
                    print 'Enabled replicaset in config on %s' % self.name
        except Exception as e:
            raise


    def manageVolume(self, snapshot):
        self.getNameIp()
        self.checkInstanceConn()
        self.getVolumeInfo()

        if not self.name in APPLY_ONLY:
            print red('Host %s is not listed in APPLY_ONLY, skipping' % self.name)
            return

        if DEBUG:
            print 'Volume id: %s' % self.old_volume_id

        self.mongoProcess(stop=True)
        self.oldVolumeDetach()
        self.newVolumeAttach(snapshot=snapshot)
        self.mountVolume()

    def prepareMongo(self):
        if not self.name in APPLY_ONLY:
            print red('Host %s is not listed in APPLY_ONLY, skipping' % self.name)
            return
        self.putKeyfile()
        self.resetOwner()
        self.switchRS(disabled=True)
        self.mongoProcess(start=True)
        self.renameRS()
        self.addUsers()
        self.mongoProcess(stop=True)
        self.switchRS(enabled=True)
        self.mongoProcess(start=True)


def getRecentSnapshot(conn):
    snapshots = filter( lambda x: x.status == 'completed', conn.get_all_snapshots(filters=VOLUME_TAGS))
    if DEBUG:
        for snap in snapshots:
           print snap.id, snap.start_time
    recent_snap = sorted( [(s.id, s.start_time) for s in snapshots ], key=lambda k: k[1] )[SNAP_COUNTER]
    if DEBUG: print red('* found snapshot {0} created at {1}'.format(*recent_snap))
    return recent_snap[0]


def main():
    conn = connect()
    snapshot = getRecentSnapshot(conn)

    instances = []

    for instance in getinstances(conn):
        instances.append(Instance(conn, instance))

    map( lambda instance: instance.manageVolume(snapshot), instances ) 
    map( lambda instance: instance.prepareMongo(), instances ) 


if __name__ == '__main__':
    main()
