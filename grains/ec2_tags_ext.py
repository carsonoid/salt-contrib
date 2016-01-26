#!/usr/bin/env python
"""
ec2_tags_ext.py - exports all EC2 tags in an 'ec2_tags' grain and splits 'Role' tag
                  into a list on 'ec2_roles' grain.

This modules uses an external statically-linked binary 
to fetch ec2 tags so it works without a full boto installation
on all minions.

Source code for ec2_tag_fetcher is at: https://github.com/carsonoid/ec2_tag_fetcher

To use it:

  1. Place ec2_tags_ext.py in <salt_root>/_grains/
  2. Build the ec2_tag_fetcher binary and copy to somewhere in salt's file_root
  3. Make sure that salt is pushing the file to minions via a highstate to somewhere
     in the salt-minion's PATH
  4. Use it

    # push ec2_tag_fetcher out
    $ salt '*' state.highstate  

    # sync grains
    $ salt '*' saltutil.sync_grains

    # test it
    $ salt '*' grains.get ec2_tags
    $ salt '*' grains.get ec2_roles

Author: Carson Anderson <ca@carson-anderson.com>
Based on ec2_tags.py by: Emil Stenqvist <emsten@gmail.com>
Licensed under Apache License (https://raw.github.com/saltstack/salt/develop/LICENSE)
"""

import os, subprocess, json
import logging

import salt.log

log = logging.getLogger(__name__)

AWS_CREDENTIALS = {
    'access_key': None,
    'secret_key': None,
}

def _get_credentials():
    creds = AWS_CREDENTIALS.copy()

    # Minion config
    if '__opts__' in globals():
        conf = __opts__.get('ec2_tags', {})
        aws = conf.get('aws', {})
        if aws.get('access_key') and aws.get('secret_key'):
            creds.update(aws)

    # 3. Get from environment
    access_key = os.environ.get('AWS_ACCESS_KEY') or os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_KEY') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    if access_key and secret_key:
        creds.update(dict(access_key=access_key, secret_key=secret_key))

    return creds

def _get_tags(creds):
    auth_env = os.environ

    auth_env['AWS_ACCESS_KEY'] = creds['access_key']
    auth_env['AWS_SECRET_KEY'] = creds['secret_key']


    tags_str = subprocess.check_output(['ec2_tag_fetcher'], env=auth_env)
    try:
        return json.loads(tags_str)
    except:
        log.error('Couldn\'t retrieve parse tag string: %s', tags_str)
        return []

def ec2_tags():
    credentials = _get_credentials()

    ec2_tags = {}
    try:
        tags = _get_tags(credentials)
        for tag in tags:
            ec2_tags[tag['Key']] = tag['Value']
    except Exception, e:
        log.error('Couldn\'t retrieve instance tags: %s', e)
        return None

    ret = dict(ec2_tags=ec2_tags)

    # Provide ec2_tags_roles functionality
    if 'Roles' in ec2_tags:
        ret['ec2_roles'] = ec2_tags['Roles'].split(',')

    return ret


if __name__ == '__main__':
    print ec2_tags()
