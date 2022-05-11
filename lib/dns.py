##
##

import dns.resolver
import dns.reversename
import dns.tsigkeyring
import dns.update
import os
import ipaddress
import json
import sys
import math
from lib.ask import ask

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

    def dns_delete(self, hostname, domain, address, prefix):
        if self.type == 'tsig':
            return self.tsig_delete(hostname, domain, address, prefix)
        else:
            print("dns_delete: Unsupported type %s" % type)
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
                    if not any(str(all_ip) == address for address in subnet_list):
                        if int(str(all_ip).split('.')[3]) >= 10:
                            free_list.append(str(all_ip))
                if omit:
                    try:
                        (first, last) = omit.split('-')
                        for ipaddr in ipaddress.summarize_address_range(ipaddress.IPv4Address(first),
                                                                        ipaddress.IPv4Address(last)):
                            for omit_ip in ipaddr:
                                if any(str(omit_ip) == address for address in free_list):
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
            print("tsig_update: failed for %s error %s" % (hostname, str(e)))
            return False

    def tsig_delete(self, hostname, domain, address, prefix):
        try:
            host_fqdn = hostname + '.' + domain + '.'
            last_octet = address.split('.')[3]
            octets = 4 - math.trunc(prefix / 8)
            reverse = dns.reversename.from_address(address)
            arpa_zone = b'.'.join(dns.name.from_text(str(reverse)).labels[octets:]).decode('utf-8')
            keyring = dns.tsigkeyring.from_text({self.tsig_keyName: self.tsig_key})
            update = dns.update.Update(self.dns_domain, keyring=keyring, keyalgorithm=getattr(dns.tsig, self.tsig_keyAlgorithm))
            update.delete(host_fqdn, 'A')
            response = dns.query.tcp(update, self.dns_server)
            update = dns.update.Update(arpa_zone, keyring=keyring, keyalgorithm=getattr(dns.tsig, self.tsig_keyAlgorithm))
            update.delete(last_octet, 'PTR')
            response = dns.query.tcp(update, self.dns_server)
            return True
        except Exception as e:
            print("tsig_delete: failed for %s error %s" % (hostname, str(e)))
            return False
