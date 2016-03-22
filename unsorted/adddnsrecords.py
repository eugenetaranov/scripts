#!/usr/bin/env python

from netaddr import IPNetwork
from dnsimple import DNSimple

# dnsimple https://github.com/mikemaccana/dnsimple-python
# adddnsrecords.py -- creates IN A records by given pattern for specific subnet, DNSsimple

NETWORKS = ['0.0.0.0/24', '0.0.0.0/24']
STARTFROM = 3
USERNAME = ''
PASSWORD = ''
DOMAIN = 'deliverme-mta.com'


def main():
    dns = DNSimple(username=USERNAME, password=PASSWORD)

    for net in NETWORKS:
        network = IPNetwork(net)
        for ip in network[1:-1]:
            print 'Adding mta{}-{}.{} IN A {}'.format(STARTFROM, ip.words[3], DOMAIN, str(ip))
            dns.add_record(DOMAIN, {'record_type': 'A', 'name': 'mta{}-{}'.format(STARTFROM, ip.words[3]),
                'content': str(ip)})
        STARTFROM += 1


if __name__ == '__main__':
    main()
