#!/usr/bin/env python3

'''
Read OpenShift Install Config and Build Terraform Files
'''

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
import base64

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
        self.parser = parser

class processTemplate(object):

    def __init__(self, pargs):
        self.template_file = pargs.template
        template_dir = os.path.dirname(self.template_file)
        self.linux_type = None
        self.linux_release = None
        self.cb_version = None

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

        try:
            with open(self.globals_file, 'r') as inputFile:
                global_var_text = inputFile.read()
                global_var_json = json.loads(global_var_text)
            inputFile.close()
        except OSError as e:
            print("Can not read global variable file: %s" % str(e))
            sys.exit(1)

        try:
            with open(self.locals_file, 'r') as inputFile:
                local_var_text = inputFile.read()
                local_var_json = json.loads(global_var_text)
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

        for item in requested_vars:
            if item == 'CB_VERSION':
                if 'linux' not in global_var_json:
                    print("Linux distribution global configuration required.")
                    sys.exit(1)

                distro_list = []
                for key in global_var_json['linux']:
                    distro_list.append(key)

                selection = self.ask('Select Linux Distribution', distro_list)
                self.linux_type = distro_list[selection]

                version_list = []
                version_desc = []
                for i in range(len(global_var_json['linux'][self.linux_type])):
                    version_list.append(global_var_json['linux'][self.linux_type][i]['version'])
                    version_desc.append(global_var_json['linux'][self.linux_type][i]['name'])

                selection = self.ask('Select Version', version_list, version_desc)
                self.linux_release = global_var_json['linux'][self.linux_type][selection]['version']
                linux_pkgmgr = global_var_json['linux'][self.linux_type][selection]['type']

                release_list = []
                try:
                    cbr = cbrelease(linux_pkgmgr, self.linux_release)
                    versions_list = cbr.get_versions()
                    release_list = self.reverse_list(versions_list)
                except Exception as e:
                    print("Can not get available releases: %s" % str(e))
                    sys.exit(1)

                selection = self.ask('Select Couchbase Version', release_list)
                self.cb_version = release_list[selection]

    def reverse_list(self, list):
        return [item for item in reversed(list)]

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
