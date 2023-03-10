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
        self.gateway = None
        self.netmask = None
        self.subnet = None

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

    def get_subnet_cidr(self):
        self.subnet = Inquire().ask_net('Subnet CIDR')
        return self.subnet

    def get_subnet_mask(self):
        self.netmask = ipaddress.ip_network(self.subnet).prefixlen
        return self.netmask

    def get_subnet_gateway(self):
        subnet = ipaddress.ip_network(self.subnet)
        gateway = next(subnet.hosts())
        self.gateway = Inquire().ask_ip('Default Gateway', default=gateway.exploded)
        return self.gateway

    def get_static_ip(self, node_name: str, domain_name: str, dns_servers: list[str]):
        resolver = dns.resolver.Resolver()
        resolver.nameservers = dns_servers

        if not self.subnet:
            self.get_subnet_cidr()
            self.get_subnet_mask()
            self.get_subnet_gateway()

        while True:
            try:
                node_fqdn = f"{node_name}.{domain_name}"
                answer = resolver.resolve(node_fqdn, 'A')
                node_ip_address = answer[0].to_text()
                print(f"Node {node_name} resolved to {node_ip_address}")
            except dns.resolver.NXDOMAIN:
                node_ip_address = Inquire().ask_ip(f"Node {node_name} IP Address")

            if ipaddress.ip_address(node_ip_address) in ipaddress.ip_network(self.subnet):
                return node_ip_address
            else:
                print(f"IP address is not in subnet {self.subnet}")
