#!/usr/bin/env python3

'''
Build Terraform Config Files
'''

import logging
import os
import sys
import traceback
import argparse
import json
import re
import os
import getpass
from itertools import cycle
import subprocess
import crypt
import ipaddress
import socket
import dns.resolver
import dns.reversename
import dns.tsigkeyring
import dns.update
import jinja2
from jinja2.meta import find_undeclared_variables
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import xml.etree.ElementTree as ET
import gzip
import datetime
from passlib.hash import sha512_crypt
import string
import random
import readline
import base64
import math
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from Crypto.PublicKey import RSA
import hashlib
from shutil import copyfile
import pytz
try:
    from botocore.exceptions import ClientError
    import boto3
except ImportError:
    pass
try:
    from pyVim.connect import SmartConnectNoSSL, Disconnect
    from pyVmomi import vim, vmodl, VmomiSupport
except ImportError:
    pass
try:
    import googleapiclient.discovery
    from google.oauth2 import service_account
    # from google.cloud import resource_manager
except ImportError:
    pass
try:
    from azure.identity import AzureCliCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.storage import StorageManagementClient
    from azure.mgmt.resource.resources import ResourceManagementClient
    from azure.mgmt.resource.subscriptions import SubscriptionClient
except ImportError:
    pass

PUBLIC_CLOUD = True
MODE_TFVAR = 0x0001
MODE_CLUSTER_MAP = 0x0002
MODE_PACKER = 0x0003
MODE_KUBE_MAP = 0x0004

CB_CFG_HEAD = """####
variable "cluster_spec" {
  description = "Map of cluster nodes and services."
  type        = map
  default     = {"""

CB_CFG_NODE = """
    {{ NODE_NAME }} = {
      node_number     = {{ NODE_NUMBER }},
      node_services   = "{{ NODE_SERVICES }}",
      install_mode    = "{{ NODE_INSTALL_MODE }}",
      node_zone       = "{{ NODE_ZONE }}",
      node_subnet     = "{{ NODE_SUBNET }}",
      node_ip_address = "{{ NODE_IP_ADDRESS }}",
      node_netmask    = "{{ NODE_NETMASK }}",
      node_gateway    = "{{ NODE_GATEWAY }}",
    }
"""

CB_CFG_TAIL = """
  }
}
"""

class ask(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def ask_list(self, question, options=[], descriptions=[]):
        list_start = 1
        list_lenghth = len(options)
        list_remaining = list_lenghth
        list_incr = 15
        list_end = list_lenghth
        if list_lenghth == 1:
            return 0
        print("%s:" % question)
        while True:
            if list_remaining <= list_incr:
                list_end = list_lenghth
            else:
                list_end = list_start + list_incr - 1
            for i in range(list_start, list_end + 1):
                if type(options[i-1]) is dict:
                    if 'name' not in options[i-1]:
                        raise Exception("ask_list: name not found in option entry")
                    option_display = options[i-1]['name']
                else:
                    option_display = options[i-1]
                if i <= len(descriptions):
                    extra = '(' + descriptions[i-1] + ')'
                elif type(options[i-1]) is dict and 'description' in options[i-1]:
                    extra = '(' + options[i-1]['description'] + ')'
                else:
                    extra = ''
                print(" %02d) %s %s" % (i, option_display, extra))
            if list_end == list_lenghth:
                answer = input("Selection [q=quit]: ")
            else:
                answer = input("Selection [n=next, q=quit]: ")
            answer = answer.rstrip("\n")
            if answer == 'n':
                list_start += list_incr
                list_remaining = list_remaining - list_incr
                continue
            if answer == 'q':
                sys.exit(0)
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

    def ask_long_list(self, question, options=[], descriptions=[], separator='.'):
        merged_list = [(options[i], descriptions[i]) for i in range(len(options))]
        sorted_list = sorted(merged_list, key=lambda option: option[0])
        options, descriptions = map(list, zip(*sorted_list))
        subselection_list = []
        new_option_list = []
        new_description_list = []
        for item in options:
            prefix = item.split(separator)[0]
            subselection_list.append(prefix)
        subselection_list = sorted(set(subselection_list))
        selection = self.ask_list(question + ' subselection', subselection_list)
        limit_prefix = subselection_list[selection]
        for i in range(len(options)):
            if options[i].startswith(limit_prefix + separator):
                new_option_list.append(options[i])
                if i < len(descriptions):
                    new_description_list.append(descriptions[i])
        selection = self.ask_list(question, new_option_list, new_description_list)
        return new_option_list[selection]

    def ask_machine_type(self, question, options=[]):
        cpu_list = []
        mem_list = []
        name_list = []
        description_list = []
        select_list = []
        num_cpu = None
        num_mem = None
        try:
            for item in options:
                cpu_list.append(item['cpu'])
                mem_list.append(item['mem'])
        except KeyError:
            raise Exception("ask_machine_type: invalid options argument")
        cpu_set = set(cpu_list)
        mem_set = set(mem_list)
        cpu_list = sorted(list(cpu_set))
        mem_list = sorted(list(mem_set))
        selection = self.ask_list('CPU count', cpu_list)
        num_cpu = cpu_list[selection]
        selection = self.ask_list('Memory', mem_list)
        num_mem = mem_list[selection]
        try:
            for i in range(len(options)):
                if options[i]['cpu'] == num_cpu and options[i]['mem'] == num_mem:
                    name_list.append(options[i]['name'])
                    if 'description' in options[i]:
                        description_list.append(options[i]['description'])
                    select_list.append(i)
        except KeyError:
            raise Exception("ask_machine_type: invalid options argument")
        if len(description_list) > 0:
            selection = self.ask_list(question, name_list, description_list)
        else:
            selection = self.ask_list(question, name_list)
        return select_list[selection]

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

    def ask_yn(self, question, default=False):
        if default:
            default_answer = 'y'
        else:
            default_answer = 'n'
        while True:
            prompt = "{} (y/n) [{}]? ".format(question, default_answer)
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                answer = default_answer
            if answer == 'Y' or answer == 'y' or answer == 'yes':
                return True
            elif answer == 'N' or answer == 'n' or answer == 'no':
                return False
            else:
                print(" [!] Unrecognized answer, please try again...")

    def ask_ip(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            try:
                ip = ipaddress.ip_address(answer)
                return answer
            except ValueError:
                print("%s does not appear to be an IP address." % answer)
                continue

    def ask_net(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            try:
                net = ipaddress.ip_network(answer)
                return answer
            except ValueError:
                print("%s does not appear to be an IP network." % answer)
                continue

    def ask_net_range(self, question):
        while True:
            prompt = question + ': '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                return None
            try:
                (first, last) = answer.split('-')
                ip_first = ipaddress.ip_address(first)
                ip_last = ipaddress.ip_address(last)
                return answer
            except Exception:
                print("Invalid input, please try again...")
                continue

    def ask_bool(self, question, default='true'):
        while True:
            prompt = question + ' [' + default + ']: '
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                answer = default
            try:
                if answer == 'true' or answer == 'false':
                    return answer
                else:
                    raise Exception("please answer true or false")
            except Exception as e:
                print("Invalid input: %s, please try again..." % str(e))
                continue

class dynamicDNS(object):

    def __init__(self, domain, type='tsig'):
        self.type = type
        self.dns_server = None
        self.dns_domain = domain
        self.zone_name = None
        self.tsig_keyName = None
        self.tsig_keyAlgorithm = None
        self.tsig_key = None
        self.free_list = []
        self.homeDir = os.environ['HOME']
        self.dnsKeyPath = self.homeDir + "/.dns"
        self.dnsKeyFile = self.dnsKeyPath + "/{}.key".format(domain)

    def dns_prep(self):
        if self.type == 'tsig':
            return self.tsig_config()
        else:
            print("dns_prep: Unsupported type %s" % type)
            return False

    def dns_update(self, hostname, domain, address, prefix):
        if self.type == 'tsig':
            return self.tsig_update(hostname, domain, address, prefix)
        else:
            print("dns_update: Unsupported type %s" % type)
            return False

    def dns_get_servers(self):
        server_list = []
        resolver = dns.resolver.Resolver()
        try:
            ns_answer = resolver.resolve(self.dns_domain, 'NS')
            for server in ns_answer:
                ip_answer = resolver.resolve(server.target, 'A')
                for ip in ip_answer:
                    server_list.append(ip.address)
            return server_list
        except dns.resolver.NXDOMAIN as e:
            raise Exception("dns_get_servers: the domain %s does not exist." % self.dns_domain)

    def dns_zone_xfer(self):
        address_list = []
        for dns_server in self.dns_get_servers():
            try:
                zone = dns.zone.from_xfr(dns.query.xfr(dns_server, self.dns_domain))
                for (name, ttl, rdata) in zone.iterate_rdatas(rdtype='A'):
                    address_list.append(rdata.to_text())
                return address_list
            except Exception as e:
                continue
        return []

    def dns_get_range(self, network, omit=None):
        address_list = self.dns_zone_xfer()
        subnet_list = []
        free_list = []
        if len(address_list) > 0:
            try:
                address_list = sorted(address_list)
                for ip in address_list:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(network):
                        subnet_list.append(ip)
                for all_ip in ipaddress.ip_network(network).hosts():
                    if not any(str(all_ip) in address for address in subnet_list):
                        if int(str(all_ip).split('.')[3]) >= 10:
                            free_list.append(str(all_ip))
                if omit:
                    try:
                        (first, last) = omit.split('-')
                        for ipaddr in ipaddress.summarize_address_range(ipaddress.IPv4Address(first),
                                                                        ipaddress.IPv4Address(last)):
                            for omit_ip in ipaddr:
                                if any(str(omit_ip) in address for address in free_list):
                                    free_list.remove(str(omit_ip))
                    except Exception as e:
                        print("dns_get_range: problem with omit range %s: %s" % (omit, str(e)))
                        return False
                self.free_list = free_list
                return True
            except Exception as e:
                print("dns_get_range: can not get free IP range from subnet %s: %s" % (network, str(e)))
                return False
        else:
            return False

    @property
    def get_free_ip(self):
        if len(self.free_list) > 0:
            return self.free_list.pop(0)
        else:
            return None

    @property
    def free_list_size(self):
        return len(self.free_list)

    def tsig_config(self):
        inquire = ask()
        algorithms = ['HMAC_MD5',
                      'HMAC_SHA1',
                      'HMAC_SHA224',
                      'HMAC_SHA256',
                      'HMAC_SHA256_128',
                      'HMAC_SHA384',
                      'HMAC_SHA384_192',
                      'HMAC_SHA512',
                      'HMAC_SHA512_256']

        if os.path.exists(self.dnsKeyFile):
            try:
                with open(self.dnsKeyFile, 'r') as keyFile:
                    try:
                        keyData = json.load(keyFile)
                    except ValueError as e:
                        print("DNS key file ~/.dns/dns.key does not contain valid JSON data: %s" % str(e))
                        return False
                    try:
                        self.tsig_key = keyData['dnskey']
                        self.tsig_keyName = keyData['keyname']
                        self.tsig_keyAlgorithm = keyData['algorithm']
                        self.dns_server = keyData['server']
                        self.tsig_keyName = self.tsig_keyName + '.'
                        return True
                    except KeyError:
                        print("DNS key file ~/.dns/dns.key does not contain TSIG key attributes.")
                        return False
            except OSError as e:
                print("Could not read dns key file: %s" % str(e))
                sys.exit(1)
        else:
            if not os.path.exists(self.dnsKeyPath):
                try:
                    os.mkdir(self.dnsKeyPath)
                except OSError as e:
                    print("Could not create dns key store path: %s" % str(e))
                    return False
            keyData = {}
            self.dns_server = keyData['server'] = inquire.ask_text('DNS Server IP Address')
            self.tsig_keyName = keyData['keyname'] = inquire.ask_text('TSIG Key Name')
            self.tsig_key = keyData['dnskey'] = inquire.ask_text('TSIG Key')
            selection = inquire.ask_list('Key Algorithm', algorithms)
            self.tsig_keyAlgorithm = keyData['algorithm'] = algorithms[selection]
            self.tsig_keyName = self.tsig_keyName + '.'
            try:
                with open(self.dnsKeyFile, 'w') as keyFile:
                    json.dump(keyData, keyFile, indent=2)
                    keyFile.write("\n")
                    keyFile.close()
            except OSError as e:
                print("Could not write dns key file: %s" % str(e))
                return False
            return True

    def tsig_update(self, hostname, domain, address, prefix):
        response = None
        try:
            host_fqdn = hostname + '.' + domain + '.'
            last_octet = address.split('.')[3]
            octets = 4 - math.trunc(prefix / 8)
            reverse = dns.reversename.from_address(address)
            arpa_zone = b'.'.join(dns.name.from_text(str(reverse)).labels[octets:]).decode('utf-8')
            keyring = dns.tsigkeyring.from_text({self.tsig_keyName: self.tsig_key})
            update = dns.update.Update(self.dns_domain, keyring=keyring, keyalgorithm=getattr(dns.tsig, self.tsig_keyAlgorithm))
            update.add(host_fqdn, 8600, 'A', address)
            response = dns.query.tcp(update, self.dns_server)
            update = dns.update.Update(arpa_zone, keyring=keyring, keyalgorithm=getattr(dns.tsig, self.tsig_keyAlgorithm))
            update.add(last_octet, 8600, 'PTR', host_fqdn)
            response = dns.query.tcp(update, self.dns_server)
            return True
        except Exception as e:
            rcode = dns.rcode.to_text(response.rcode())
            print("tsig_update: failed for %s server returned %s error %s" % (hostname, str(rcode), str(e)))
            return False

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
                version = version.strip()
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
        parser.add_argument('--singlezone', action='store_true', help="Use One Availability Zone", default=False)
        parser.add_argument('--refresh', action='store_true', help="Packer file", default=False)
        parser.add_argument('--host', action='store', help="Host Name")
        parser.add_argument('--user', action='store', help="Host User")
        parser.add_argument('--password', action='store', help="Host Password")
        parser.add_argument('--static', action='store_true', help="Assign Static IPs", default=False)
        parser.add_argument('--dns', action='store_true', help="Update DNS", default=False)
        parser.add_argument('--gateway', action='store', help="Default Gateway")
        parser.add_argument('--domain', action='store', help="DNS Domain")
        parser.add_argument('--subnet', action='store', help="Network Subnet")
        parser.add_argument('--omit', action='store', help="Network Subnet")
        self.parser = parser

class processTemplate(object):

    def __init__(self, pargs):
        self.debug = pargs.debug
        self.operating_mode = MODE_TFVAR
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
        self.location = pargs.location
        self.static_ip = pargs.static
        self.update_dns = pargs.dns
        self.subnet_cidr = pargs.subnet
        self.subnet_netmask = None
        self.default_gateway = pargs.gateway
        self.omit_range = pargs.omit
        self.use_public_ip = False
        self.use_single_zone = pargs.singlezone
        self.availability_zone_cycle = None
        self.packer_mode = pargs.packer
        self.globals_file = None
        self.locals_file = None
        self.linux_type = None
        self.linux_release = None
        self.linux_pkgmgr = None
        self.ssh_private_key = None
        self.ssh_public_key = None
        self.ssh_public_key_file = None
        self.ssh_key_fingerprint = None
        self.domain_name = pargs.domain
        self.dns_server = None
        self.dns_server_list = None
        self.cb_version = None
        self.cb_index_mem_type = None
        self.aws_image_name = None
        self.aws_image_owner = None
        self.aws_image_user = None
        self.aws_region = None
        self.aws_availability_zones = []
        self.aws_ami_id = None
        self.aws_instance_type = None
        self.aws_ssh_key = None
        self.aws_subnet_id = None
        self.aws_subnet_list = []
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
        self.vmware_iso_checksum = None
        self.vmware_sw_url = None
        self.vmware_build_user = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_timezone = None
        self.vmware_key = None
        self.vmware_dc_folder = None
        self.vmware_network_folder = None
        self.vmware_host_folder = None
        self.vmware_dvs = None
        self.vmware_template = None
        self.gcp_account_file = None
        self.gcp_image_name = None
        self.gcp_cb_image = None
        self.gcp_image_family = None
        self.gcp_project = None
        self.gcp_auth_json_project_id = None
        self.gcp_image_user = None
        self.gcp_zone = None
        self.gcp_zone_list = []
        self.gcp_region = None
        self.gcp_machine_type = None
        self.gcp_subnet = None
        self.gcp_root_size = None
        self.gcp_root_type = None
        self.gcp_service_account_email = None
        self.azure_subscription_id = None
        self.azure_resource_group = None
        self.azure_image_publisher = None
        self.azure_image_offer = None
        self.azure_image_sku = None
        self.azure_location = None
        self.azure_availability_zones = []
        self.azure_vnet = None
        self.azure_subnet = None
        self.azure_nsg = None
        self.azure_image_name = None
        self.azure_machine_type = None
        self.azure_admin_user = None
        self.azure_disk_type = None
        self.azure_disk_size = None
        self.global_var_json = {}
        self.local_var_json = {}
        self.supported_variable_list = [
            ('AWS_AMI_ID', 0),
            ('AWS_AMI_OWNER', 2),
            ('AWS_AMI_USER', 2),
            ('AWS_IMAGE', 2),
            ('AWS_INSTANCE_TYPE', 2),
            ('AWS_REGION', 2),
            ('AWS_ROOT_IOPS', 2),
            ('AWS_ROOT_SIZE', 2),
            ('AWS_ROOT_TYPE', 2),
            ('AWS_SECURITY_GROUP', 2),
            ('AWS_SSH_KEY', 0),
            ('AWS_SUBNET_ID', 2),
            ('AWS_VPC_ID', 2),
            ('AZURE_ADMIN_USER', 2),
            ('AZURE_DISK_SIZE', 2),
            ('AZURE_DISK_TYPE', 2),
            ('AZURE_IMAGE_NAME', 0),
            ('AZURE_LOCATION', 2),
            ('AZURE_MACHINE_TYPE', 2),
            ('AZURE_NSG', 2),
            ('AZURE_OFFER', 2),
            ('AZURE_PUBLISHER', 2),
            ('AZURE_RG', 2),
            ('AZURE_SKU', 2),
            ('AZURE_SUBNET', 2),
            ('AZURE_SUBSCRIPTION_ID', 2),
            ('AZURE_VNET', 2),
            ('CB_INDEX_MEM_TYPE', 2),
            ('CB_VERSION', 2),
            ('DNS_SERVER_LIST', 2),
            ('DOMAIN_NAME', 2),
            ('GCP_ACCOUNT_FILE', 2),
            ('GCP_CB_IMAGE', 0),
            ('GCP_IMAGE', 2),
            ('GCP_IMAGE_FAMILY', 2),
            ('GCP_IMAGE_USER', 2),
            ('GCP_MACHINE_TYPE', 2),
            ('GCP_PROJECT', 2),
            ('GCP_REGION', 2),
            ('GCP_ROOT_SIZE', 2),
            ('GCP_ROOT_TYPE', 2),
            ('GCP_SA_EMAIL', 2),
            ('GCP_SUBNET', 2),
            ('GCP_ZONE', 2),
            ('LINUX_RELEASE', 1),
            ('LINUX_TYPE', 1),
            ('SSH_PRIVATE_KEY', 1),
            ('SSH_PUBLIC_KEY_FILE', 2),
            ('USE_PUBLIC_IP', 2),
            ('VMWARE_BUILD_PASSWORD', 2),
            ('VMWARE_BUILD_PWD_ENCRYPTED', 2),
            ('VMWARE_BUILD_USERNAME', 2),
            ('VMWARE_CLUSTER', 2),
            ('VMWARE_CPU_CORES', 2),
            ('VMWARE_DATACENTER', 2),
            ('VMWARE_DATASTORE', 2),
            ('VMWARE_DISK_SIZE', 2),
            ('VMWARE_DVS', 2),
            ('VMWARE_FOLDER', 2),
            ('VMWARE_HOSTNAME', 0),
            ('VMWARE_ISO_CHECKSUM', 2),
            ('VMWARE_ISO_URL', 2),
            ('VMWARE_KEY', 2),
            ('VMWARE_MEM_SIZE', 2),
            ('VMWARE_NETWORK', 2),
            ('VMWARE_OS_TYPE', 2),
            ('VMWARE_PASSWORD', 0),
            ('VMWARE_SW_URL', 2),
            ('VMWARE_TEMPLATE', 1),
            ('VMWARE_TIMEZONE', 2),
            ('VMWARE_USERNAME', 0),
        ]
        inquire = ask()

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
            self.operating_mode = MODE_CLUSTER_MAP
            try:
                self.create_cluster_config()
            except Exception as e:
                print("Error: %s" % str(e))
                sys.exit(1)
            print("Cluster configuration complete.")
            sys.exit(0)
        elif pargs.packer:
            self.operating_mode = MODE_PACKER

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

        sorted_token_list = [tuple for x in requested_vars for tuple in self.supported_variable_list if tuple[0] == x]
        sorted_token_list = sorted(sorted_token_list, key=lambda tuple: tuple[1])

        for count, tuple in enumerate(sorted_token_list):
            item = tuple[0]
            self.logger.info("Processing variable %s" % item)
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
                        self.vmware_get_dvs_network()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_NETWORK = %s" % self.vmware_network)
            elif item == 'VMWARE_DVS':
                if not self.vmware_dvs:
                    try:
                        self.vmware_get_dvs_network()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_DVS = %s" % self.vmware_dvs)
            elif item == 'VMWARE_ISO_URL':
                if not self.vmware_iso:
                    try:
                        self.vmware_get_isourl()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_ISO_URL = %s" % self.vmware_iso)
            elif item == 'VMWARE_ISO_CHECKSUM':
                if not self.vmware_iso_checksum:
                    try:
                        self.vmware_get_iso_checksum()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_ISO_CHECKSUM = %s" % self.vmware_iso_checksum)
            elif item == 'VMWARE_SW_URL':
                if not self.vmware_sw_url:
                    try:
                        self.vmware_get_sw_url()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_SW_URL = %s" % self.vmware_sw_url)
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
            elif item == 'VMWARE_TEMPLATE':
                if not self.vmware_template:
                    try:
                        self.vmware_get_template()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("VMWARE_TEMPLATE = %s" % self.vmware_template)
            elif item == 'DOMAIN_NAME':
                if not self.domain_name:
                    try:
                        self.get_domain_name()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("DOMAIN_NAME = %s" % self.domain_name)
            elif item == 'DNS_SERVER_LIST':
                if not self.dns_server_list:
                    try:
                        self.get_dns_servers()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("DNS_SERVER_LIST = %s" % self.dns_server_list)
            elif item == 'GCP_ACCOUNT_FILE':
                if not self.gcp_account_file:
                    try:
                        self.gcp_get_account_file()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_ACCOUNT_FILE = %s" % self.gcp_account_file)
            elif item == 'GCP_IMAGE':
                if not self.gcp_image_name:
                    try:
                        self.get_gcp_image_name()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_IMAGE = %s" % self.gcp_image_name)
            elif item == 'GCP_IMAGE_FAMILY':
                if not self.gcp_image_family:
                    try:
                        self.get_gcp_image_family()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_IMAGE_FAMILY = %s" % self.gcp_image_family)
            elif item == 'GCP_IMAGE_USER':
                if not self.gcp_image_user:
                    try:
                        self.get_gcp_image_user()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_IMAGE_USER = %s" % self.gcp_image_user)
            elif item == 'GCP_PROJECT':
                if not self.gcp_project:
                    try:
                        self.get_gcp_project()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_PROJECT = %s" % self.gcp_project)
            elif item == 'GCP_ZONE':
                if not self.gcp_zone:
                    try:
                        self.get_gcp_zones()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_ZONE = %s" % self.gcp_zone)
            elif item == 'GCP_REGION':
                if not self.gcp_region:
                    try:
                        self.get_gcp_region()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_REGION = %s" % self.gcp_region)
            elif item == 'GCP_CB_IMAGE':
                if not self.gcp_cb_image:
                    try:
                        self.gcp_get_cb_image_name()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_CB_IMAGE = %s" % self.gcp_cb_image)
            elif item == 'GCP_MACHINE_TYPE':
                if not self.gcp_machine_type:
                    try:
                        self.gcp_get_machine_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_MACHINE_TYPE = %s" % self.gcp_machine_type)
            elif item == 'GCP_SUBNET':
                if not self.gcp_subnet:
                    try:
                        self.gcp_get_subnet()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_SUBNET = %s" % self.gcp_subnet)
            elif item == 'GCP_ROOT_SIZE':
                if not self.gcp_root_size:
                    try:
                        self.gcp_get_root_size()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_ROOT_SIZE = %s" % self.gcp_root_size)
            elif item == 'GCP_ROOT_TYPE':
                if not self.gcp_root_type:
                    try:
                        self.gcp_get_root_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_ROOT_TYPE = %s" % self.gcp_root_type)
            elif item == 'SSH_PUBLIC_KEY_FILE':
                if not self.ssh_public_key_file:
                    try:
                        self.get_ssh_public_key_file()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("SSH_PUBLIC_KEY_FILE = %s" % self.ssh_public_key_file)
            elif item == 'GCP_SA_EMAIL':
                if not self.gcp_service_account_email:
                    try:
                        self.gcp_get_account_file()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("GCP_SA_EMAIL = %s" % self.gcp_service_account_email)
            elif item == 'AZURE_SUBSCRIPTION_ID':
                if not self.azure_subscription_id:
                    try:
                        self.azure_get_subscription_id()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_SUBSCRIPTION_ID = %s" % self.azure_subscription_id)
            elif item == 'AZURE_RG':
                if not self.azure_resource_group:
                    try:
                        self.azure_get_resource_group()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_RG = %s" % self.azure_resource_group)
            elif item == 'AZURE_LOCATION':
                if not self.azure_location:
                    try:
                        self.azure_get_location()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_LOCATION = %s" % self.azure_location)
            elif item == 'AZURE_PUBLISHER':
                if not self.azure_image_publisher:
                    try:
                        self.azure_get_image_publisher()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_PUBLISHER = %s" % self.azure_image_publisher)
            elif item == 'AZURE_OFFER':
                if not self.azure_image_offer:
                    try:
                        self.azure_get_image_offer()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_OFFER = %s" % self.azure_image_offer)
            elif item == 'AZURE_SKU':
                if not self.azure_image_sku:
                    try:
                        self.azure_get_image_sku()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_SKU = %s" % self.azure_image_sku)
            elif item == 'AZURE_VNET':
                if not self.azure_vnet:
                    try:
                        self.azure_get_vnet()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_VNET = %s" % self.azure_vnet)
            elif item == 'AZURE_SUBNET':
                if not self.azure_subnet:
                    try:
                        self.azure_get_subnet()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_SUBNET = %s" % self.azure_subnet)
            elif item == 'AZURE_NSG':
                if not self.azure_nsg:
                    try:
                        self.azure_get_nsg()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_NSG = %s" % self.azure_nsg)
            elif item == 'AZURE_IMAGE_NAME':
                if not self.azure_image_name:
                    try:
                        self.azure_get_image_name()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_IMAGE_NAME = %s" % self.azure_image_name)
            elif item == 'AZURE_MACHINE_TYPE':
                if not self.azure_machine_type:
                    try:
                        self.azure_get_machine_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_MACHINE_TYPE = %s" % self.azure_machine_type)
            elif item == 'AZURE_ADMIN_USER':
                if not self.azure_admin_user:
                    try:
                        self.azure_get_image_user()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_ADMIN_USER = %s" % self.azure_admin_user)
            elif item == 'AZURE_DISK_TYPE':
                if not self.azure_disk_type:
                    try:
                        self.azure_get_root_type()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_DISK_TYPE = %s" % self.azure_disk_type)
            elif item == 'AZURE_DISK_SIZE':
                if not self.azure_disk_size:
                    try:
                        self.azure_get_root_size()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("AZURE_DISK_SIZE = %s" % self.azure_disk_size)
            elif item == 'USE_PUBLIC_IP':
                if not self.use_public_ip:
                    try:
                        self.ask_to_use_public_ip()
                    except Exception as e:
                        print("Error: %s" % str(e))
                        sys.exit(1)
                self.logger.info("USE_PUBLIC_IP = %s" % self.use_public_ip)

        raw_template = jinja2.Template(raw_input)
        format_template = raw_template.render(
                                              CB_VERSION=self.cb_version,
                                              LINUX_TYPE=self.linux_type,
                                              LINUX_RELEASE=self.linux_release,
                                              DOMAIN_NAME=self.domain_name,
                                              DNS_SERVER_LIST=self.dns_server_list,
                                              USE_PUBLIC_IP=self.use_public_ip,
                                              AWS_IMAGE=self.aws_image_name,
                                              AWS_AMI_OWNER=self.aws_image_owner,
                                              AWS_AMI_USER=self.aws_image_user,
                                              AWS_REGION=self.aws_region,
                                              AWS_AMI_ID=self.aws_ami_id,
                                              AWS_INSTANCE_TYPE=self.aws_instance_type,
                                              CB_INDEX_MEM_TYPE=self.cb_index_mem_type,
                                              AWS_SSH_KEY=self.aws_ssh_key,
                                              SSH_PRIVATE_KEY=self.ssh_private_key,
                                              SSH_PUBLIC_KEY_FILE=self.ssh_public_key_file,
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
                                              VMWARE_DVS=self.vmware_dvs,
                                              VMWARE_ISO_CHECKSUM=self.vmware_iso_checksum,
                                              VMWARE_SW_URL=self.vmware_sw_url,
                                              VMWARE_BUILD_USERNAME=self.vmware_build_user,
                                              VMWARE_BUILD_PASSWORD=self.vmware_build_password,
                                              VMWARE_BUILD_PWD_ENCRYPTED=self.vmware_build_pwd_encrypted,
                                              VMWARE_TIMEZONE=self.vmware_timezone,
                                              VMWARE_KEY=self.ssh_public_key,
                                              VMWARE_TEMPLATE=self.vmware_template,
                                              GCP_ACCOUNT_FILE=self.gcp_account_file,
                                              GCP_IMAGE=self.gcp_image_name,
                                              GCP_IMAGE_FAMILY=self.gcp_image_family,
                                              GCP_PROJECT=self.gcp_project,
                                              GCP_IMAGE_USER=self.gcp_image_user,
                                              GCP_ZONE=self.gcp_zone,
                                              GCP_REGION=self.gcp_region,
                                              GCP_MACHINE_TYPE=self.gcp_machine_type,
                                              GCP_SUBNET=self.gcp_subnet,
                                              GCP_ROOT_SIZE=self.gcp_root_size,
                                              GCP_ROOT_TYPE=self.gcp_root_type,
                                              GCP_CB_IMAGE=self.gcp_cb_image,
                                              GCP_SA_EMAIL=self.gcp_service_account_email,
                                              AZURE_SUBSCRIPTION_ID=self.azure_subscription_id,
                                              AZURE_RG=self.azure_resource_group,
                                              AZURE_PUBLISHER=self.azure_image_publisher,
                                              AZURE_OFFER=self.azure_image_offer,
                                              AZURE_SKU=self.azure_image_sku,
                                              AZURE_LOCATION=self.azure_location,
                                              AZURE_VNET=self.azure_vnet,
                                              AZURE_SUBNET=self.azure_subnet,
                                              AZURE_NSG=self.azure_nsg,
                                              AZURE_IMAGE_NAME=self.azure_image_name,
                                              AZURE_MACHINE_TYPE=self.azure_machine_type,
                                              AZURE_ADMIN_USER=self.azure_admin_user,
                                              AZURE_DISK_TYPE=self.azure_disk_type,
                                              AZURE_DISK_SIZE=self.azure_disk_size,
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

        if self.operating_mode == MODE_TFVAR:
            cluster_map_file = 'cluster.tf'
            cluster_map_path = self.template_dir + '/' + cluster_map_file
            if not os.path.exists(cluster_map_path) or pargs.refresh:
                try:
                    self.create_cluster_config()
                except Exception as e:
                    print("Error: %s" % str(e))
                    sys.exit(1)
                print("Cluster configuration complete.")

    def ask_to_use_public_ip(self):
        inquire = ask()
        selection = inquire.ask_bool('Use Public IP', default='false')
        self.use_public_ip = selection

    def get_dns_servers(self):
        server_list = []
        dns_lookup = dynamicDNS(self.domain_name)
        server_list = dns_lookup.dns_get_servers()
        self.dns_server_list = ','.join(f'"{s}"' for s in server_list)

    def azure_get_root_type(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_type']
        self.logger.info("Default root size is %s" % default_selection)
        selection = self.ask_text('Root volume size', default_selection)
        self.azure_disk_type = selection

    def azure_get_root_size(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_size']
        self.logger.info("Default root size is %s" % default_selection)
        selection = self.ask_text('Root volume size', default_selection)
        self.azure_disk_size = selection

    def azure_get_image_user(self):
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
                self.azure_admin_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable user for %s %s linux." % (self.linux_type, self.linux_release))

    def azure_get_machine_type(self):
        inquire = ask()
        size_list = []
        if not self.azure_location:
            self.azure_get_location()
        if self.azure_machine_type:
            return
        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        sizes = compute_client.virtual_machine_sizes.list(self.azure_location)
        for group in list(sizes):
            config_block = {}
            config_block['name'] = group.name
            config_block['cpu'] = group.number_of_cores
            config_block['mem'] = int(group.memory_in_mb / 1024)
            size_list.append(config_block)
        selection = inquire.ask_machine_type('Azure Machine Type', size_list)
        self.azure_machine_type = size_list[selection]['name']

    def azure_get_image_name(self):
        inquire = ask()
        image_list = []
        if not self.azure_resource_group:
            self.azure_get_resource_group()
        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        images = compute_client.images.list_by_resource_group(self.azure_resource_group)
        for group in list(images):
            image_block = {}
            image_block['name'] = group.name
            if 'Type' in group.tags:
                image_block['type'] = group.tags['Type']
            if 'Release' in group.tags:
                image_block['release'] = group.tags['Release']
            if 'Version' in group.tags:
                image_block['version'] = image_block['description'] = group.tags['Version']
            image_list.append(image_block)
        selection = inquire.ask_list('Azure Image Name', image_list)
        self.azure_image_name = image_list[selection]['name']
        if 'type' in image_list[selection]:
            self.linux_type = image_list[selection]['type']
            self.logger.info("Selecting linux type %s from image metadata" % self.linux_type)
        if 'release' in image_list[selection]:
            self.linux_release = image_list[selection]['release']
            self.logger.info("Selecting linux release %s from image metadata" % self.linux_release)
        if 'version' in image_list[selection]:
            self.cb_version = image_list[selection]['version']
            self.logger.info("Selecting couchbase version %s from image metadata" % self.cb_version)

    def azure_get_nsg(self):
        inquire = ask()
        nsg_list = []
        if not self.azure_resource_group:
            self.azure_get_resource_group()
        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        nsgs = network_client.network_security_groups.list(self.azure_resource_group)
        for group in list(nsgs):
            nsg_list.append(group.name)
        selection = inquire.ask_list('Azure Network Security Group', nsg_list)
        self.azure_nsg = nsg_list[selection]

    def azure_get_subnet(self):
        inquire = ask()
        subnet_list = []
        if not self.azure_vnet:
            self.azure_get_vnet()
        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        subnets = network_client.subnets.list(self.azure_resource_group, self.azure_vnet)
        for group in list(subnets):
            subnet_list.append(group.name)
        selection = inquire.ask_list('Azure Subnet', subnet_list)
        self.azure_subnet = subnet_list[selection]

    def azure_get_vnet(self):
        inquire = ask()
        vnet_list = []
        if not self.azure_resource_group:
            self.azure_get_resource_group()
        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        vnetworks = network_client.virtual_networks.list(self.azure_resource_group)
        for group in list(vnetworks):
            vnet_list.append(group.name)
        selection = inquire.ask_list('Azure Virtual Network', vnet_list)
        self.azure_vnet = vnet_list[selection]

    def azure_get_image_sku(self):
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
                self.azure_image_sku = self.local_var_json['linux'][self.linux_type][i]['sku']
                return True
        raise Exception("Can not locate suitable sku for %s %s linux." % (self.linux_type, self.linux_release))

    def azure_get_image_offer(self):
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
                self.azure_image_offer = self.local_var_json['linux'][self.linux_type][i]['offer']
                return True
        raise Exception("Can not locate suitable offer for %s %s linux." % (self.linux_type, self.linux_release))

    def azure_get_image_publisher(self):
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
                self.azure_image_publisher = self.local_var_json['linux'][self.linux_type][i]['publisher']
                return True
        raise Exception("Can not locate suitable publisher for %s %s linux." % (self.linux_type, self.linux_release))

    def azure_get_all_locations(self):
        inquire = ask()
        location_list = []
        location_name = []
        if not self.azure_subscription_id:
            self.azure_get_subscription_id()
        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        locations = subscription_client.subscriptions.list_locations(self.azure_subscription_id)
        for group in list(locations):
            location_list.append(group.name)
            location_name.append(group.display_name)
        selection = inquire.ask_list('Azure Location', location_list, location_name)
        self.azure_location = location_list[selection]

    def azure_get_location(self):
        inquire = ask()
        location_list = []
        location_name = []
        if not self.azure_resource_group:
            self.azure_get_resource_group()
        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, self.azure_subscription_id)
        resource_group = resource_client.resource_groups.list()
        for group in list(resource_group):
            if group.name == self.azure_resource_group:
                location_list.append(group.location)
        selection = inquire.ask_list('Azure Location', location_list, location_name)
        self.azure_location = location_list[selection]
        self.azure_get_machine_type()
        self.azure_get_zones()

    def azure_get_zones(self):
        if not self.azure_location:
            self.azure_get_location()
        if len(self.azure_availability_zones) > 0:
            return
        print("Fetching Azure zone information, this may take a few minutes...")
        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        zone_list = compute_client.resource_skus.list()
        for group in list(zone_list):
            if group.resource_type == 'virtualMachines' \
                    and group.name == self.azure_machine_type \
                    and group.locations[0].lower() == self.azure_location.lower():
                for resource_location in group.location_info:
                    for zone_number in resource_location.zones:
                        self.azure_availability_zones.append(zone_number)
                self.azure_availability_zones = sorted(self.azure_availability_zones)
                for zone_number in self.azure_availability_zones:
                    self.logger.info("Added Azure availability zone %s" % zone_number)

    def azure_get_resource_group(self):
        inquire = ask()
        group_list = []
        if not self.azure_subscription_id:
            self.azure_get_subscription_id()
        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, self.azure_subscription_id)
        groups = resource_client.resource_groups.list()
        for group in list(groups):
            group_list.append(group.name)
        selection = inquire.ask_list('Azure Resource Group', group_list)
        self.azure_resource_group = group_list[selection]

    def azure_get_subscription_id(self):
        inquire = ask()
        subscription_list = []
        subscription_name = []
        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        subscriptions = subscription_client.subscriptions.list()
        for group in list(subscriptions):
            subscription_list.append(group.subscription_id)
            subscription_name.append(group.display_name)
        selection = inquire.ask_list('Azure Subscription ID', subscription_list, subscription_name)
        self.azure_subscription_id = subscription_list[selection]
        self.logger.info("Azure Subscription ID = %s" % self.azure_subscription_id)

    def generate_public_key_file(self, public_file):
        self.get_public_key()
        try:
            file_handle = open(public_file, 'w')
            file_handle.write(self.ssh_public_key)
            file_handle.write("\n")
            file_handle.close()
            return True
        except OSError as e:
            print("generate_public_key_file: can not write public key file.")
            return False

    def get_ssh_public_key_file(self):
        inquire = ask()
        dir_list = []
        key_file_list = []
        key_directory = os.environ['HOME'] + '/.ssh'

        if self.ssh_private_key:
            private_key_dir = os.path.dirname(self.ssh_private_key)
            private_key_file = os.path.basename(self.ssh_private_key)
            private_key_name = os.path.splitext(private_key_file)[0]
            check_file_name = private_key_dir + '/' + private_key_name + '.pub'
            if os.path.exists(check_file_name):
                print("Auto selecting public key file %s" % check_file_name)
                self.ssh_public_key_file = check_file_name
                return True
            else:
                if inquire.ask_yn("Generate public key from private key %s" % self.ssh_private_key):
                    if self.generate_public_key_file(check_file_name):
                        self.ssh_public_key_file = check_file_name
                        return True

        for file_name in os.listdir(key_directory):
            full_path = key_directory + '/' + file_name
            dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')
            public_key = file_handle.readline()
            file_size = os.fstat(file_handle.fileno()).st_size
            read_size = len(public_key)
            if file_size != read_size:
                continue
            public_key = public_key.rstrip()
            key_parts = public_key.split(' ')
            pub_key_part = ' '.join(key_parts[0:2])
            pub_key_bytes = str.encode(pub_key_part)
            try:
                key = serialization.load_ssh_public_key(pub_key_bytes)
            except Exception:
                continue
            self.logger.info("Found public key %s" % dir_list[i])
            key_file_list.append(dir_list[i])

        selection = self.ask('Select SSH public key', key_file_list)
        self.ssh_public_key_file = key_file_list[selection]

    def gcp_get_machine_type(self):
        inquire = ask()
        machine_type_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_zone:
            self.get_gcp_zones()
        if not self.gcp_project:
            self.get_gcp_project()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.machineTypes().list(project=self.gcp_project, zone=self.gcp_zone)
        while request is not None:
            response = request.execute()
            for machine_type in response['items']:
                config_block = {}
                config_block['name'] = machine_type['name']
                config_block['cpu'] = machine_type['guestCpus']
                config_block['mem'] = int(machine_type['memoryMb']/1024)
                config_block['description'] = machine_type['description']
                machine_type_list.append(config_block)
            request = gcp_client.machineTypes().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_machine_type('GCP Machine Type', machine_type_list)
        self.gcp_machine_type = machine_type_list[selection]['name']

    def gcp_get_cb_image_name(self):
        inquire = ask()
        image_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_project:
            self.get_gcp_project()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.images().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            if "items" in response:
                for image in response['items']:
                    image_block = {}
                    image_block['name'] = image['name']
                    if 'labels' in image:
                        if 'type' in image['labels']:
                            image_block['type'] = image['labels']['type']
                        if 'release' in image['labels']:
                            image_block['release'] = image['labels']['release']
                        if 'version' in image['labels']:
                            image_block['version'] = image_block['description'] = image['labels']['version'].replace("_", ".")
                    image_list.append(image_block)
                request = gcp_client.images().list_next(previous_request=request, previous_response=response)
            else:
                raise Exception("No images exist in this project")
        selection = inquire.ask_list('GCP Couchbase Image', image_list)
        self.gcp_cb_image = image_list[selection]['name']
        if 'type' in image_list[selection]:
            self.linux_type = image_list[selection]['type']
            self.logger.info("Selecting linux type %s from image metadata" % self.linux_type)
        if 'release' in image_list[selection]:
            self.linux_release = image_list[selection]['release']
            self.logger.info("Selecting linux release %s from image metadata" % self.linux_release)
        if 'version' in image_list[selection]:
            self.cb_version = image_list[selection]['version']
            self.logger.info("Selecting couchbase version %s from image metadata" % self.cb_version)

    def gcp_get_subnet(self):
        inquire = ask()
        subnet_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_region:
            self.get_gcp_region()
        if not self.gcp_project:
            self.get_gcp_project()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.subnetworks().list(project=self.gcp_project, region=self.gcp_region)
        while request is not None:
            response = request.execute()
            for subnet in response['items']:
                subnet_list.append(subnet['name'])
            request = gcp_client.subnetworks().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_list('GCP Subnet', subnet_list)
        self.gcp_subnet = subnet_list[selection]

    def gcp_get_root_type(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_type' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_type']
        self.logger.info("Default root type is %s" % default_selection)
        selection = self.ask_text('Root volume type', default_selection)
        self.gcp_root_type = selection

    def gcp_get_root_size(self):
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_size']
        self.logger.info("Default root size is %s" % default_selection)
        selection = self.ask_text('Root volume size', default_selection)
        self.gcp_root_size = selection

    def get_gcp_region(self):
        inquire = ask()
        region_list = []
        current_location = self.get_country()
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_project:
            self.get_gcp_project()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.regions().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            for region in response['items']:
                if current_location:
                    if current_location.lower() == 'us':
                        if not region['name'].startswith('us'):
                            continue
                    else:
                        if region['name'].startswith('us'):
                            continue
                region_list.append(region['name'])
            request = gcp_client.regions().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_list('GCP Region', region_list)
        self.gcp_region = region_list[selection]
        self.get_gcp_zones()

    def get_country(self):
        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        response = requests.get('http://icanhazip.com', verify=False, timeout=15)
        if response.status_code == 200:
            public_ip = response.text.rstrip()
        else:
            return None
        response = requests.get('http://api.hostip.info/country.php?ip=' + public_ip, verify=False, timeout=15)
        if response.status_code == 200:
            ip_location = response.text.rstrip()
        else:
            return None
        return ip_location

    def get_gcp_zones(self):
        if not self.gcp_region:
            self.get_gcp_region()
        if len(self.gcp_zone_list) > 0:
            return
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.zones().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            for zone in response['items']:
                if not zone['name'].startswith(self.gcp_region):
                    continue
                self.gcp_zone_list.append(zone['name'])
            request = gcp_client.zones().list_next(previous_request=request, previous_response=response)
        self.gcp_zone_list = sorted(self.gcp_zone_list)
        self.gcp_zone = self.gcp_zone_list[0]
        for gcp_zone_name in self.gcp_zone_list:
            self.logger.info("Added GCP zone %s" % gcp_zone_name)

    def get_gcp_project(self):
        inquire = ask()
        project_ids = []
        project_names = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
        request = gcp_client.projects().list()
        while request is not None:
            response = request.execute()
            for project in response.get('projects', []):
                project_ids.append(project['projectId'])
                project_names.append(project['name'])
            request = gcp_client.projects().list_next(previous_request=request, previous_response=response)
        if len(project_ids) == 0:
            self.logger.info("Insufficient permissions to list projects, attempting to get project ID from auth JSON")
            if self.gcp_auth_json_project_id:
                self.logger.info("Setting project ID to %s" % self.gcp_auth_json_project_id)
                self.gcp_project = self.gcp_auth_json_project_id
                return True
            else:
                self.logger.info("Can not get project ID from auth JSON")
                self.gcp_project = inquire.ask_text('GCP Project ID')
                return True
        selection = inquire.ask_list('GCP Project', project_ids, project_names)
        self.gcp_project = project_ids[selection]

    def get_gcp_image_user(self):
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
                self.gcp_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable user for %s %s linux." % (self.linux_type, self.linux_release))

    def get_gcp_image_family(self):
        if not self.gcp_image_family:
            try:
                self.get_gcp_image_name()
            except Exception:
                raise

    def get_gcp_image_name(self):
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
                self.gcp_image_name = self.local_var_json['linux'][self.linux_type][i]['image']
                self.gcp_image_family = self.local_var_json['linux'][self.linux_type][i]['family']
                self.gcp_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable image for %s %s linux." % (self.linux_type, self.linux_release))

    def gcp_get_account_file(self):
        dir_list = []
        auth_file_list = []
        auth_directory = os.environ['HOME'] + '/.config/gcloud'

        for file_name in os.listdir(auth_directory):
            if file_name.lower().endswith('.json'):
                full_path = auth_directory + '/' + file_name
                dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')

            try:
                json_data = json.load(file_handle)
                file_type = json_data['type']
                file_handle.close()
            except (ValueError, KeyError):
                continue
            except OSError:
                print("Can not access GCP config file %s" % dir_list[i])
                raise

            if file_type == 'service_account':
                auth_file_list.append(dir_list[i])

        selection = self.ask('Select GCP auth JSON', auth_file_list)
        self.gcp_account_file = auth_file_list[selection]

        file_handle = open(self.gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'project_id' in auth_data:
            self.gcp_auth_json_project_id = auth_data['project_id']
        if 'client_email' in auth_data:
            self.gcp_service_account_email = auth_data['client_email']

    def get_domain_name(self):
        resolver = dns.resolver.Resolver()
        hostname = socket.gethostname()
        default_selection = ''
        try:
            ip_result = resolver.resolve(hostname, 'A')
            arpa_result = dns.reversename.from_address(ip_result[0].to_text())
            fqdn_result = resolver.resolve(arpa_result, 'PTR')
            host_fqdn = fqdn_result[0].to_text()
            domain_name = host_fqdn.split('.', 1)[1].rstrip('.')
            self.logger.info("Host domain is %s" % domain_name)
            default_selection = domain_name
        except dns.resolver.NXDOMAIN:
            pass
        selection = self.ask_text('DNS Domain Name', default_selection)
        self.domain_name = selection

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

    def vmware_get_template(self):
        if not self.vmware_hostname:
            self.vmware_get_hostname()
        templates = []
        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            for managed_object_ref in container.view:
                if managed_object_ref.config.template:
                    templates.append(managed_object_ref.name)
            container.Destroy()
            selection = self.ask('Select template', templates)
            self.vmware_template = templates[selection]
        except Exception:
            raise

    def vmware_get_sw_url(self):
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
                self.vmware_sw_url = self.local_var_json['linux'][self.linux_type][i]['sw_url']
                return True
        raise Exception("Can not locate software URL for %s %s linux." % (self.linux_type, self.linux_release))

    def vmware_get_iso_checksum(self):
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
                self.vmware_iso_checksum = self.local_var_json['linux'][self.linux_type][i]['checksum']
                return True
        raise Exception("Can not locate ISO checksum for %s %s linux." % (self.linux_type, self.linux_release))

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
        self.vmware_build_pwd_encrypted = sha512_crypt.using(salt=''.join([random.choice(string.ascii_letters + string.digits) for _ in range(16)]), rounds=5000).hash(self.vmware_build_password)

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

    def vmware_get_dvs_network(self):
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
            selection = self.ask('Distributed switch', dvsList)
            self.vmware_dvs = dvsList[selection]
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
        if self.packer_mode:
            if 'defaults' in self.local_var_json:
                if 'folder' in self.local_var_json['defaults']:
                    default_selection = self.local_var_json['defaults']['folder']
        else:
            if self.dev_num:
                default_selection = "couchbase-dev{:02d}".format(self.dev_num)
            elif self.test_num:
                default_selection = "couchbase-tst{:02d}".format(self.test_num)
            elif self.prod_num:
                default_selection = "couchbase-prd{:02d}".format(self.prod_num)
            else:
                default_selection = 'couchbase-database'
        self.logger.info("Default folder is %s" % default_selection)
        selection = self.ask_text('Folder', default_selection)
        self.vmware_folder = selection
        if self.packer_mode:
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
            item_name = ''
            if 'Tags' in vpcs['Vpcs'][i]:
                item_tag = self.aws_get_tag('Name', vpcs['Vpcs'][i]['Tags'])
                if item_tag:
                    item_name = item_tag
            vpc_name_list.append(item_name)

        selection = self.ask('Select VPC', vpc_list, vpc_name_list)
        self.aws_vpc_id = vpcs['Vpcs'][selection]['VpcId']

    def aws_get_availability_zone_list(self):
        availability_zone_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        for zone in self.aws_availability_zones:
            config_block = {}
            config_block['name'] = zone
            self.aws_get_subnet_id(zone)
            config_block['subnet'] = self.aws_subnet_id
            availability_zone_list.append(config_block)
        return availability_zone_list

    def aws_get_subnet_id(self, availability_zone=None):
        inquire = ask()
        if not self.aws_vpc_id:
            try:
                self.aws_get_vpc_id()
            except Exception:
                raise
        subnet_list = []
        subnet_name_list = []
        filter_list = []
        question = "AWS Select Subnet"
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                self.aws_vpc_id,
            ]
        }
        filter_list.append(vpc_filter)
        if availability_zone:
            question = question + " for zone {}".format(availability_zone)
            zone_filter = {
                'Name': 'availability-zone',
                'Values': [
                    availability_zone,
                ]
            }
            filter_list.append(zone_filter)
        subnets = ec2_client.describe_subnets(Filters=filter_list)
        for i in range(len(subnets['Subnets'])):
            subnet_list.append(subnets['Subnets'][i]['SubnetId'])
            item_name = ''
            if 'Tags' in subnets['Subnets'][i]:
                item_tag = self.aws_get_tag('Name', subnets['Subnets'][i]['Tags'])
                if item_tag:
                    item_name = item_tag
            subnet_name_list.append(item_name)

        selection = inquire.ask_list(question, subnet_list, subnet_name_list)
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
        inquire = ask()
        size_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        describe_args = {}
        while True:
            instance_types = ec2_client.describe_instance_types(**describe_args)
            for machine_type in instance_types['InstanceTypes']:
                config_block = {}
                config_block['name'] = machine_type['InstanceType']
                config_block['cpu'] = machine_type['VCpuInfo']['DefaultVCpus']
                config_block['mem'] = int(machine_type['MemoryInfo']['SizeInMiB'] / 1024)
                config_block['description'] = ",".join(machine_type['ProcessorInfo']['SupportedArchitectures']) \
                                              + ' ' + str(machine_type['ProcessorInfo']['SustainedClockSpeedInGhz']) + 'GHz' \
                                              + ', Network: ' + machine_type['NetworkInfo']['NetworkPerformance'] \
                                              + ', Hypervisor: ' + machine_type['Hypervisor'] if 'Hypervisor' in machine_type else 'NA'
                size_list.append(config_block)
            if 'NextToken' not in instance_types:
                break
            describe_args['NextToken'] = instance_types['NextToken']
        selection = inquire.ask_machine_type('AWS Instance Type', size_list)
        self.aws_instance_type = size_list[selection]['name']

    def aws_get_ami_id(self):
        inquire = ask()
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
            image_block = {}
            image_block['name'] = images['Images'][i]['ImageId']
            image_block['description'] = images['Images'][i]['Name']
            if 'Tags' in images['Images'][i]:
                item_release_tag = self.aws_get_tag('Release', images['Images'][i]['Tags'])
                item_type_tag = self.aws_get_tag('Type', images['Images'][i]['Tags'])
                item_version_tag = self.aws_get_tag('Version', images['Images'][i]['Tags'])
                if item_type_tag:
                    image_block['type'] = item_type_tag
                if item_release_tag:
                    image_block['release'] = item_release_tag
                if item_version_tag:
                    image_block['version'] = item_version_tag
                    image_block['description'] = image_block['description'] + ' => Version: ' + item_version_tag
            image_list.append(image_block)
        selection = inquire.ask_list('Select AMI', image_list)
        self.aws_ami_id = image_list[selection]['name']
        if 'type' in image_list[selection]:
            self.linux_type = image_list[selection]['type']
            self.logger.info("Selecting linux type %s from image metadata" % self.linux_type)
        if 'release' in image_list[selection]:
            self.linux_release = image_list[selection]['release']
            self.logger.info("Selecting linux release %s from image metadata" % self.linux_release)
        if 'version' in image_list[selection]:
            self.cb_version = image_list[selection]['version']
            self.logger.info("Selecting couchbase version %s from image metadata" % self.cb_version)

    def aws_get_region(self):
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

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        zone_list = ec2_client.describe_availability_zones()
        for availability_zone in zone_list['AvailabilityZones']:
            self.logger.info("Added availability zone %s" % availability_zone['ZoneName'])
            self.aws_availability_zones.append(availability_zone['ZoneName'])

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
        inquire = ask()
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
            release_list = sorted(versions_list, reverse=True)
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

    def aws_tag_exists(self, key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return True
        return False

    def aws_get_tag(self, key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return tags[i]['Value']
        return None

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

    def ask_yn(self, question, default=False):
        if default:
            default_answer = 'y'
        else:
            default_answer = 'n'
        while True:
            prompt = "{} (y/n) [{}]? ".format(question, default_answer)
            answer = input(prompt)
            answer = answer.rstrip("\n")
            if len(answer) == 0:
                answer = default_answer
            if answer == 'Y' or answer == 'y' or answer == 'yes':
                return True
            elif answer == 'N' or answer == 'n' or answer == 'no':
                return False
            else:
                print(" [!] Unrecognized answer, please try again...")

    def get_subnet_cidr(self):
        inquire = ask()
        selection = inquire.ask_net('Subnet CIDR')
        self.subnet_cidr = selection

    def get_subnet_mask(self):
        if not self.subnet_cidr:
            self.get_subnet_cidr()
        self.subnet_netmask = ipaddress.ip_network(self.subnet_cidr).prefixlen

    def get_subnet_gateway(self):
        inquire = ask()
        selection = inquire.ask_ip('Default Gateway')
        self.default_gateway = selection

    def get_omit_range(self):
        inquire = ask()
        selection = inquire.ask_net_range('Omit Network Range')
        self.omit_range = selection

    def set_availability_zone_cycle(self):
        inquire = ask()
        if self.location == 'aws':
            availability_zone_list = self.aws_get_availability_zone_list()
        elif self.location == 'gcp':
            if len(self.gcp_zone_list) == 0:
                self.get_gcp_region()
            availability_zone_list = self.gcp_zone_list
        elif self.location == 'azure':
            if len(self.azure_availability_zones) == 0:
                self.azure_get_location()
            availability_zone_list = self.azure_availability_zones
        else:
            self.availability_zone_cycle = None
            return
        if self.use_single_zone:
            selection = inquire.ask_list('Select availability zone', availability_zone_list)
            self.availability_zone_cycle = cycle([availability_zone_list[selection]])
        else:
            self.availability_zone_cycle = cycle(availability_zone_list)

    @property
    def get_next_availability_zone(self):
        return next(self.availability_zone_cycle)

    def create_cluster_config(self):
        inquire = ask()
        resolver = dns.resolver.Resolver()
        config_segments = []
        config_segments.append(CB_CFG_HEAD)
        node = 1
        services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing', ]
        self.set_availability_zone_cycle()

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
            node_ip_address = None
            node_netmask = None
            node_gateway = None
            node_name = "cb-{}-n{:02d}".format(env_text, node)
            if self.availability_zone_cycle:
                zone_data = self.get_next_availability_zone
                availability_zone = zone_data['name']
                node_subnet = zone_data['subnet']
            else:
                availability_zone = None
                node_subnet = None
            if node == 1:
                install_mode = 'init'
            else:
                install_mode = 'add'
            print("Configuring node %d" % node)
            if self.static_ip:
                if not self.domain_name:
                    self.get_domain_name()
                if not self.subnet_cidr:
                    self.get_subnet_cidr()
                if not self.subnet_netmask:
                    self.get_subnet_mask()
                if not self.default_gateway:
                    self.get_subnet_gateway()
                node_netmask = self.subnet_netmask
                node_gateway = self.default_gateway
                node_fqdn = "{}.{}".format(node_name, self.domain_name)
                try:
                    answer = resolver.resolve(node_fqdn, 'A')
                    node_ip_address = answer[0]
                except dns.resolver.NXDOMAIN:
                    print("[i] Warning Can not resolve node host name %s" % node_fqdn)
                if self.update_dns:
                    if not node_ip_address:
                        print("Node IP not assigned, attempting DNS update...")
                        if not self.omit_range:
                            self.get_omit_range()
                        dnsupd = dynamicDNS(self.domain_name)
                        if dnsupd.dns_prep():
                            dnsupd.dns_get_range(self.subnet_cidr, self.omit_range)
                            if dnsupd.free_list_size > 0:
                                node_ip_address = dnsupd.get_free_ip
                                print("[i] Auto assigned IP %s to %s" % (node_ip_address, node_name))
                            else:
                                node_ip_address = inquire.ask_text('Node IP Address')
                            if dnsupd.dns_update(node_name, self.domain_name, node_ip_address, self.subnet_netmask):
                                print("Added address record for %s" % node_fqdn)
                            else:
                                print("Can not add DNS record, aborting.")
                                sys.exit(1)
                        else:
                            print("Can not setup dynamic update, aborting.")
                            sys.exit(1)
                else:
                    if not node_ip_address:
                        node_ip_address = inquire.ask_text('Node IP Address')
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
                NODE_NAME=node_name,
                NODE_NUMBER=node,
                NODE_SERVICES=','.join(selected_services),
                NODE_INSTALL_MODE=install_mode,
                NODE_ZONE=availability_zone,
                NODE_SUBNET=node_subnet,
                NODE_IP_ADDRESS=node_ip_address,
                NODE_NETMASK=node_netmask,
                NODE_GATEWAY=node_gateway,
            )
            config_segments.append(format_template)
            if node >= 3:
                print("")
                if not inquire.ask_yn('  ==> Add another node'):
                    break
                print("")
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
