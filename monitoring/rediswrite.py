#!/usr/bin/env python

from redis import Redis
from argparse import ArgumentParser
from sys import exit
from time import time


TTL = 10


def parseargs():
    p = ArgumentParser()
    p.add_argument('-H', '--host', required=True)
    p.add_argument('-P', '--port', default=6379, required=False, type=int)
    return vars(p.parse_args())


def main():

    conn = Redis(host=params['host'], port=params['port'], socket_timeout=10)

    key = int(time())

    try:
        conn.set(key, key)
    except Exception as e:
        print 'Connection failed: %s' % str(e)
        exit(2)

    conn.expire(key, TTL)

    try:
        assert int(conn.get(key)) == key
        print 'OK'
    except:
        print 'Key read failed', key, conn.get(key)
        exit(2)


if __name__ == '__main__':
    params = parseargs()
    main()
