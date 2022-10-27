##
##

import requests
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import xml.etree.ElementTree as ET
import gzip
import re
import json
from lib.exceptions import CBReleaseManagerError


class CBRelease(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def _get_pkg_mgr(os_name: str):
        if os_name == 'centos' or os_name == 'rhel':
            return 'yum'
        elif os_name == 'ubuntu' or os_name == 'debian':
            return 'apt'

    @staticmethod
    def cb_index_mem_setting():
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

        return option_list

    def get_cb_version(self, os_name: str, os_rel: str):
        pkg_mgr = self._get_pkg_mgr(os_name)
        if pkg_mgr == 'yum':
            versions_list = self.get_rpm(os_rel)
        else:
            versions_list = self.get_apt(os_rel)
        release_list = sorted(versions_list, reverse=True)
        return release_list

    @staticmethod
    def get_rpm(os_rel: str):
        pkg_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/rpm/' + os_rel + '/x86_64/repodata/repomd.xml'
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

        list_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/rpm/' + os_rel + '/x86_64/' + filelist_url

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

    @staticmethod
    def get_apt(os_rel: str):
        pkg_url = 'http://packages.couchbase.com/releases/couchbase-server/enterprise/deb/dists/' + os_rel + '/' + os_rel + '/main/binary-amd64/Packages.gz'
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

    def get_sgw_version(self):
        versions_list = self.get_sgw_versions()
        release_list = sorted(versions_list, reverse=True)
        return release_list

    @staticmethod
    def get_sgw_rpm(version):
        return f"http://packages.couchbase.com/releases/couchbase-sync-gateway/{version}/couchbase-sync-gateway-enterprise_{version}_x86_64.rpm"

    @staticmethod
    def get_sgw_apt(version):
        return f"http://packages.couchbase.com/releases/couchbase-sync-gateway/{version}/couchbase-sync-gateway-enterprise_{version}_x86_64.deb"

    def get_sgw_versions(self):
        sgw_git_release_url = 'https://api.github.com/repos/couchbase/sync_gateway/releases'
        git_release_list = []
        found_release_list = []

        session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.1,
                        status_forcelist=[500, 501, 503])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = requests.get(sgw_git_release_url, verify=False, timeout=15)

        if response.status_code != 200:
            raise Exception("Can not get Sync Gateway release data: error %d" % response.status_code)

        try:
            releases = json.loads(response.content)
            for release in releases:
                git_release_list.append(release['tag_name'])
        except Exception as err:
            raise CBReleaseManagerError(f"can not process Sync Gateway release data: {err}")

        for release in git_release_list:
            check_url = self.get_sgw_rpm(release)
            response = requests.head(check_url, verify=False, timeout=15)

            if response.status_code != 200:
                continue

            check_url = self.get_sgw_apt(release)
            response = requests.head(check_url, verify=False, timeout=15)

            if response.status_code == 200:
                found_release_list.append(release)

        return found_release_list
