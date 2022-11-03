##
##

import logging
import jinja2
import dns.resolver
import ipaddress
from itertools import cycle
from lib.exceptions import *
from lib.ask import ask
from lib.dns import dynamicDNS
from lib.constants import CB_CFG_HEAD, CB_CFG_NODE, CB_CFG_TAIL, APP_CFG_HEAD, CLUSTER_CONFIG, APP_CONFIG, SGW_CFG_HEAD, SGW_CONFIG, STD_CFG_HEAD, STD_CONFIG
from lib.location import location
from lib.toolbox import toolbox
from lib.util.inquire import Inquire
import lib.config as config


class clustermgr(object):

    def __init__(self, driver, env, nm, parameters):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cloud = parameters.cloud
        self.args = parameters
        self.driver = driver
        self.env = env
        self.subnet_cidr = None
        self.subnet_netmask = None
        self.default_gateway = None
        self.omit_range = None
        self.use_single_zone = self.args.zone
        self.availability_zone_cycle = None
        self.static_ip = self.args.static
        self.update_dns = self.args.dns
        self.subnet_cidr = None
        self.subnet_netmask = None
        self.default_gateway = None
        self.domain_name = None
        self.lc = location()
        self.lc.set_cloud(self.cloud)
        self.tools = toolbox()
        self.nm = nm
        self.cluster_file_name = 'cluster.tf'
        self.app_file_name = 'app.tf'
        self.sgw_file_name = 'sgw.tf'
        self.std_file_name = 'nodes.tf'

    def set_availability_zone_cycle(self):
        inquire = ask()
        if self.cloud == 'aws':
            availability_zone_list = self.driver.aws_get_availability_zone_list()
        elif self.cloud == 'gcp':
            availability_zone_list = self.driver.gcp_get_availability_zone_list()
        elif self.cloud == 'azure':
            availability_zone_list = self.driver.azure_get_availability_zone_list()
        else:
            self.availability_zone_cycle = None
            return
        if self.use_single_zone:
            selection = inquire.ask_list('Select availability zone', availability_zone_list)
            self.logger.info("AWS AZ: %s" % availability_zone_list[selection]['subnet'])
            self.availability_zone_cycle = cycle([availability_zone_list[selection]])
        else:
            self.logger.info("AWS AZ List: %s" % ",".join([e['subnet'] for e in availability_zone_list]))
            self.availability_zone_cycle = cycle(availability_zone_list)

    @property
    def get_next_availability_zone(self):
        return next(self.availability_zone_cycle)

    def check_node_ip_address(self, node_ip):
        if ipaddress.ip_address(node_ip) in ipaddress.ip_network(self.subnet_cidr):
            return True
        else:
            return False

    def get_static_ip(self, node_name):
        inquire = ask()
        resolver = dns.resolver.Resolver()
        change_node_ip_address = False
        old_ip_address = None
        node_ip_address = None

        if not self.domain_name:
            self.domain_name = self.nm.get_domain_name()
        if not self.subnet_cidr:
            self.subnet_cidr = self.nm.get_network_cidr()
        if not self.subnet_netmask:
            self.subnet_netmask = self.nm.get_network_mask()
        if not self.default_gateway:
            self.default_gateway = self.nm.get_network_gateway()
        if not self.omit_range:
            self.omit_range = self.nm.get_network_omit()
        node_netmask = self.subnet_netmask
        node_gateway = self.default_gateway
        node_fqdn = "{}.{}".format(node_name, self.domain_name)
        try:
            answer = resolver.resolve(node_fqdn, 'A')
            node_ip_address = answer[0].to_text()
        except dns.resolver.NXDOMAIN:
            print("[i] Warning Can not resolve node host name %s" % node_fqdn)
        if node_ip_address:
            change_node_ip_address = not self.check_node_ip_address(node_ip_address)
            if change_node_ip_address:
                old_ip_address = node_ip_address
                print("Warning: node IP %s not in node subnet %s" % (node_ip_address, self.subnet_cidr))
        if self.update_dns:
            if not node_ip_address or change_node_ip_address:
                print("%s: Attempting to acquire node IP and update DNS" % node_name)
                dnsupd = dynamicDNS(self.domain_name)
                if dnsupd.dns_prep():
                    dnsupd.dns_get_range(self.subnet_cidr, self.omit_range)
                    if dnsupd.free_list_size > 0:
                        node_ip_address = dnsupd.get_free_ip
                        print("[i] Auto assigned IP %s to %s" % (node_ip_address, node_name))
                    else:
                        node_ip_address = inquire.ask_text('Node IP Address')
                    if change_node_ip_address:
                        if dnsupd.dns_delete(node_name, self.domain_name, old_ip_address, self.subnet_netmask):
                            print("Deleted old IP %s for %s" % (old_ip_address, node_name))
                        else:
                            print("Can not delete DNS record. Aborting.")
                            sys.exit(1)
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

        return node_ip_address, node_netmask, node_gateway

    def create_node_config(self, mode, destination, nodes=3):
        inquire = ask()
        config_segments = []
        node = 1
        prefix_text = None
        services = []
        min_nodes = nodes
        output_file = None
        env_text = self.env.get_env
        env_text = env_text.replace(':', '')
        node_env = env_text

        if mode == CLUSTER_CONFIG:
            services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing', ]
            prefix_text = 'cb'
            config_segments.append(CB_CFG_HEAD)
            output_file = self.cluster_file_name
        elif mode == APP_CONFIG:
            min_nodes = 1
            prefix_text = 'app'
            node_env = self.env.get_app_env.replace(':', '-')
            config_segments.append(APP_CFG_HEAD)
            output_file = self.app_file_name
        elif mode == SGW_CONFIG:
            min_nodes = 1
            prefix_text = 'sgw'
            node_env = self.env.get_sgw_env.replace(':', '-')
            config_segments.append(SGW_CFG_HEAD)
            output_file = self.sgw_file_name
        elif mode == STD_CONFIG:
            min_nodes = 1
            prefix_text = 'node'
            config_segments.append(STD_CFG_HEAD)
            output_file = self.std_file_name

        self.set_availability_zone_cycle()

        node_swap = Inquire.ask_bool('Configure swap', recommendation='false')

        print(f"Building {prefix_text} node configuration")
        while True:
            selected_services = []
            node_ip_address = None
            node_netmask = None
            node_gateway = None
            node_ram = 16
            node_name = f"{prefix_text}-{env_text}-n{node:02d}"
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
                node_ip_address, node_netmask, node_gateway = self.get_static_ip(node_name)
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
                NODE_ENV=node_env,
                NODE_ZONE=availability_zone,
                NODE_SUBNET=node_subnet,
                NODE_RAM=node_ram,
                NODE_SWAP=str(node_swap).lower(),
                NODE_IP_ADDRESS=node_ip_address,
                NODE_NETMASK=node_netmask,
                NODE_GATEWAY=node_gateway,
            )
            config_segments.append(format_template)
            if node >= min_nodes:
                print("")
                if not inquire.ask_yn('  ==> Add another node'):
                    break
                print("")
            node += 1

        config_segments.append(CB_CFG_TAIL)
        output_file = destination + '/' + output_file
        try:
            with open(output_file, 'w') as write_file:
                for i in range(len(config_segments)):
                    write_file.write(config_segments[i])
                write_file.write("\n")
                write_file.close()
        except OSError as err:
            raise ClusterMgrError(f"Can not write to new node file: {err}")
