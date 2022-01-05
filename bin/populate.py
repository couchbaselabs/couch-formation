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
import crypt
import ipaddress
import jinja2
from jinja2.meta import find_undeclared_variables
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import xml.etree.ElementTree as ET
import gzip
import datetime
import readline
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from Crypto.PublicKey import RSA
import hashlib
from shutil import copyfile
import pytz
try:
    import boto3
except ImportError:
    pass
try:
    from pyVim.connect import SmartConnectNoSSL, Disconnect
    from pyVmomi import vim, vmodl, VmomiSupport
except ImportError:
    pass



CB_CFG_HEAD = """####
variable "cluster_spec" {
  description = "Map of cluster nodes and services."
  type        = map
  default     = {"""

CB_CFG_NODE = """
    cb-{{ NODE_ENV }}-n{{ NODE_NUMBER_FMT }} = {
      node_number     = {{ NODE_NUMBER }},
      node_services   = "{{ NODE_SERVICES }}",
      install_mode    = "{{ NODE_INSTALL_MODE }}",
      node_ip_address = "{{ NODE_IP_ADDRESS }}",
    }
"""

CB_CFG_TAIL = """
  }
}
"""

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
        parser.add_argument('--cluster', action='store_true', help="Packer file", default=False)
        parser.add_argument('--dev', action='store', help="Development Environment", type=int)
        parser.add_argument('--test', action='store', help="Test Environment", type=int)
        parser.add_argument('--prod', action='store', help="Prod Environment", type=int)
        parser.add_argument('--location', action='store', help="Public/Private Cloud", default='aws')
        parser.add_argument('--refresh', action='store_true', help="Packer file", default=False)
        parser.add_argument('--host', action='store', help="Host Name")
        parser.add_argument('--user', action='store', help="Host User")
        parser.add_argument('--password', action='store', help="Host Password")
        self.parser = parser

class processTemplate(object):

    def __init__(self, pargs):
        self.debug = pargs.debug
        self.cwd = os.getcwd()
        if not pargs.cluster:
            self.template_file = pargs.template
            self.template_dir = os.path.dirname(self.template_file)
        else:
            self.template_file = ''
            self.template_dir = ''
        self.dev_num = pargs.dev
        self.test_num = pargs.test
        self.prod_num = pargs.prod
        self.packer_mode = pargs.packer
        self.globals_file = None
        self.locals_file = None
        self.linux_type = None
        self.linux_release = None
        self.linux_pkgmgr = None
        self.ssh_private_key = None
        self.ssh_public_key = None
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
        self.vmware_hostname = pargs.host
        self.vmware_username = pargs.user
        self.vmware_password = pargs.password
        self.vmware_datacenter = None
        self.vmware_cluster = None
        self.vmware_datastore = None
        self.vmware_folder = None
        self.vmware_ostype = None
        self.vmware_cpucores = None
        self.vmware_memsize = None
        self.vmware_disksize = None
        self.vmware_network = None
        self.vmware_iso = None
        self.vmware_build_user = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_timezone = None
        self.vmware_key = None
        self.vmware_dc_folder = None
        self.vmware_network_folder = None
        self.vmware_host_folder = None
        self.vmware_dvs = None
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

        self.working_dir = self.cwd + '/' + pargs.location
        if not os.path.exists(self.working_dir):
            print("Location %s does not exist." % self.working_dir)
            sys.exit(1)

        if len(self.template_dir) > 0:
            print("[i] Template file path specified, environment mode disabled.")
        else:
            try:
                self.get_paths(refresh=pargs.refresh)
            except Exception as e:
                print("Error: %s" % str(e))
                sys.exit(1)
            self.template_file = self.template_dir + '/' + self.template_file

        if pargs.cluster:
            try:
                self.create_cluster_config()
            except Exception as e:
                print("Error: %s" % str(e))
                sys.exit(1)
            print("Cluster configuration complete.")
            sys.exit(0)

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
            if os.path.exists(self.template_dir + '/locals.json'):
                self.locals_file = self.template_dir + '/locals.json'
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
            elif item == 'AWS_ROOT_IOPS':
                if not self.aws_root_iops:
                    try:
                        self.aws_get_root_iops()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_ROOT_IOPS = %s" % self.aws_root_iops)
            elif item == 'AWS_ROOT_SIZE':
                if not self.aws_root_size:
                    try:
                        self.aws_get_root_size()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_ROOT_SIZE = %s" % self.aws_root_size)
            elif item == 'AWS_ROOT_TYPE':
                if not self.aws_root_type:
                    try:
                        self.aws_get_root_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AWS_ROOT_TYPE = %s" % self.aws_root_type)
            elif item == 'VMWARE_HOSTNAME':
                if not self.vmware_hostname:
                    try:
                        self.vmware_get_hostname()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_HOSTNAME = %s" % self.vmware_hostname)
            elif item == 'VMWARE_USERNAME':
                if not self.vmware_username:
                    try:
                        self.vmware_get_username()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_USERNAME = %s" % self.vmware_username)
            elif item == 'VMWARE_PASSWORD':
                if not self.vmware_password:
                    try:
                        self.vmware_get_password()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_PASSWORD = %s" % self.vmware_password)
            elif item == 'VMWARE_DATACENTER':
                if not self.vmware_datacenter:
                    try:
                        self.vmware_get_datacenter()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_DATACENTER = %s" % self.vmware_datacenter)
            elif item == 'VMWARE_CLUSTER':
                if not self.vmware_cluster:
                    try:
                        self.vmware_get_cluster()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_CLUSTER = %s" % self.vmware_cluster)
            elif item == 'VMWARE_DATASTORE':
                if not self.vmware_datastore:
                    try:
                        self.vmware_get_datastore()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_DATASTORE = %s" % self.vmware_datastore)
            elif item == 'VMWARE_FOLDER':
                if not self.vmware_folder:
                    try:
                        self.vmware_get_folder()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_FOLDER = %s" % self.vmware_folder)
            elif item == 'VMWARE_OS_TYPE':
                if not self.vmware_ostype:
                    try:
                        self.vmware_get_ostype()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_OS_TYPE = %s" % self.vmware_ostype)
            elif item == 'VMWARE_CPU_CORES':
                if not self.vmware_cpucores:
                    try:
                        self.vmware_get_cpucores()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_CPU_CORES = %s" % self.vmware_cpucores)
            elif item == 'VMWARE_MEM_SIZE':
                if not self.vmware_memsize:
                    try:
                        self.vmware_get_memsize()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_MEM_SIZE = %s" % self.vmware_memsize)
            elif item == 'VMWARE_DISK_SIZE':
                if not self.vmware_disksize:
                    try:
                        self.vmware_get_disksize()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_DISK_SIZE = %s" % self.vmware_disksize)
            elif item == 'VMWARE_NETWORK':
                if not self.vmware_network:
                    try:
                        self.vmware_get_network()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_NETWORK = %s" % self.vmware_network)
            elif item == 'VMWARE_ISO_URL':
                if not self.vmware_iso:
                    try:
                        self.vmware_get_isourl()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_ISO_URL = %s" % self.vmware_iso)
            elif item == 'VMWARE_BUILD_USERNAME':
                if not self.vmware_build_user:
                    try:
                        self.vmware_get_build_username()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_BUILD_USERNAME = %s" % self.vmware_build_user)
            elif item == 'VMWARE_BUILD_PASSWORD':
                if not self.vmware_build_password:
                    try:
                        self.vmware_get_build_password()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_BUILD_PASSWORD = %s" % self.vmware_build_password)
            elif item == 'VMWARE_BUILD_PWD_ENCRYPTED':
                if not self.vmware_build_pwd_encrypted:
                    try:
                        self.vmware_get_build_password()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_BUILD_PWD_ENCRYPTED = %s" % self.vmware_build_pwd_encrypted)
            elif item == 'VMWARE_KEY':
                if not self.ssh_public_key:
                    try:
                        self.get_public_key()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_KEY = %s" % self.ssh_public_key)
            elif item == 'VMWARE_TIMEZONE':
                if not self.vmware_timezone:
                    try:
                        self.get_timezone()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_TIMEZONE = %s" % self.vmware_timezone)

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
                                              VMWARE_HOSTNAME=self.vmware_hostname,
                                              VMWARE_USERNAME=self.vmware_username,
                                              VMWARE_PASSWORD=self.vmware_password,
                                              VMWARE_DATACENTER=self.vmware_datacenter,
                                              VMWARE_CLUSTER=self.vmware_cluster,
                                              VMWARE_DATASTORE=self.vmware_datastore,
                                              VMWARE_FOLDER=self.vmware_folder,
                                              VMWARE_OS_TYPE=self.vmware_ostype,
                                              VMWARE_CPU_CORES=self.vmware_cpucores,
                                              VMWARE_MEM_SIZE=self.vmware_memsize,
                                              VMWARE_DISK_SIZE=self.vmware_disksize,
                                              VMWARE_NETWORK=self.vmware_network,
                                              VMWARE_ISO_URL=self.vmware_iso,
                                              VMWARE_BUILD_USERNAME=self.vmware_build_user,
                                              VMWARE_BUILD_PASSWORD=self.vmware_build_password,
                                              VMWARE_BUILD_PWD_ENCRYPTED=self.vmware_build_pwd_encrypted,
                                              VMWARE_TIMEZONE=self.vmware_timezone,
                                              VMWARE_KEY=self.ssh_public_key,
                                              )

        if pargs.packer and self.linux_type:
            output_file = self.linux_type + '-' + self.linux_release + '.pkrvars.hcl'
        elif pargs.packer:
            output_file = 'variables.pkrvars.hcl'
        else:
            output_file = 'variables.tf'

        output_file = self.template_dir + '/' + output_file
        try:
            with open(output_file, 'w') as write_file:
                write_file.write(format_template)
                write_file.write("\n")
                write_file.close()
        except OSError as e:
            print("Can not write to new variable file: %s" % str(e))
            sys.exit(1)

    def get_timezone(self):
        local_code = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()
        tzpath = '/etc/localtime'
        tzlist = []
        if os.path.exists(tzpath) and os.path.islink(tzpath):
            link_path = os.path.realpath(tzpath)
            start = link_path.find("/") + 1
            while start != 0:
                link_path = link_path[start:]
                try:
                    pytz.timezone(link_path)
                    self.vmware_timezone = link_path
                    return True
                except pytz.UnknownTimeZoneError:
                    pass
                start = link_path.find("/") + 1

        for name in pytz.all_timezones:
            tzone = pytz.timezone(name)
            code = datetime.datetime.now(tzone).tzname()
            if code == local_code:
                tzlist.append(tzone)
        selection = self.ask('Select timezone', tzlist)
        self.vmware_timezone = tzlist[selection]

    def get_public_key(self):
        if not self.ssh_private_key:
            self.get_private_key()
        fh = open(self.ssh_private_key, 'r')
        key_pem = fh.read()
        fh.close()
        rsa_key = RSA.importKey(key_pem)
        modulus = rsa_key.n
        pubExpE = rsa_key.e
        priExpD = rsa_key.d
        primeP = rsa_key.p
        primeQ = rsa_key.q
        private_key = RSA.construct((modulus, pubExpE, priExpD, primeP, primeQ))
        public_key = private_key.public_key().exportKey('OpenSSH')
        self.ssh_public_key = public_key.decode('utf-8')

    def vmware_get_build_password(self):
        if not self.vmware_build_user:
            self.vmware_get_build_username()
        selection = self.ask_pass("Build user %s password" % self.vmware_build_user)
        self.vmware_build_password = selection
        self.vmware_build_pwd_encrypted = crypt.crypt(self.vmware_build_password, crypt.mksalt(crypt.METHOD_SHA512))

    def vmware_get_build_username(self):
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
                self.vmware_build_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate build user for %s %s linux." % (self.linux_type, self.linux_release))

    def vmware_get_network(self):
        if not self.vmware_hostname:
            self.vmware_get_hostname()
        folder = self.vmware_network_folder
        dvsList = []
        pgList = []
        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(folder, [vim.dvs.VmwareDistributedVirtualSwitch], True)
            for managed_object_ref in container.view:
                dvsList.append(managed_object_ref.name)
            container.Destroy()
            container = content.viewManager.CreateContainerView(folder, [vim.dvs.DistributedVirtualPortgroup], True)
            for managed_object_ref in container.view:
                pgList.append(managed_object_ref.name)
            container.Destroy()
            pgList = sorted(set(pgList))
            selection = self.ask('Select datastore', pgList)
            self.vmware_network = pgList[selection]
        except Exception:
            raise

    def vmware_get_disksize(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'vm_disk_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['vm_disk_size']
        self.logger.info("Default disk size is %s" % default_selection)
        selection = self.ask_text('Disk size', default_selection)
        self.vmware_disksize = selection

    def vmware_get_memsize(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'vm_mem_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['vm_mem_size']
        self.logger.info("Default memory size is %s" % default_selection)
        selection = self.ask_text('Memory size', default_selection)
        self.vmware_memsize = selection

    def vmware_get_cpucores(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'vm_cpu_cores' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['vm_cpu_cores']
        self.logger.info("Default CPU cores is %s" % default_selection)
        selection = self.ask_text('CPU cores', default_selection)
        self.vmware_cpucores = selection

    def vmware_get_isourl(self):
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
                self.vmware_iso = self.local_var_json['linux'][self.linux_type][i]['image']
                return True
        raise Exception("Can not locate ISO URL for %s %s linux." % (self.linux_type, self.linux_release))

    def vmware_get_ostype(self):
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
                self.vmware_ostype = self.local_var_json['linux'][self.linux_type][i]['type']
                return True
        raise Exception("Can not locate OS type for %s %s linux." % (self.linux_type, self.linux_release))

    def vmware_get_folder(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'folder' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['folder']
        self.logger.info("Default folder is %s" % default_selection)
        selection = self.ask_text('Folder', default_selection)
        self.vmware_folder = selection
        for folder in self.vmware_dc_folder.vmFolder.childEntity:
            if folder.name == self.vmware_folder:
                self.logger.info("Folder %s already exists." % self.vmware_folder)
                return True
        self.logger.info("Folder %s does not exist." % self.vmware_folder)
        print("Creating folder %s" % self.vmware_folder)
        try:
            self.vmware_dc_folder.vmFolder.CreateFolder(self.vmware_folder)
        except Exception:
            raise

    def vmware_get_datastore(self):
        if not self.vmware_hostname:
            self.vmware_get_hostname()
        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            datastore_name = []
            datastore_type = []
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
            esxi_hosts = container.view
            for esxi_host in esxi_hosts:
                storage_system = esxi_host.configManager.storageSystem
                host_file_sys_vol_mount_info = storage_system.fileSystemVolumeInfo.mountInfo
                for host_mount_info in host_file_sys_vol_mount_info:
                    if host_mount_info.volume.type == 'VFFS' or host_mount_info.volume.type == 'OTHER':
                        continue
                    datastore_name.append(host_mount_info.volume.name)
                    datastore_type.append(host_mount_info.volume.type)
            selection = self.ask('Select datastore', datastore_name, datastore_type)
            self.vmware_datastore = datastore_name[selection]
            container.Destroy()
            return True
        except Exception:
            raise

    def vmware_get_cluster(self):
        if not self.vmware_host_folder:
            self.vmware_get_datacenter()
        try:
            clusters = []
            for c in self.vmware_host_folder.childEntity:
                if isinstance(c, vim.ClusterComputeResource):
                    clusters.append(c.name)
            selection = self.ask('Select cluster', clusters)
            self.vmware_cluster = clusters[selection]
            return True
        except Exception:
            raise

    def vmware_get_datacenter(self):
        if not self.vmware_datacenter:
            self.vmware_get_hostname()

    def vmware_get_hostname(self):
        while True:
            if not self.vmware_hostname:
                hostname = input("vSphere Host Name: ")
                self.vmware_hostname = hostname.rstrip("\n")
            if not self.vmware_username:
                self.vmware_get_username()
            if not self.vmware_password:
                self.vmware_get_password()
            try:
                si = SmartConnectNoSSL(host=self.vmware_hostname,
                                       user=self.vmware_username,
                                       pwd=self.vmware_password,
                                       port=443)
                content = si.RetrieveContent()
                datacenter = []
                container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)
                for c in container.view:
                    datacenter.append(c.name)
                selection = self.ask('Select datacenter', datacenter)
                self.vmware_datacenter = datacenter[selection]
                for c in container.view:
                    if c.name == self.vmware_datacenter:
                        self.vmware_dc_folder = c
                        self.vmware_network_folder = c.networkFolder
                        self.vmware_host_folder = c.hostFolder
                container.Destroy()
                return True
            except Exception:
                print(" [!] Can not access vSphere with provided credentials.")

    def vmware_get_username(self):
        useranswer = input("vSphere Admin User: ")
        self.vmware_username = useranswer.rstrip("\n")
        if not self.vmware_password:
            self.vmware_get_password()

    def vmware_get_password(self):
        if not self.vmware_password:
            passanswer = getpass.getpass(prompt="vSphere Admin Password: ")
            self.vmware_password = passanswer.rstrip("\n")

    def aws_get_root_type(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_type' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_type']
        self.logger.info("Default root type is %s" % default_selection)
        selection = self.ask_text('Root volume type', default_selection)
        self.aws_root_type = selection

    def aws_get_root_size(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_size']
        self.logger.info("Default root size is %s" % default_selection)
        selection = self.ask_text('Root volume size', default_selection)
        self.aws_root_size = selection

    def aws_get_root_iops(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_iops' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_iops']
        self.logger.info("Default root IOPS is %s" % default_selection)
        selection = self.ask_text('Root volume IOPS', default_selection)
        self.aws_root_iops = selection

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
        self.aws_subnet_id = subnets['Subnets'][selection]['SubnetId']

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
        self.aws_ssh_key = key_pairs['KeyPairs'][selection]['KeyName']
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

    def ask_pass(self, question):
        while True:
            passanswer = getpass.getpass(prompt=question + ': ')
            passanswer = passanswer.rstrip("\n")
            checkanswer = getpass.getpass(prompt="Re-enter password: ")
            checkanswer = checkanswer.rstrip("\n")
            if passanswer == checkanswer:
                return passanswer
            else:
                print(" [!] Passwords do not match, please try again ...")

    def create_cluster_config(self):
        config_segments = []
        config_segments.append(CB_CFG_HEAD)
        node = 1
        node_ip_address = ''
        services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing', ]

        if self.dev_num:
            env_text = "dev{:02d}".format(self.dev_num)
        elif self.test_num:
            env_text = "tst{:02d}".format(self.test_num)
        elif self.prod_num:
            env_text = "prd{:02d}".format(self.prod_num)
        else:
            env_text = 'server'

        print("Building cluster configuration")
        while True:
            selected_services = []
            if node == 1:
                install_mode = 'init'
            else:
                install_mode = 'add'
            print("Configuring node %d" % node)
            for node_svc in services:
                if node_svc == 'data' or node_svc == 'index' or node_svc == 'query':
                    default_answer = 'y'
                else:
                    default_answer = 'n'
                answer = input(" -> %s (y/n) [%s]: " % (node_svc, default_answer))
                answer = answer.rstrip("\n")
                if len(answer) == 0:
                    answer = default_answer
                if answer == 'y' or answer == 'yes':
                    selected_services.append(node_svc)
            raw_template = jinja2.Template(CB_CFG_NODE)
            format_template = raw_template.render(
                NODE_ENV=env_text,
                NODE_NUMBER_FMT="{:02d}".format(node),
                NODE_NUMBER=node,
                NODE_SERVICES=','.join(selected_services),
                NODE_INSTALL_MODE=install_mode,
                NODE_IP_ADDRESS=node_ip_address,
            )
            config_segments.append(format_template)
            if node >= 3:
                answer = input("[?] Add another node? [y/n]: ")
                answer = answer.rstrip("\n")
                if answer == 'n' or answer == 'no':
                    break
            node += 1

        config_segments.append(CB_CFG_TAIL)
        output_file = 'cluster.tf'
        output_file = self.template_dir + '/' + output_file
        try:
            with open(output_file, 'w') as write_file:
                for i in range(len(config_segments)):
                    write_file.write(config_segments[i])
                write_file.write("\n")
                write_file.close()
        except OSError as e:
            print("Can not write to new cluster file: %s" % str(e))
            sys.exit(1)

    def create_env_dir(self, overwrite=False):
        parent_dir = os.path.dirname(self.template_dir)
        copy_files = [
            'locals.json',
            'main.tf',
            'variables.template',
            'outputs.tf',
        ]
        if not os.path.exists(self.template_dir):
            try:
                self.logger.info("Creating %s" % self.template_dir)
                os.mkdir(self.template_dir)
            except Exception as e:
                self.logger.error("create_env_dir: %s" % str(e))
                raise

        for file_name in copy_files:
            source = parent_dir + '/' + file_name
            destination = self.template_dir + '/' + file_name
            if not os.path.exists(destination) or overwrite:
                try:
                    self.logger.info("Copying %s -> %s" % (source, destination))
                    copyfile(source, destination)
                except Exception as e:
                    self.logger.error("create_env_dir: copy: %s: %s" % (source, str(e)))
                    raise

    def get_paths(self, refresh=False):
        if self.packer_mode:
            self.logger.info("get_paths: operating in packer mode.")
            relative_path = self.working_dir + '/' + 'packer'
            self.template_dir = relative_path
            self.logger.info("Template directory: %s" % self.template_dir)
            # self.template_file = self.template_dir + '/' + self.template_file
            self.logger.info("Template file: %s" % self.template_file)
            return True
        else:
            relative_path = self.working_dir + '/' + 'terraform'
            if self.dev_num:
                dev_directory = "dev-{:02d}".format(self.dev_num)
                self.template_dir = relative_path + '/' + dev_directory
            elif self.test_num:
                test_directory = "test-{:02d}".format(self.test_num)
                self.template_dir = relative_path + '/' + test_directory
            elif self.prod_num:
                prod_directory = "prod-{:02d}".format(self.prod_num)
                self.template_dir = relative_path + '/' + prod_directory
            else:
                raise Exception("Environment not specified.")
            try:
                self.create_env_dir(overwrite=refresh)
            except Exception as e:
                self.logger.error("get_paths: %s" % str(e))
                raise

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
