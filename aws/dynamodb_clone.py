#!/usr/bin/env python
# Clones DynamoDB tables with defined prefix and copies defined number of records from original table

import boto
from argparse import ArgumentParser
from signal import signal, SIGINT
from time import sleep


AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
SEPARATOR = '_'
SLEEPTIME = 20

def signal_handler(signal, frame):
    print '\nExiting...'
    exit(1)


def parseargs():
    parser = ArgumentParser()
    parser.add_argument('--tables', default = 'all', help = 'Comma separated list of tables to clone from, default is all')
    parser.add_argument('--prefix', default = 'new', help = 'Prefix for cloned table, default is "new"')
    parser.add_argument('--records', default = 0, help = 'Number of records to copy, if zero - just schema is copied, default is 0')
    return vars(parser.parse_args())


def main():
    if AWS_SECRET_ACCESS_KEY != '' and AWS_ACCESS_KEY_ID != '':
        conn = boto.connect_dynamodb(aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    else:
        conn = boto.connect_dynamodb()

    if params['tables'] == 'all':
        tables = conn.list_tables()
    else:
        tables = params['tables'].split(',')

    for table_name in tables:
        table = conn.get_table(table_name)

        # new_table_name = '{0}{1}{2}'.format(params['prefix'], SEPARATOR, table_name)
        new_table_name = '{0}{1}{2}'.format(params['prefix'], SEPARATOR, table_name[3:])

        try:
            conn.create_table(new_table_name, table.schema, 1, 1)
            print 'Created table', new_table_name
        except Exception, e:
            print 'Could not create table', new_table_name, e.message

        # putting items into dynamodb 
        records_num = int(params['records'])
        if records_num > 0:
            records = table.scan(max_results=records_num).response['Items']
            new_table = conn.get_table(new_table_name)

            while True:
                if new_table.status == 'ACTIVE':
                    break
                new_table.refresh()
                sleep(SLEEPTIME)

            for record in records:
                item = new_table.new_item(attrs=record)
                try:
                    item.put()
                except Exception, e:
                    print e.message, record, new_table_name


if __name__ == '__main__':
    params = parseargs()
    signal(SIGINT, signal_handler)
    main()
