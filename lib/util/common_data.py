##
##

import logging
from itertools import cycle
from typing import Union
import lib.util.aws_data
import lib.util.gcp_data
import lib.util.azure_data
import lib.util.vmware_data
import lib.util.capella_data
from lib.util.inquire import Inquire
from lib.util.cfgmgr import ConfigMgr
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.common import ClusterMapElement, VariableMap, CapellaServerGroup, CapellaServerGroupList
from lib.drivers.cbrelease import CBRelease
from lib.util.network import NetworkUtil


class ClusterCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.node_swap = None
        self.availability_zone_cycle = None
        self.cluster_map = None
        self.cluster_node_list = []
        self.sgw_version = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def create_cloud(self, node_type: str,
                     dc: Union[lib.util.aws_data.DataCollect,
                               lib.util.gcp_data.DataCollect,
                               lib.util.azure_data.DataCollect,
                               lib.util.vmware_data.DataCollect]):
        node_env = config.env_name
        node = 1
        group = 1
        services = []

        if node_type == "app":
            min_nodes = 1
            prefix_text = 'app'
        elif node_type == "sgw":
            min_nodes = 1
            prefix_text = 'sgw'
        elif node_type == "generic":
            min_nodes = 1
            prefix_text = 'node'
        else:
            node_type = 'cluster'
            services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing']
            prefix_text = 'cb'
            min_nodes = config.cb_node_min

        print("")
        in_progress = self.env_cfg.get(f"{config.cloud}_map_in_progress_{node_type}")
        if in_progress is not None and in_progress is False:
            print("Node configuration is complete")
            print("")

            self.cluster_map = self.env_cfg.get(f"{config.cloud}_node_map_{node_type}")
            for item in self.cluster_map:
                print(f"  [{item}]")
                for element in self.cluster_map[item]:
                    print(f"    {element.ljust(16)} = {self.cluster_map[item][element]}")

            print("")
            if not Inquire().ask_bool("Create new node configuration", recommendation='false'):
                return

        self.env_cfg.update(**{f"{config.cloud}_map_in_progress_{node_type}": True})

        print(f" ==> Creating {node_env} {node_type} node configuration <==")
        print("")

        if config.cloud_zone:
            self.availability_zone_cycle = cycle(list(i for i in dc.subnet_list if i['zone'] == config.cloud_zone))
        else:
            self.availability_zone_cycle = cycle(dc.subnet_list)

        self.node_swap = Inquire.ask_bool('Configure swap', recommendation='false')

        var_map = VariableMap.build()
        net = NetworkUtil()

        while True:
            dc.get_node_settings()

            machine_data = config.cloud_machine_type().details(dc.instance_type)

            selected_services = []
            node_ram = int(machine_data['memory'] / 1024)

            zone_data = next(self.availability_zone_cycle)
            availability_zone = zone_data['zone']
            node_subnet = zone_data['name']

            print("")
            print(f"Configuring group {group}")

            node_count = Inquire().ask_int("Node count", min_nodes, min_nodes)

            print("")
            print("Select services")

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

            for n in range(node_count):
                node_name = f"{prefix_text}-{node_env}-n{node:02d}"
                node_ip_address = None
                node_netmask = None
                node_gateway = None

                if node == 1:
                    install_mode = 'init'
                else:
                    install_mode = 'add'

                if config.static_ip:
                    print("")
                    node_ip_address = net.get_static_ip(node_name, dc.domain_name, dc.dns_server_list)
                    node_netmask = str(net.netmask)
                    node_gateway = net.gateway

                var_map.add(node_name,
                            ClusterMapElement.construct(
                                install_mode,
                                node_env,
                                node,
                                ','.join(selected_services),
                                node_subnet,
                                availability_zone,
                                str(node_ram),
                                self.node_swap,
                                dc.instance_type,
                                str(dc.disk_iops),
                                str(dc.disk_size),
                                dc.disk_type,
                                node_gateway,
                                node_ip_address,
                                node_netmask
                            ).as_dict
                            )
                node += 1

            print("")
            if not Inquire().ask_yn('  ==> Add another server group'):
                break
            print("")

        self.cluster_map = var_map.as_dict
        self.env_cfg.update(**{f"{config.cloud}_node_map_{node_type}": self.cluster_map})
        self.env_cfg.update(**{f"{config.cloud}_map_in_progress_{node_type}": False})

    def create_sgw(self, data: dict):
        print("")
        in_progress = self.env_cfg.get(f"{config.cloud}_sgw_in_progress")
        if in_progress is not None and in_progress is False:
            print("Sync Gateway configuration is complete")
            print("")

            self.sgw_version = self.env_cfg.get(f"cbs_sgw_version")
            self.cluster_node_list = self.env_cfg.get(f"{config.cloud}_sgw_node_list")
            print(f"SGW Version                    = {self.sgw_version}")
            print(f"Sync Gateway connected cluster = {','.join(list(i for i in self.cluster_node_list))}")

            print("")
            if not Inquire().ask_bool("Create new SGW configuration", recommendation='false'):
                return

        self.env_cfg.update(**{f"{config.cloud}_sgw_in_progress": True})

        for item in data:
            if item == 'node-private':
                self.cluster_node_list.clear()
                for n, host in enumerate(data[item]['value']):
                    self.cluster_node_list.append(host)

        if len(self.cluster_node_list) == 0:
            print("")
            answer = Inquire().ask_ip("IP address to connect to Couchbase Server")
            self.cluster_node_list.clear()
            self.cluster_node_list.append(answer)

        versions_list = CBRelease().get_sgw_versions()
        release_list = sorted(versions_list, reverse=True)
        self.sgw_version = Inquire().ask_list_basic('Select Sync Gateway version', release_list)

        self.env_cfg.update(**{f"cbs_sgw_version": self.sgw_version})
        self.env_cfg.update(**{f"{config.cloud}_sgw_node_list": self.cluster_node_list})
        self.env_cfg.update(**{f"{config.cloud}_sgw_in_progress": False})

    def create_capella(self, dc: Union[lib.util.capella_data.DataCollect]):
        group = 1
        services = config.cloud_base().SERVICES

        print("")
        in_progress = self.env_cfg.get("capella_map_in_progress_cluster")
        if in_progress is not None and in_progress is False:
            print("Node configuration is complete")
            print("")

            self.cluster_map = self.env_cfg.get("capella_node_map_cluster")
            for n, item in enumerate(self.cluster_map.get('server_groups')):
                print(f"  Group {n+1}:")
                for element in item:
                    print(f"    {element.ljust(16)} = {item[element]}")

            print("")
            if not Inquire().ask_bool("Create new node configuration", recommendation='false'):
                return

        self.env_cfg.update(**{"capella_map_in_progress_cluster": True})

        print(f" ==> Creating Capella server group configuration <==")
        print("")

        server_groups = CapellaServerGroupList.build()

        while True:
            selected_services = []
            dc.get_node_settings()

            print("Configuring group %d" % group)

            node_count = Inquire().ask_int("Node count", 3, 1)

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

            server_groups.add(
                CapellaServerGroup.construct(
                   dc.machine_type,
                   selected_services,
                   node_count,
                   str(dc.disk_size),
                   dc.disk_type,
                   str(dc.disk_iops) if dc.disk_iops else None
                ).as_dict
            )

            print("")
            if not Inquire().ask_yn('  ==> Add another server group'):
                break
            print("")
            group += 1

        self.cluster_map = server_groups.as_dict
        self.env_cfg.update(**{"capella_node_map_cluster": self.cluster_map})
        self.env_cfg.update(**{"capella_map_in_progress_cluster": False})
