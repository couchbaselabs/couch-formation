##
##

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
import logging
import dns.resolver
import datetime
import socket
import pytz
from lib.dns import dynamicDNS
from lib.ask import ask
from lib.exceptions import *


class toolbox(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_country(self):
        """Attempt to identify the location of the user"""
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
            if ip_location.lower() == "xx":
                response = requests.get('http://ipwhois.app/json/' + public_ip, verify=False, timeout=15)
                if response.status_code == 200:
                    try:
                        response_json = json.loads(response.text)
                        ip_location = response_json['country_code']
                    except Exception:
                        return None
                else:
                    return None
        else:
            return None
        self.logger.info("Determined current location to be %s" % ip_location)
        return ip_location

    def get_domain_name(self, default=None):
        inquire = ask()
        resolver = dns.resolver.Resolver()
        hostname = socket.gethostname()
        default_selection = ''
        try:
            ip_result = resolver.resolve(hostname, 'A')
            arpa_result = dns.reversename.from_address(ip_result[0].to_text())
            fqdn_result = resolver.resolve(arpa_result.to_text(), 'PTR')
            host_fqdn = fqdn_result[0].to_text()
            domain_name = host_fqdn.split('.', 1)[1].rstrip('.')
            self.logger.info("Host domain is %s" % domain_name)
            default_selection = domain_name
        except dns.resolver.NXDOMAIN:
            pass
        selection = inquire.ask_text('DNS Domain Name', recommendation=default_selection, default=default)
        return selection

    def get_timezone(self, default=None):
        inquire = ask()
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
                    return link_path
                except pytz.UnknownTimeZoneError:
                    pass
                start = link_path.find("/") + 1

        for name in pytz.all_timezones:
            tzone = pytz.timezone(name)
            code = datetime.datetime.now(tzone).tzname()
            if code == local_code:
                tzlist.append(tzone)
        selection = inquire.ask_list('Select timezone', tzlist, default=default)
        return tzlist[selection]

    def get_linux_release_from_image_name(self, name):
        try:
            linux_release = name.split('-')[1]
            return linux_release
        except IndexError:
            raise ImageNameFormatError(f"can not get release from image {name}")

    def get_linux_type_from_image_name(self, name):
        try:
            linux_type = name.split('-')[0]
            return linux_type
        except IndexError:
            raise ImageNameFormatError(f"can not get os name from image {name}")

    def get_cb_cluster_name(self, dev_num=None, test_num=None, prod_num=None, default=None):
        """Get the Couchbase Cluster Name"""
        inquire = ask()
        if dev_num:
            cluster_name = "dev{:02d}db".format(dev_num)
        elif test_num:
            cluster_name = "test{:02d}db".format(test_num)
        elif prod_num:
            cluster_name = "prod{:02d}db".format(prod_num)
        else:
            cluster_name = 'cbdb'
        selection = inquire.ask_text('Couchbase Cluster Name', cluster_name, default=default)
        return selection

    def ask_to_use_public_ip(self, default=None):
        """Ask if the public IP should be assigned and used for SSH"""
        inquire = ask()
        selection = inquire.ask_bool('Use Public IP', recommendation='false', default=default)
        return selection

    def get_dns_servers(self, domain_name: str):
        """Get list of DNS servers"""
        server_list = []
        dns_lookup = dynamicDNS(domain_name)
        server_list = dns_lookup.dns_get_servers()
        dns_server_list = ','.join(f'"{s}"' for s in server_list)
        return dns_server_list
