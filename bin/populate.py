#!/usr/bin/env python3

'''
Build Terraform Config Files
'''

import logging
import os
import sys
import argparse
import json
import dns.resolver
import re
import os
import dns.reversename
import getpass
import ipaddress
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl, VmomiSupport
import jinja2
from jinja2.meta import find_undeclared_variables
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import xml.etree.ElementTree as ET
import gzip
import readline
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import hashlib
try:
    import boto3
except ImportError:
    pass

class cbrelease(object):

    def __init__(self, type, release):
        self.pkgmgr_type = type
        self.os_release = release

    def get_versions(self):
        if self.pkgmgr_type == 'yum':
            return self.get_rpm()
        elif self.pkgmgr_type == 'apt':
            return self.get_apt()

    def get_rpm(self):
        osrel = self.os_release
        pkg_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/rpm/' + osrel + '/x86_64/repodata/repomd.xml'
        filelist_url = None
        return_list = []

        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = requests.get(pkg_url, verify=False, timeout=15)

        if response.status_code != 200:
            raise Exception("Can not get repo data: error %d" % response.status_code)

        root = ET.fromstring(response.text)
        for datatype in root.findall('{http://linux.duke.edu/metadata/repo}data'):
            if datatype.get('type') == 'filelists':
                filelist_url = datatype.find('{http://linux.duke.edu/metadata/repo}location').get('href')

        if not filelist_url:
            raise Exception("Invalid response from server, can not get release list.")

        list_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/rpm/' + osrel + '/x86_64/' + filelist_url

        response = requests.get(list_url, verify=False, timeout=15)

        if response.status_code != 200:
            raise Exception("Can not get release list: error %d" % response.status_code)

        try:
            filelist_xml = gzip.decompress(response.content).decode()
            root = ET.fromstring(filelist_xml)
        except Exception:
            print("Invalid response from server, can not get release list.")
            raise

        for release in root.findall('{http://linux.duke.edu/metadata/filelists}package'):
            if release.get('name') == 'couchbase-server':
                version = release.find('{http://linux.duke.edu/metadata/filelists}version').get('ver')
                relcode = release.find('{http://linux.duke.edu/metadata/filelists}version').get('rel')
                # print("%s-%s" %(version, relcode))
                vers_string = "%s-%s" % (version, relcode)
                return_list.append(vers_string)

        return return_list

    def get_apt(self):
        osrel = self.os_release
        pkg_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/deb/dists/' + osrel + '/' + osrel + '/main/binary-amd64/Packages.gz'
        return_list = []

        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = requests.get(pkg_url, verify=False, timeout=15)

        if response.status_code != 200:
            raise Exception("Can not get APT package data: error %d" % response.status_code)

        try:
            response_text = gzip.decompress(response.content).decode()
        except Exception:
            print("Invalid response from server, can not get package list.")
            raise

        lines = iter(response_text.splitlines())

        for line in lines:
            if re.match(r'Version', line):
                version = line.split(':')[1]
                # print("%s" % version)
                return_list.append(version)

        return return_list

class params(object):

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--template', action='store', help="Template file")
        parser.add_argument('--globals', action='store', help="Global variables file")
        parser.add_argument('--locals', action='store', help="Local variables file")
        parser.add_argument('--debug', action='store', help="Debug level", type=int, default=3)
        parser.add_argument('--packer', action='store_true', help="Packer file", default=False)
        # parser.add_argument('--aws', action='store_true', help="Enable AWS Support", default=False)
        # parser.add_argument('--gcp', action='store_true', help="Enable GCP Support", default=False)
        # parser.add_argument('--azure', action='store_true', help="Enable Azure Support", default=False)
        # parser.add_argument('--vmware', action='store_true', help="Enable VMware Support", default=False)
        self.parser = parser

class processTemplate(object):

    def __init__(self, pargs):
        self.debug = pargs.debug
        self.template_file = pargs.template
        template_dir = os.path.dirname(self.template_file)
        self.globals_file = None
        self.locals_file = None
        self.linux_type = None
        self.linux_release = None
        self.linux_pkgmgr = None
        self.ssh_private_key = None
        self.ssh_key_fingerprint = None
        self.cb_version = None
        self.cb_index_mem_type = None
        self.aws_image_name = None
        self.aws_image_owner = None
        self.aws_image_user = None
        self.aws_region = None
        self.aws_ami_id = None
        self.aws_instance_type = None
        self.aws_ssh_key = None
        self.aws_subnet_id = None
        self.aws_vpc_id = None
        self.aws_sg_id = None
        self.aws_root_iops = None
        self.aws_root_size = None
        self.aws_root_type = None
        self.global_var_json = {}
        self.local_var_json = {}

        logging.basicConfig()
        self.logger = logging.getLogger()
        if self.debug == 0:
            self.logger.setLevel(logging.DEBUG)
        elif self.debug == 1:
            self.logger.setLevel(logging.INFO)
        elif self.debug == 2:
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.setLevel(logging.CRITICAL)

        if pargs.globals:
            self.globals_file = pargs.globals
        else:
            if os.path.exists('globals.json'):
                self.globals_file = 'globals.json'
            else:
                print("WARNING: No global variable file present.")

        if pargs.locals:
            self.locals_file = pargs.locals
        else:
            if os.path.exists(template_dir + '/locals.json'):
                self.locals_file = template_dir + '/locals.json'
            else:
                print("INFO: No local variable file present.")

        if self.globals_file:
            try:
                with open(self.globals_file, 'r') as inputFile:
                    global_var_text = inputFile.read()
                    self.global_var_json = json.loads(global_var_text)
                inputFile.close()
            except OSError as e:
                print("Can not read global variable file: %s" % str(e))
                sys.exit(1)

        if self.locals_file:
            try:
                with open(self.locals_file, 'r') as inputFile:
                    local_var_text = inputFile.read()
                    self.local_var_json = json.loads(local_var_text)
                inputFile.close()
            except OSError as e:
                print("Can not read local variable file: %s" % str(e))
                sys.exit(1)

        try:
            with open(self.template_file, 'r') as inputFile:
                raw_input = inputFile.read()
            inputFile.close()
        except OSError as e:
            print("Can not read template file: %s" % str(e))
            sys.exit(1)

        env = jinja2.Environment(undefined=jinja2.DebugUndefined)
        template = env.from_string(raw_input)
        rendered = template.render()
        ast = env.parse(rendered)
        requested_vars = find_undeclared_variables(ast)

        for item in sorted(requested_vars):
            if item == 'CB_VERSION':
                try:
                    self.get_cb_version()
                except Exception as e:
                    print("Error: %s" % str(e))
                    sys.exit(1)
                self.logger.info("CB_VERSION = %s" % self.cb_version)
            elif item == 'LINUX_TYPE':
                if not self.linux_type:
                    try:
                        self.get_linux_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("LINUX_TYPE = %s" % self.linux_type)
            elif item == 'LINUX_RELEASE':
                if not self.linux_release:
                    try:
                        self.get_linux_release()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("LINUX_RELEASE = %s" % self.linux_release)
            elif item == 'AWS_IMAGE':
                if not self.aws_image_name:
                    try:
                        self.get_aws_image_name()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_IMAGE = %s" % self.aws_image_name)
            elif item == 'AWS_AMI_OWNER':
                if not self.aws_image_owner:
                    try:
                        self.get_aws_image_owner()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_AMI_OWNER = %s" % self.aws_image_owner)
            elif item == 'AWS_AMI_USER':
                if not self.aws_image_user:
                    try:
                        self.get_aws_image_user()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_AMI_USER = %s" % self.aws_image_user)
            elif item == 'AWS_REGION':
                if not self.aws_region:
                    try:
                        self.aws_get_region()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_REGION = %s" % self.aws_region)
            elif item == 'AWS_AMI_ID':
                if not self.aws_ami_id:
                    try:
                        self.aws_get_ami_id()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_AMI_ID = %s" % self.aws_ami_id)
            elif item == 'AWS_INSTANCE_TYPE':
                if not self.aws_instance_type:
                    try:
                        self.aws_get_instance_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_INSTANCE_TYPE = %s" % self.aws_instance_type)
            elif item == 'CB_INDEX_MEM_TYPE':
                if not self.cb_index_mem_type:
                    try:
                        self.get_cb_index_mem_setting()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("CB_INDEX_MEM_TYPE = %s" % self.cb_index_mem_type)
            elif item == 'AWS_SSH_KEY':
                if not self.aws_ssh_key:
                    try:
                        self.aws_get_ssh_key()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_SSH_KEY = %s" % self.aws_ssh_key)
            elif item == 'SSH_PRIVATE_KEY':
                if not self.ssh_private_key:
                    try:
                        self.get_private_key()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("SSH_PRIVATE_KEY = %s" % self.ssh_private_key)
            elif item == 'AWS_SUBNET_ID':
                if not self.aws_subnet_id:
                    try:
                        self.aws_get_subnet_id()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_SUBNET_ID = %s" % self.aws_subnet_id)
            elif item == 'AWS_VPC_ID':
                if not self.aws_vpc_id:
                    try:
                        self.aws_get_vpc_id()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_VPC_ID = %s" % self.aws_vpc_id)
            elif item == 'AWS_SECURITY_GROUP':
                if not self.aws_sg_id:
                    try:
                        self.aws_get_sg_id()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_SECURITY_GROUP = %s" % self.aws_sg_id)

        raw_template = jinja2.Template(raw_input)
        format_template = raw_template.render(
                                              CB_VERSION=self.cb_version,
                                              LINUX_TYPE=self.linux_type,
                                              LINUX_RELEASE=self.linux_release,
                                              AWS_IMAGE=self.aws_image_name,
                                              AWS_AMI_OWNER=self.aws_image_owner,
                                              AWS_AMI_USER=self.aws_image_user,
                                              AWS_REGION=self.aws_region,
                                              AWS_AMI_ID=self.aws_ami_id,
                                              AWS_INSTANCE_TYPE=self.aws_instance_type,
                                              CB_INDEX_MEM_TYPE=self.cb_index_mem_type,
                                              AWS_SSH_KEY=self.aws_ssh_key,
                                              SSH_PRIVATE_KEY=self.ssh_private_key,
                                              AWS_SUBNET_ID=self.aws_subnet_id,
                                              AWS_VPC_ID=self.aws_vpc_id,
                                              AWS_SECURITY_GROUP=self.aws_sg_id,
                                              AWS_ROOT_IOPS=self.aws_root_iops,
                                              AWS_ROOT_SIZE=self.aws_root_size,
                                              AWS_ROOT_TYPE=self.aws_root_type,
                                              )

        if pargs.packer and self.linux_type:
            output_file = self.linux_type + '-' + self.linux_release + '.pkrvars.hcl'
        elif pargs.packer:
            output_file = 'variables.pkrvars.hcl'
        else:
            output_file = 'variables.tf'

        output_file = template_dir + '/' + output_file
        try:
            with open(output_file, 'w') as write_file:
                write_file.write(format_template)
                write_file.write("\n")
                write_file.close()
        except OSError as e:
            print("Can not write to new variable file: %s" % str(e))
            sys.exit(1)

    def aws_get_sg_id(self):
        if not self.aws_vpc_id:
            try:
                self.aws_get_vpc_id()
            except Exception:
                raise
        sg_list = []
        sg_name_list = []
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                self.aws_vpc_id,
            ]
        }
        sgs = ec2_client.describe_security_groups(Filters=[vpc_filter, ])
        for i in range(len(sgs['SecurityGroups'])):
            sg_list.append(sgs['SecurityGroups'][i]['GroupId'])
            sg_name_list.append(sgs['SecurityGroups'][i]['GroupName'])

        selection = self.ask('Select security group', sg_list, sg_name_list)
        self.aws_sg_id = sgs['SecurityGroups'][selection]['GroupId']

    def aws_get_vpc_id(self):
        vpc_list = []
        vpc_name_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpcs = ec2_client.describe_vpcs()
        for i in range(len(vpcs['Vpcs'])):
            vpc_list.append(vpcs['Vpcs'][i]['VpcId'])
            if 'Tags' in vpcs['Vpcs'][i]:
                vpc_name_list.append(self.aws_get_tag('Name', vpcs['Vpcs'][i]['Tags']))
            else:
                vpc_name_list.append('')

        selection = self.ask('Select VPC', vpc_list, vpc_name_list)
        self.aws_vpc_id = vpcs['Vpcs'][selection]['VpcId']

    def aws_get_subnet_id(self):
        if not self.aws_vpc_id:
            try:
                self.aws_get_vpc_id()
            except Exception:
                raise
        subnet_list = []
        subnet_name_list = []
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                self.aws_vpc_id,
            ]
        }
        subnets = ec2_client.describe_subnets(Filters=[vpc_filter, ])
        for i in range(len(subnets['Subnets'])):
            subnet_list.append(subnets['Subnets'][i]['SubnetId'])
            if 'Tags' in subnets['Subnets'][i]:
                subnet_name_list.append(self.aws_get_tag('Name', subnets['Subnets'][i]['Tags']))
            else:
                subnet_name_list.append('')

        selection = self.ask('Select subnet', subnet_list, subnet_name_list)
        self.aws_vpc_id = subnets['Subnets'][selection]['SubnetId']

    def get_private_key(self):
        dir_list = []
        key_file_list = []
        key_directory = os.environ['HOME'] + '/.ssh'

        for file_name in os.listdir(key_directory):
            full_path = key_directory + '/' + file_name
            dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')
            blob = file_handle.read()
            pem_key_bytes = str.encode(blob)

            try:
                key = serialization.load_pem_private_key(
                    pem_key_bytes, password=None, backend=default_backend()
                )
            except Exception:
                continue

            self.logger.info("Found private key %s" % dir_list[i])
            key_file_list.append(dir_list[i])
            pri_der = key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            der_digest = hashlib.sha1(pri_der)
            hex_digest = der_digest.hexdigest()
            key_fingerprint = ':'.join(hex_digest[i:i + 2] for i in range(0, len(hex_digest), 2))
            if key_fingerprint == self.ssh_key_fingerprint:
                print("Auto selecting SSH private key %s" % dir_list[i])
                self.ssh_private_key = dir_list[i]
                return True

        selection = self.ask('Select SSH private key', key_file_list)
        self.ssh_private_key = key_file_list[selection]

    def aws_get_ssh_key(self):
        key_list = []
        key_name_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        key_pairs = ec2_client.describe_key_pairs()
        for i in range(len(key_pairs['KeyPairs'])):
            key_list.append(key_pairs['KeyPairs'][i]['KeyPairId'])
            key_name_list.append(key_pairs['KeyPairs'][i]['KeyName'])

        selection = self.ask('Select SSH key', key_list, key_name_list)
        self.aws_ssh_key = key_pairs['KeyPairs'][selection]['KeyPairId']
        self.ssh_key_fingerprint = key_pairs['KeyPairs'][selection]['KeyFingerprint']

    def get_cb_index_mem_setting(self):
        option_list = [
            'Standard Index Storage',
            'Memory-optimized',
        ]
        selection = self.ask('Select index storage option', option_list)
        if selection == 0:
            self.cb_index_mem_type = 'default'
        else:
            self.cb_index_mem_type = 'memopt'

    def aws_get_instance_type(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'instance_type' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['instance_type']
        self.logger.info("Default instance type is %s" % default_selection)
        selection = self.ask_text('Instance type', default_selection)
        self.aws_instance_type = selection

    def aws_get_ami_id(self):
        image_list = []
        image_name_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        images = ec2_client.describe_images(Owners=['self'])
        for i in range(len(images['Images'])):
            image_list.append(images['Images'][i]['ImageId'])
            image_name_list.append(images['Images'][i]['Name'])

        selection = self.ask('Select AMI', image_list, image_name_list)
        self.aws_ami_id = images['Images'][selection]['ImageId']

    def aws_get_region(self):
        try:
            sts = boto3.client('sts')
            sts.get_caller_identity()
        except Exception:
            raise

        if 'AWS_REGION' in os.environ:
            self.aws_region = os.environ['AWS_REGION']
        elif 'AWS_DEFAULT_REGION' in os.environ:
            self.aws_region = os.environ['AWS_DEFAULT_REGION']
        elif boto3.DEFAULT_SESSION:
            self.aws_region = boto3.DEFAULT_SESSION.region_name
        elif boto3.Session().region_name:
            self.aws_region = boto3.Session().region_name

        if not self.aws_region:
            answer = input("AWS Region: ")
            answer = answer.rstrip("\n")
            self.aws_region = answer

    def get_aws_image_user(self):
        if not self.linux_type:
            try:
                self.get_linux_type()
            except Exception:
                raise
        if not self.linux_release:
            try:
                self.get_linux_release()
            except Exception:
                raise
        for i in range(len(self.local_var_json['linux'][self.linux_type])):
            if self.local_var_json['linux'][self.linux_type][i]['version'] == self.linux_release:
                self.aws_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate ssh user for %s %s linux." % (self.linux_type, self.linux_release))

    def get_aws_image_owner(self):
        if not self.aws_image_owner:
            try:
                self.get_aws_image_name()
            except Exception:
                raise

    def get_aws_image_name(self):
        if not self.linux_type:
            try:
                self.get_linux_type()
            except Exception:
                raise
        if not self.linux_release:
            try:
                self.get_linux_release()
            except Exception:
                raise
        for i in range(len(self.local_var_json['linux'][self.linux_type])):
            if self.local_var_json['linux'][self.linux_type][i]['version'] == self.linux_release:
                self.aws_image_name = self.local_var_json['linux'][self.linux_type][i]['image']
                self.aws_image_owner = self.local_var_json['linux'][self.linux_type][i]['owner']
                self.aws_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable image for %s %s linux." % (self.linux_type, self.linux_release))

    def get_cb_version(self):
        if not self.linux_type:
            try:
                self.get_linux_type()
            except Exception:
                raise
        if not self.linux_release:
            try:
                self.get_linux_release()
            except Exception:
                raise
        try:
            cbr = cbrelease(self.linux_pkgmgr, self.linux_release)
            versions_list = cbr.get_versions()
            release_list = self.reverse_list(versions_list)
        except Exception:
            raise

        selection = self.ask('Select Couchbase Version', release_list)
        self.cb_version = release_list[selection]

    def get_linux_release(self):
        version_list = []
        version_desc = []
        if 'linux' not in self.global_var_json:
            raise Exception("Linux distribution global configuration required.")

        for i in range(len(self.global_var_json['linux'][self.linux_type])):
            version_list.append(self.global_var_json['linux'][self.linux_type][i]['version'])
            version_desc.append(self.global_var_json['linux'][self.linux_type][i]['name'])

        selection = self.ask('Select Version', version_list, version_desc)
        self.linux_release = self.global_var_json['linux'][self.linux_type][selection]['version']
        self.linux_pkgmgr = self.global_var_json['linux'][self.linux_type][selection]['type']

    def get_linux_type(self):
        distro_list = []
        if 'linux' not in self.global_var_json:
            raise Exception("Linux distribution global configuration required.")

        for key in self.global_var_json['linux']:
            distro_list.append(key)

        selection = self.ask('Select Linux Distribution', distro_list)
        self.linux_type = distro_list[selection]

    def reverse_list(self, list):
        return [item for item in reversed(list)]

    def aws_get_tag(self, key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return tags[i]['Value']
        return ''

    def ask(self, question, options=[], descriptions=[]):
        print("%s:" % question)
        for i in range(len(options)):
            if i < len(descriptions):
                extra = '(' + descriptions[i] + ')'
            else:
                extra = ''
            print(" %02d) %s %s" % (i+1, options[i], extra))
        while True:
            answer = input("Selection: ")
            answer = answer.rstrip("\n")
            try:
                value = int(answer)
                if value > 0 and value <= len(options):
                    return value - 1
                else:
                    print("Incorrect value, please try again...")
                    continue
            except Exception:
                print("Please select the number corresponding to your selection.")
                continue

    def ask_text(self, question, default=''):
        while True:
            prompt = question + ' [' + default + ']: '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) > 0:
                return answer
            else:
                if len(default) > 0:
                    return default
                else:
                    print("Please make a selection.")
                    continue

def main():
    parms = params()
    parameters = parms.parser.parse_args()
    processTemplate(parameters)

if __name__ == '__main__':

    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            os._exit(0)
        else:
            os._exit(e.code)
