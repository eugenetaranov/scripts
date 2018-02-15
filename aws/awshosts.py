#!/usr/bin/env python

import boto.utils, boto3
from tabulate import tabulate

region_name = boto.utils.get_instance_identity()['document']['region']
resource = boto3.resource('ec2', region_name=region_name)

instances = []

for instance in list(resource.instances.all()):
  name = [tag['Value'] for tag in instance.tags if tag['Key'] == 'Name'][0]
  instances.append([name, instance.instance_id, instance.private_ip_address, instance.state['Name']])

print tabulate(sorted(instances), tablefmt="rst")
