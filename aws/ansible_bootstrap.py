#!/usr/bin/env python

import boto.utils, boto.ec2, boto.sns
from ansible.playbook import PlayBook
from ansible import callbacks
from ansible import utils
from git import Git, Repo                     # pip install gitpython
from os import unlink, path, system
from shutil import rmtree
from urllib2 import urlopen


AWS_ACCESS_KEY_ID = ""  # FIXME
AWS_SECRET_ACCESS_KEY = ""  # FIXME
SNS_ARN = ''  # FIXME
KEYPASS = '/root/keypass'
ANSIBLE_REPO = 'ssh://git@..'
REPO_PARENT = '/root'
PLAYBOOK = 'playbooks/local_{0}.yml'
DOMAIN = 'project.int'
HOSTNAME_PATTERN = '{0}-{1}'  # node role, last 2 octets
META_URL = 'http://169.254.169.254/latest/meta-data/local-ipv4'


def tagValue(aws_access_key_id, aws_secret_access_key):
    ''' Retrieves 'role' tag value of current instance '''
    instance_metadata = boto.utils.get_instance_metadata(timeout=1, num_retries=10)
    region = instance_metadata['placement']['availability-zone'][:-1]
    instance_id = instance_metadata['instance-id']

    conn = boto.ec2.connect_to_region(region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    try:
        role = filter(lambda x: x.name == 'role', conn.get_all_tags(filters={'resource-id': instance_id}))[0].value
    except:
        role = ''

    try:
        env = filter(lambda x: x.name == 'env', conn.get_all_tags(filters={'resource-id': instance_id}))[0].value
    except:
        env = ''

    try:
        project = filter(lambda x: x.name == 'appname', conn.get_all_tags(filters={'resource-id': instance_id}))[0].value
    except:
        project = ''

    try:
        ansible_branch = filter(lambda x: x.name == 'ansible_branch', conn.get_all_tags(filters={'resource-id': instance_id}))[0].value
    except:
        ansible_branch = ''

    return role, env, project, ansible_branch, instance_id


def getTags(aws_access_key_id, aws_secret_access_key, timeout=300):
    ''' Sometime instance tags become available only after few minutes after instance start '''
    from time import sleep
    pause = 5 # wait 5 seconds between retries

    for i in range(0, timeout/pause):
        role, env, project, ansible_branch, instance_id = tagValue(aws_access_key_id, aws_secret_access_key)
        if role and env and project:
            break
        print "Empty tags received. project: {0}, env: {1}, role: {2}. Sleep for {3} seconds, timeout {4} seconds.".format(project, env, role, pause, timeout-pause*i)
        sleep(pause)

    if not role:
        raise Exception("Required tag 'role' not found")

    return role, env, project, ansible_branch, instance_id


def snsPublish(aws_access_key_id, aws_secret_access_key, arn, message, subject):
    instance_metadata = boto.utils.get_instance_metadata(timeout=1, num_retries=10)
    region = instance_metadata['placement']['availability-zone'][:-1]

    boto.connect_sns(aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)
    sns_conn = boto.sns.connect_to_region(region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)
    sns_conn.publish(arn, message, subject)


def readPassword(path):
    try:
        with open(path, 'r') as f:
            return f.readline().strip()
    except:
        return None


def sethostname(role, env):
    try:
        octets = ''.join(urlopen(META_URL).read().split('.')[-2:])
    except:
        octets = '0000'

    hostname = '.'.join(filter( lambda x: x != '', (HOSTNAME_PATTERN.format(role, octets), env, DOMAIN) ))
    try:
        system('hostnamectl set-hostname ' + hostname)
    except Exception as e:
        print str(e)



def renderInventoryFile(role, env):
    import jinja2
    from tempfile import NamedTemporaryFile

    inventory = """[{{ env }}]
127.0.0.1
"""
    inventory_template = jinja2.Template(inventory)
    rendered_inventory = inventory_template.render({
        'env': env
    })

    # Create a temporary file and write the template string to it
    hosts = NamedTemporaryFile(delete=False)
    hosts.write(rendered_inventory)
    hosts.close()

    print rendered_inventory

    return hosts.name


def main():
    try:
        role, env, project, ansible_branch, instance_id = getTags(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

        sethostname(role, env)


        Git(REPO_PARENT).clone(ANSIBLE_REPO)

        ansible_branch = ansible_branch if ansible_branch else env  # just safe defaults
        repo = Repo(REPO_PARENT+'/project')
        repo.git.checkout(ansible_branch)
        for subm in repo.submodules:
            subm.update()

        utils.VERBOSITY = 0
        playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
        stats = callbacks.AggregateStats()
        runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
        host_list_file = renderInventoryFile(role, env)

        pb = PlayBook(playbook=path.join(REPO_PARENT, project, PLAYBOOK.format(role)), host_list=host_list_file, \
             callbacks=playbook_cb, runner_callbacks=runner_cb, stats=stats, vault_password=readPassword(KEYPASS))

        report = pb.run()

        if report['127.0.0.1']['failures'] > 0:
            snsPublish(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SNS_ARN,
                report,
                'project-{}: bootstrap error at {} ({})'.format(env, instance_id, role)
    except:
        import traceback
        snsPublish(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SNS_ARN,
            traceback.format_exc(),
            'project-{}: bootstrap error at {} ({})'.format(env, instance_id, role)
        pass

    unlink(KEYPASS)
    unlink('/root/.ssh/key')
    rmtree(path.join(REPO_PARENT, project))
    unlink(path.abspath(__file__))


if __name__ == '__main__':
    main()
