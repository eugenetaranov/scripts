#!/usr/bin/env python

from pymongo import MongoClient, ReadPreference
from argparse import ArgumentParser
from pymongo.errors import *
from datetime import datetime
from time import sleep, time

MONGODB_URI = ''
MONGODB_USER_RW = ''
MONGODB_PASSWORD_RW = ''
MONGODB_USER_CM = ''
MONGODB_PASSWORD_CM = ''
TIMEOUT = 60
WAIT = 6


def parseargs():
    p = ArgumentParser()
    p.add_argument('--rw', required=False, action='store_true', help='Check replication by writing/reading')
    p.add_argument('--oplog', required=False, action='store_true', help='Check replication lag')
    return vars(p.parse_args())


if __name__ == '__main__':
    params = parseargs()
    mongo_client = MongoClient(MONGODB_URI)

    if params['rw']:

        mongo_db = mongo_client['monitoring']
        mongo_db.authenticate(MONGODB_USER_RW, MONGODB_PASSWORD_RW)
        mongo_collection = mongo_db['monitoring']

        post = {'message': datetime.utcnow()}
        id = mongo_collection.insert(post)

        for i in xrange(12):

           sleep(WAIT)

           if mongo_collection.find_one({'_id': id}):
               mongo_collection.remove({'_id': id})

               if len(mongo_client.secondaries) >= 2:
                   print 'Replication OK'
                   exit(0)
               else:
                   print 'Replication OK, but too few slaves is online'
                   exit(1)


    elif params['oplog']:

        mongo_db = mongo_client['admin']

        try:
            mongo_db.authenticate(MONGODB_USER_CM, MONGODB_PASSWORD_CM)
        except OperationFailure:
            pass

        getrepl = mongo_db.command('replSetGetStatus')['members']
        calc2 = filter(lambda x: x['stateStr'] == 'PRIMARY', getrepl)[0]['optimeDate'] - filter(lambda x: x.has_key('self'), getrepl)[0]['optimeDate']

        if calc2.seconds < TIMEOUT:
            print 'Replication OK'
            exit(0)
        else:
            print 'Replication FAIL'
            exit(2)

    else:
        print "No arguments"
        exit(2)

    print 'Error in execution'
    exit(2)
