#!/usr/bin/env python

import subprocess
import logging
from boto import route53
from socket import gethostname


AWS_ACCESS_KEY = ''
AWS_SECRET_ACCESS_KEY = ''
DOMAIN = ''
TTL = 600

logger = logging.getLogger(__name__)
handler = logging.FileHandler('/var/log/route53.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_instance_details():
    ec2_hostname = subprocess.Popen(["/opt/aws/bin/ec2-metadata", "--public-hostname"], stdout=subprocess.PIPE).communicate()[0].split(':')[1].strip()
    hostname = gethostname()
    return hostname, ec2_hostname

def dns_update():
    conn = route53.connection.Route53Connection(aws_access_key_id = AWS_ACCESS_KEY, aws_secret_access_key = AWS_SECRET_ACCESS_KEY)
    zone = conn.get_zone(DOMAIN)
    hostname, ec2_hostname = get_instance_details()
    if ec2_hostname in zone.get_cname(hostname, 'CNAME').resource_records:
        try:
            zone.update_cname(hostname, ec2_hostname, ttl = TTL)
            logger.info('Updated %s, set to %s' % (hostname, ec2_hostname))
        except route53.exception.DNSServerError as e:
            logger.error('Could not update %s: %s' % (hostname, e.reason))
    else:
        logger.info('Record %s is correct, skipping update' % hostname)


if __name__ == '__main__':
    dns_update()
