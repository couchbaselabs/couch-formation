##
##

import requests
import ipaddress
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
    VARIABLES = [
        ('OS_TIMEZONE', 'os_timezone', 'get_timezone', None),
        ('USE_PUBLIC_IP', 'use_public_ip', 'ask_to_use_public_ip', None),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.os_timezone = None
        self.use_public_ip = None

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

    def get_timezone(self, default=None, write=None):
        inquire = ask()

        if write:
            self.os_timezone = write
            return self.os_timezone

        if self.os_timezone:
            return self.os_timezone

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
        self.os_timezone = tzlist[selection]
        return self.os_timezone

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

    def check_image_name_format(self, name):
        try:
            name_fields = name.split('-')
            if name_fields[2] == 'couchbase' and len(name_fields) == 7:
                return True
        except IndexError:
            pass
        return False

    def ask_to_use_public_ip(self, default=None, write=None):
        """Ask if the public IP should be assigned and used for SSH"""
        inquire = ask()

        if write:
            self.use_public_ip = write
            return self.use_public_ip

        if self.use_public_ip:
            return self.use_public_ip

        selection = inquire.ask_bool('Use Public IP', recommendation='true', default=default)
        self.use_public_ip = selection
        return self.use_public_ip

    def get_dns_servers(self, domain_name: str):
        """Get list of DNS servers"""
        dns_lookup = dynamicDNS(domain_name)
        server_list = dns_lookup.dns_get_servers()
        return server_list

    def get_subnet_cidr(self):
        inquire = ask()
        selection = inquire.ask_net('Subnet CIDR')
        return selection

    def get_subnet_mask(self, subnet_cidr: str):
        subnet_netmask = ipaddress.ip_network(subnet_cidr).prefixlen
        return subnet_netmask

    def get_subnet_gateway(self):
        inquire = ask()
        selection = inquire.ask_ip('Default Gateway')
        return selection

    def get_omit_range(self):
        inquire = ask()
        selection = inquire.ask_net_range('Omit Network Range')
        return selection

    def get_first_ip(self, subnet_cidr: str):
        return str(ipaddress.ip_network(subnet_cidr)[0])

    def create_dir(self, name) -> None:
        if not os.path.exists(name):
            path_dir = os.path.dirname(name)
            if not os.path.exists(path_dir):
                self.create_dir(path_dir)
            try:
                os.mkdir(name)
            except OSError as err:
                raise ToolboxError(f"Could not create directory {name}: {err}")
