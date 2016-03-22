#!/usr/bin/env python

import boto
import itertools
from json import dumps

AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
APPNAME = ''
ENV = ''
DOMAIN = ''


def main():
    ec2 = boto.connect_ec2(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    chain = itertools.chain.from_iterable

    sorted_instances = { '_meta': { 'hostvars': {} } }

    for instance in list(chain([res.instances for res in ec2.get_all_instances()])):
        if 'env' in instance.tags and 'appname' in instance.tags and 'role' in instance.tags:
            if instance.tags.get('env') == ENV and instance.tags.get('appname') == APPNAME:
                name = instance.tags.get('Name')
                if name and name.endswith(DOMAIN):
                    if instance.tags.get('role') in sorted_instances:
                        sorted_instances[instance.tags.get('role')].append(name)
                        sorted_instances['_meta']['hostvars'][name] = {}
                    else:
                        sorted_instances[instance.tags.get('role')] = [name]
                        sorted_instances['_meta']['hostvars'][name] = {}
                elif instance.private_ip_address:
                    if instance.tags.get('role') in sorted_instances:
                        sorted_instances[instance.tags.get('role')].append(instance.private_ip_address)
                        sorted_instances['_meta']['hostvars'][instance.private_ip_address] = {}
                    else:
                        sorted_instances[instance.tags.get('role')] = [instance.private_ip_address]
                        sorted_instances['_meta']['hostvars'][instance.private_ip_address] = {}

    print dumps(sorted_instances, indent=2)


if __name__ == '__main__':
    main()
