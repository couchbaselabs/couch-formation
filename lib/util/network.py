##
##

import logging
import socket
import dns.resolver
import ipaddress
from lib.util.inquire import Inquire


class NetworkUtil(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def get_domain_name():
        resolver = dns.resolver.Resolver()
        hostname = socket.gethostname()
        try:
            ip_result = resolver.resolve(hostname, 'A')
            arpa_result = dns.reversename.from_address(ip_result[0].to_text())
            fqdn_result = resolver.resolve(arpa_result.to_text(), 'PTR')
            host_fqdn = fqdn_result[0].to_text()
            domain_name = host_fqdn.split('.', 1)[1].rstrip('.')
            return domain_name
        except dns.resolver.NXDOMAIN:
            return None

    @staticmethod
    def get_dns_servers(domain_name: str, server: str = None):
        server_list = []
        resolver = dns.resolver.Resolver()
        if server:
            resolver.nameservers = [server]
        try:
            ns_answer = resolver.resolve(domain_name, 'NS')
            for server in ns_answer:
                ip_answer = resolver.resolve(server.target, 'A')
                for ip in ip_answer:
                    server_list.append(ip.address)
            return server_list
        except dns.resolver.NXDOMAIN:
            return None

    @staticmethod
    def get_subnet_cidr():
        selection = Inquire().ask_net('Subnet CIDR')
        return selection

    @staticmethod
    def get_subnet_mask(subnet_cidr: str):
        subnet_netmask = ipaddress.ip_network(subnet_cidr).prefixlen
        return subnet_netmask

    @staticmethod
    def get_subnet_gateway():
        selection = Inquire().ask_ip('Default Gateway')
        return selection
