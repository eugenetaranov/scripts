#!/usr/bin/env python

import boto, tabulate, datetime
from argparse import ArgumentParser

conn = boto.connect_ec2()
cw = boto.connect_cloudwatch()


def parseargs():
    parser = ArgumentParser()
    parser.add_argument('-v', '--vpcid')
    return vars(parser.parse_args())


def metrics(id, metric=None):
    # returns max of the 2 weeks average values

    if metric == 'cpu':
        n = cw.get_metric_statistics(3600, datetime.datetime.utcnow() - datetime.timedelta(weeks=2), datetime.datetime.utcnow(), 'CPUUtilization', 'AWS/EC2', 'Average', dimensions={'InstanceId': id})
        try:
            return int(max(n, key=lambda x: x['Average'])['Average'])
        except ValueError:
            return None
    else:
        return None

params = parseargs()

instances = [r.instances[0] for r in conn.get_all_instances(filters={'vpc_id': params['vpcid']})]

table = map( lambda a: [a.id, a.tags.get('Name'), a.tags.get('role'), a.state, a.instance_type, metrics(a.id, 'cpu')], instances )
n = 0
for row in table:
    row.insert(0, n)
    n += 1

headers = ['#', 'id', 'name', 'role', 'state', 'type', 'cpu avg %']

print tabulate.tabulate(table, headers, tablefmt='psql')

types = map( lambda a: a.instance_type, instances )
table = []

for t in set(types):
    table.append([ t, types.count(t) ])

headers = ['type', 'count']
print tabulate.tabulate(table, headers, tablefmt='psql')
