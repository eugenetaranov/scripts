#!/usr/bin/env python

from datetime import datetime
from random import choice
import requests, boto

IP = ''
HOST = ''
TIMEOUT = 5
FRONTEND_PROXY_FILTER = {'tag:NAME': 'VALUE'}
SEND_MSG = True
ARN = ''


class EIP_Check():
    ''' checks connection to elastic ip and assocaites ip with other instance if failed '''
    def __init__(self, ip, hostheader, filters=None):
        self.ip = ip
        self.hostheader = hostheader
        self.filters = filters


    def move_eip(self):
        ''' selects new random tagged instance and associates elastic ip with it'''
        conn = boto.connect_ec2()
        instances = [r.instances[0] for r in conn.get_all_instances(filters=FRONTEND_PROXY_FILTER)]
        failover_instance = choice( filter(lambda x: x.ip_address != self.ip, instances) )
        eip = conn.get_all_network_interfaces(filters={'association.public-ip': self.ip})[0]
        conn.associate_address(instance_id=failover_instance.id, allocation_id=eip.allocationId, allow_reassociation=True)
        self.message = 'Elastic ip {} migrated to instance {}'.format(self.ip, failover_instance.id)


    def send_message(self, arn, tags):
        sns = boto.connect_sns()
        sns.publish(topic=arn, message=self.message, subject='Elastic ip migrated {}'.format(' '.join(tags.values())))


    def http_check(self, timeout=5):
        try:
            doc = requests.get("http://{}".format(self.ip), headers={"Host" : self.hostheader}, timeout=timeout).content
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            return False

        return True


if __name__ == '__main__':
    check = EIP_Check(IP, HOST, FRONTEND_PROXY_FILTER)

    if not check.http_check(timeout=TIMEOUT):
        check.move_eip()

        if SEND_MSG:
            check.send_message(ARN, FRONTEND_PROXY_FILTER) 
        
        print 'Check {} {} failed, moved elastic ip'.format(IP, HOST)
        exit(1)
