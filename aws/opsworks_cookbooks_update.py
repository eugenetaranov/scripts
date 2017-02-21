#!/usr/bin/python
'''
1. Runs berks package -b {dir}/Berksfile on all subdirectories with Berksfiles
2. Uploads cookbook archive to s3 bucket
3. Updates stack settings pointing to new cookbook archive
3. Runs custom_cookbook_update
4. Runs setup
'''

import os, boto3, subprocess
from time import sleep


COOKBOOKS_BUCKET = ''
STACK_ID = ''
RUN_SETUP = True


def cookbook_build():
    cookbook_dirs = [x for x in os.listdir('.') if os.path.isdir(x) and 'Berksfile' in os.listdir(x)]
    args = [item for sublist in cookbook_dirs for item in ['-b', '{}/Berksfile'.format(sublist)]]
    cmd = ['berks', 'package']
    cmd.extend(args)
    res = subprocess.check_output(cmd)
    artifact_name = os.path.basename(res.replace('Cookbook(s) packaged to ', '').strip())
    return artifact_name


def artifact_s3_upload(artifact_name, s3_bucket):
    s3 = boto3.resource('s3')
    s3.Object(s3_bucket, artifact_name).upload_file(artifact_name)


class Opsworks(object):
    def __init__(self):
        self.conn = boto3.client('opsworks')

    def stack_update(self, stack_id, s3_bucket, artifact_name):
        self.conn.update_stack(
            StackId=stack_id,
            CustomCookbooksSource={
                'Type': 's3',
                'Url': 'https://s3.amazonaws.com/{}/{}'.format(s3_bucket, artifact_name)
                })

    def stack_update_cookbooks(self, stack_id):
        res = self.conn.create_deployment(StackId=stack_id, Command={'Name': 'update_custom_cookbooks'})

        n = 0
        while n < 10:
            if self.conn.describe_deployments(DeploymentIds=[res['DeploymentId']])['Deployments'][0]['Status'] == 'successful':
                return
                
            sleep(10)
            n = n + 1

        raise Exception('Timeout')

    def stack_setup(self, stack_id):
        res = self.conn.create_deployment(StackId=stack_id, Command={'Name': 'setup'})

        n = 0
        while n < 10:
            if self.conn.describe_deployments(DeploymentIds=[res['DeploymentId']])['Deployments'][0]['Status'] == 'successful':
                return

            sleep(10)
            n = n + 1

        raise Exception('Timeout')


def main():
    artifact_name = cookbook_build()
    artifact_s3_upload(artifact_name, COOKBOOKS_BUCKET)
    os.unlink(artifact_name)

    ops_client = Opsworks()
    ops_client.stack_update(STACK_ID, COOKBOOKS_BUCKET, artifact_name)
    ops_client.stack_update_cookbooks(STACK_ID)

    if RUN_SETUP:
        ops_client.stack_setup(STACK_ID)


if __name__ == '__main__':
    main()
