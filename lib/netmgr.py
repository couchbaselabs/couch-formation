##
##

import os
import logging
import json
from lib.exceptions import NetworkMgrError
from lib.ask import ask
from lib.location import location
from lib.toolbox import toolbox
from lib.prereq import prereq


class network_manager(object):
    VARIABLES = [
        ('DOMAIN_NAME', 'domain_name', 'get_domain_name', None),
        ('DNS_SERVER_LIST', 'dns_server_list', 'get_dns_server_list', None),
    ]

    def __init__(self, parameters):
        self.cloud = parameters.cloud
        self.args = parameters
        self.logger = logging.getLogger(self.__class__.__name__)
        self.lc = location()
        self.tools = toolbox()
        self.domain_name = None
        self.dns_server_list = []
        self.subnet_cidr = None
        self.subnet_netmask = None
        self.default_gateway = None
        self.omit_range = None
        self.db_directory = self.lc.package_dir + '/db'

    def add_domain(self):
        self.domain_name = self.tools.get_domain_name()
        self.dns_server_list = self.tools.get_dns_servers(self.domain_name)

        out_file_name = self.db_directory + '/' + self.domain_name + '.json'

        file_entry = {
            'domain': self.domain_name,
            'servers': self.dns_server_list,
        }

        try:
            with open(out_file_name, 'w') as dat_file:
                json.dump(file_entry, dat_file, indent=2)
                dat_file.write("\n")
                dat_file.close()
        except OSError as err:
            raise NetworkMgrError(f"can not write domain data file: {err}")

    def add_network(self):
        self.subnet_cidr = self.tools.get_subnet_cidr()
        self.subnet_netmask = self.tools.get_subnet_mask(self.subnet_cidr)
        self.default_gateway = self.tools.get_subnet_gateway()
        self.omit_range = self.tools.get_omit_range()

        first_ip = self.tools.get_first_ip(self.subnet_cidr)

        out_file_name = self.db_directory + '/' + first_ip + '.json'

        file_entry = {
            'cidr': self.subnet_cidr,
            'netmask': self.subnet_netmask,
            'gateway': self.default_gateway,
            'omit_range': self.omit_range,
        }

        try:
            with open(out_file_name, 'w') as dat_file:
                json.dump(file_entry, dat_file, indent=2)
                dat_file.write("\n")
                dat_file.close()
        except OSError as err:
            raise NetworkMgrError(f"can not write domain data file: {err}")

    def list_data(self):
        self.load_domain(select=False)
        self.load_network(select=False)

    def load_domain(self, select=True):
        inquire = ask()
        entry_list = []

        if self.domain_name and select:
            return True

        for file_name in os.listdir(self.db_directory):
            full_path = self.db_directory + '/' + file_name

            file_handle = open(full_path, 'r')
            data = file_handle.read()
            file_handle.close()

            try:
                file_data = json.loads(data)
                if 'domain' in file_data:
                    file_data['name'] = file_data['domain']
                    entry_list.append(file_data)
            except Exception:
                continue

        if len(entry_list) > 0:
            if select:
                selection = inquire.ask_list('Select Domain', entry_list)
                self.domain_name = entry_list[selection]['domain']
                self.dns_server_list = entry_list[selection]['servers']
            else:
                for n, item in enumerate(entry_list):
                    print(f"{n+1:d}) Domain: {item['domain']}, Servers: {','.join(item['servers'])}")
            return True
        else:
            raise NetworkMgrError("no domains configured")

    def load_network(self, select=True):
        inquire = ask()
        entry_list = []

        if self.subnet_cidr and select:
            return True

        for file_name in os.listdir(self.db_directory):
            full_path = self.db_directory + '/' + file_name

            file_handle = open(full_path, 'r')
            data = file_handle.read()
            file_handle.close()

            try:
                file_data = json.loads(data)
                if 'cidr' in file_data:
                    file_data['name'] = file_data['cidr']
                    entry_list.append(file_data)
            except Exception:
                continue

        if len(entry_list) > 0:
            if select:
                selection = inquire.ask_list('Select Network', entry_list)
                self.subnet_cidr = entry_list[selection]['cidr']
                self.subnet_netmask = entry_list[selection]['netmask']
                self.default_gateway = entry_list[selection]['gateway']
                self.omit_range = entry_list[selection]['omit_range']
            else:
                for n, item in enumerate(entry_list):
                    print(f"{n+1:d}) Subnet: {item['cidr']}, Mask: {item['netmask']}, Gateway: {item['gateway']}, Omit: {item['omit_range']}")
            return True
        else:
            raise NetworkMgrError("no networks defined")

    @prereq(requirements=('load_domain',))
    def get_domain_name(self, write=None):
        if write:
            self.domain_name = write

        return self.domain_name

    @prereq(requirements=('load_domain',))
    def get_dns_server_list(self, write=None):
        if write:
            self.dns_server_list = write.replace('"', '').split(",")

        dns_server_list = ','.join(f'"{s}"' for s in self.dns_server_list)
        return dns_server_list

    @prereq(requirements=('load_network',))
    def get_network_cidr(self, write=None):
        if write:
            self.subnet_cidr = write

        return self.subnet_cidr

    @prereq(requirements=('load_network',))
    def get_network_mask(self, write=None):
        if write:
            self.subnet_netmask = write

        return self.subnet_netmask

    @prereq(requirements=('load_network',))
    def get_network_gateway(self, write=None):
        if write:
            self.default_gateway = write

        return self.default_gateway

    @prereq(requirements=('load_network',))
    def get_network_omit(self, write=None):
        if write:
            self.omit_range = write

        return self.omit_range
