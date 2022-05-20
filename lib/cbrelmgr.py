##
##

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import xml.etree.ElementTree as ET
import gzip
import re
from typing import Type
from lib.ask import ask
from lib.envmgr import envmgr


class cbrelease(object):
    VARIABLES = [
        ('CB_INDEX_MEM_TYPE', 'index_memory', 'get_cb_index_mem_setting', None),
        ('CB_VERSION', 'cb_version', 'get_cb_version', None),
    ]

    def __init__(self, pkgmgr=None, release=None):
        self.pkgmgr_type = pkgmgr
        self.os_release = release
        self.os_name = None
        self.cb_version = None
        self.cb_index_mem_type = None

    def set_os_name(self, name: str):
        self.os_name = name
        if self.os_name == 'centos':
            self.pkgmgr_type = 'yum'
        elif self.os_name == 'ubuntu':
            self.pkgmgr_type = 'apt'

    def set_os_ver(self, release: str):
        self.os_release = release

    def get_cb_index_mem_setting(self, default=None, write=None):
        inquire = ask()

        if write:
            self.cb_index_mem_type = write
            return self.cb_index_mem_type

        if self.cb_index_mem_type:
            return self.cb_index_mem_type

        option_list = [
            {
                'name': 'default',
                'description': 'Standard Index Storage'
            },
            {
                'name': 'memopt',
                'description': 'Memory-optimized'
            },
        ]
        selection = inquire.ask_list('Select index storage option', option_list, default=default)
        self.cb_index_mem_type = option_list[selection]['name']

        return self.cb_index_mem_type

    def get_cb_version(self, default=None, write=None):
        inquire = ask()

        if write:
            self.cb_version = write
            return self.cb_version

        if self.cb_version:
            return self.cb_version

        versions_list = self.get_versions()
        release_list = sorted(versions_list, reverse=True)
        selection = inquire.ask_list('Select Couchbase Version', release_list, page_len=5, default=default)
        self.cb_version = release_list[selection]

        return self.cb_version

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