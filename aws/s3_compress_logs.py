#!/usr/bin/env python

import boto, gzip, shutil
from datetime import date, timedelta
from os import path, unlink


BUCKET = 'BUCKET'
PREFIX = 'AWSLogs//elasticloadbalancing/us-east-1/'
ALL_DAYS = False
TMP_DIR = '/tmp'
DAYS_AGO = 1
DEBUG = True


def s3_compress():
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(BUCKET)

    if ALL_DAYS:
        prefix = PREFIX
    else:
        prefix = PREFIX + (date.today() - timedelta(days=DAYS_AGO)).strftime('%Y/%m/%d')

    keys = filter( lambda x: x.name.endswith('.gz') == False, bucket.get_all_keys( prefix=prefix ))


    def sum_size(keys):
        return sum( map(lambda x: x.size, keys) )


    def compress(path0, path1):
        with open(path0, 'rb') as f_in, gzip.open(path1, 'wb', compresslevel=3) as f_out:
            shutil.copyfileobj(f_in, f_out)


    if DEBUG:
        size0 = sum_size(keys)


    for key in keys:
        dir_path, name = path.split(key.name)
        key.get_contents_to_filename(path.join(TMP_DIR, name))
        compress(path.join( TMP_DIR, name ), path.join( TMP_DIR, name + '.gz' ))
        new_key = bucket.new_key(path.join( dir_path, name + '.gz' ))
        new_key.set_contents_from_filename(path.join( TMP_DIR, name + '.gz' ))
        key.delete()
        unlink(path.join( TMP_DIR, name + '.gz' ))
        unlink(path.join( TMP_DIR, name ))
        print new_key.name


    if DEBUG:
        keys = filter( lambda x: x.name.endswith('.gz') == True, bucket.get_all_keys( prefix=prefix ))
        size1 = sum_size(keys)

        print 'Before compression:', naturalsize(size0)
        print 'After compression:', naturalsize(size1)
        print 'Diff:', naturalsize(size0 - size1)

if __name__ == '__main__':
    from humanize import naturalsize
    s3_compress()
