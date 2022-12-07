##
##

import logging
from itertools import cycle
from typing import Union

import lib.util.aws_data
from lib.util.inquire import Inquire
from lib.util.cfgmgr import ConfigMgr
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.common import ClusterMapElement, VariableMap


class ClusterCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.node_swap = None
        self.availability_zone_cycle = None
        self.cluster_map = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def create_cloud(self, node_type: str, dc: Union[lib.util.aws_data.DataCollect]):
        node_env = config.env_name
        node = 1
        services = []

        print("")

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
            services = ['data', 'index', 'query', 'fts', 'analytics', 'eventing']
            prefix_text = 'cb'
            min_nodes = config.cb_node_min

        print(f" ==> Creating {node_env} node configuration <==")
        print("")

        if config.cloud_zone:
            self.availability_zone_cycle = cycle(list(i for i in dc.subnet_list if i['zone'] == config.cloud_zone))
        else:
            self.availability_zone_cycle = cycle(dc.subnet_list)

        self.node_swap = Inquire.ask_bool('Configure swap', recommendation='false')

        var_map = VariableMap.build()

        while True:
            dc.get_node_settings()

            machine_data = config.cloud_machine_type().details(dc.instance_type)

            print(f"Machine CPU    = {machine_data['cpu']}")
            print(f"Machine Memory = {machine_data['memory']}")

            selected_services = []
            node_ram = int(machine_data['memory'] / 1024)
            node_name = f"{prefix_text}-{node_env}-n{node:02d}"

            zone_data = next(self.availability_zone_cycle)
            availability_zone = zone_data['zone']
            node_subnet = zone_data['name']

            if node == 1:
                install_mode = 'init'
            else:
                install_mode = 'add'

            print("Configuring node %d" % node)

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
                            None,
                            None,
                            None
                        ).as_dict
                        )

            if node >= min_nodes:
                print("")
                if not Inquire().ask_yn('  ==> Add another node'):
                    break
                print("")
            node += 1

        self.cluster_map = var_map.as_dict
