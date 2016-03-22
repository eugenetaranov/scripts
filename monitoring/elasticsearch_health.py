#!/usr/bin/env python

from json import load, dumps
from urllib import urlopen
from argparse import ArgumentParser
from sys import exit


def parseargs():
    p = ArgumentParser()
    p.add_argument('-s', '--server', metavar='Elasticsearch HTTP endpoint', required=False, default='127.0.0.1', help='Elasticsearch HTTP endpoint')
    p.add_argument('-p', '--port', metavar='Elasticsearch HTTP port', required=False, type=int, default=9200, help='Elasticsearch HTTP port')
    return vars(p.parse_args())

def main():
    try:
        res = urlopen('http://{0}:{1}/_cluster/health'.format(params['server'], params['port']))
    except Exception as e:
        exit(2)

    if not res.code == 200:
        print 'Error code %' % res.code
        exit(2)

    else:
        doc = load(res)

        print 'Status: {status}, total nodes: {number_of_nodes}, data nodes: {number_of_data_nodes}, active primary shards: {active_primary_shards}, relocating shards: {relocating_s
hards}, initializing shards: {initializing_shards}'.format(**doc)

        if doc['status'] == 'green' and doc['unassigned_shards'] == 0:
            exit(0)

        elif doc['status'] == 'yellow' or doc['unassigned_shards'] != 0:
            exit(1)

        else:
            exit(2)


if __name__ == '__main__':
    params = parseargs()
    main()
