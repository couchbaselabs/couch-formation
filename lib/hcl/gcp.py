##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from typing import Iterable
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.exceptions import GCPDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
import lib.config as config
from lib.invoke import tf_run
from lib.hcl.gcp_vpc import GCPProvider, NetworkResource, SubnetResource, FirewallResource, Variables, Variable, VPCConfig, Resources


@attr.s
class Build(object):
    build = attr.ib(validator=io(dict))

    @classmethod
    def from_config(cls, json_data: dict):
        return cls(
            json_data.get("build"),
            )


@attr.s
class Entry(object):
    versions = attr.ib(validator=io(Iterable))

    @classmethod
    def from_config(cls, distro: str, json_data: dict):
        return cls(
            json_data.get(distro),
            )


@attr.s
class Record(object):
    version = attr.ib(validator=io(str))
    image = attr.ib(validator=io(str))
    family = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))
    vars = attr.ib(validator=io(str))
    hcl = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("image"),
            json_data.get("family"),
            json_data.get("user"),
            json_data.get("vars"),
            json_data.get("hcl"),
            )


class CloudDriver(object):
    VERSION = '3.0.0'
    DRIVER_CONFIG = "gcp.json"
    NETWORK_CONFIG = "main.tf.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise GCPDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.IMAGE)
        self.path_map.map(PathType.CLUSTER)
        self.path_map.map(PathType.NETWORK)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise GCPDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        pass

    def create_nodes(self):
        pass

    def create_net(self):
        cidr_util = NetworkDriver()
        subnet_count = 0

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        vpc_cidr = cidr_util.get_next_network()
        subnet_list = list(cidr_util.get_next_subnet())
        zone_list = config.cloud_base().zones()
        region = config.cloud_base().region
        project = config.cloud_base().project
        account_file = config.cloud_base().account_file

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name", "string"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR", "string"),
            ("region_name", region, "Region name", "string"),
            ("cf_gcp_account_file", account_file, "Region name", "string"),
            ("cf_gcp_project", project, "Region name", "string"),
            ("cf_subnet_cidr_1", subnet_list[1], "Region name", "string"),
        ]

        provider_block = GCPProvider.for_region("cf_gcp_account_file", "cf_gcp_project", "region_name")

        network_block = NetworkResource.construct(False, "cf_env_name")

        subnet_block = SubnetResource.construct("cf_subnet_cidr_1", "cf_env_name", "cf_vpc", "region_name")

        firewall_block = FirewallResource.build("cf_env_name", "cf_vpc", "cf_vpc_cidr")
        firewall_block.add("cf-fw-cb",
                           ["8091-8097", "9123", "9140", "11210", "11280", "11207", "18091-18097", "4984-4986"],
                           "tcp",
                           "cf_env_name",
                           "cf_vpc",
                           ["0.0.0.0/0"])
        firewall_block.add("cf-fw-ssh", ["22"], "tcp", "cf_env_name", "cf_vpc", ["0.0.0.0/0"])

        resource_block = Resources.build()
        resource_block.add(network_block.as_dict)
        resource_block.add(subnet_block.as_dict)
        resource_block.add(firewall_block.as_dict)

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2], item[3]).as_dict)

        vpc_config = VPCConfig.build()\
            .add(provider_block.as_dict)\
            .add(resource_block.as_dict)\
            .add(var_block.as_dict).as_dict

        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(vpc_config, cfg_file_h, indent=2)
        except Exception as err:
            raise GCPDriverError(f"can not write to network config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Creating VPC ...")
            tf = tf_run(working_dir=cfg_file.file_path)
            tf.init()
            if not tf.validate():
                raise GCPDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise GCPDriverError(f"can not create VPC: {err}")

    def destroy_net(self):
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            if Inquire().ask_yn(f"Remove VPC for {config.env_name}", default=False):
                tf = tf_run(working_dir=cfg_file.file_path)
                if not tf.validate():
                    tf.init()
                tf.destroy()
        except Exception as err:
            raise GCPDriverError(f"can not destroy VPC: {err}")
