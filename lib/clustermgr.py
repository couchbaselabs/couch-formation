##
##

class clustermgr(object):

    def __init__(self):
        pass

    def create_cluster_config(self):
        inquire = ask()
        resolver = dns.resolver.Resolver()
        config_segments = []
        config_segments.append(CB_CFG_HEAD)
        node = 1
        change_node_ip_address = False
        services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing', ]
        self.set_availability_zone_cycle()

        env_text = self.get_env_string()

        print("Building cluster configuration")
        while True:
            selected_services = []
            node_ip_address = None
            old_ip_address = None
            node_netmask = None
            node_gateway = None
            node_name = "cb-{}-n{:02d}".format(env_text, node)
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
                if not self.domain_name:
                    self.get_domain_name()
                if not self.subnet_cidr:
                    self.get_subnet_cidr()
                if not self.subnet_netmask:
                    self.get_subnet_mask()
                if not self.default_gateway:
                    self.get_subnet_gateway()
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
                NODE_ZONE=availability_zone,
                NODE_SUBNET=node_subnet,
                NODE_IP_ADDRESS=node_ip_address,
                NODE_NETMASK=node_netmask,
                NODE_GATEWAY=node_gateway,
            )
            config_segments.append(format_template)
            if node >= 3:
                print("")
                if not inquire.ask_yn('  ==> Add another node'):
                    break
                print("")
            node += 1

        config_segments.append(CB_CFG_TAIL)
        output_file = 'cluster.tf'
        output_file = self.template_dir + '/' + output_file
        try:
            with open(output_file, 'w') as write_file:
                for i in range(len(config_segments)):
                    write_file.write(config_segments[i])
                write_file.write("\n")
                write_file.close()
        except OSError as e:
            print("Can not write to new cluster file: %s" % str(e))
            sys.exit(1)
