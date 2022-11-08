##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from typing import Iterable
from lib.util.envmgr import PathMap, PathType
from lib.exceptions import AWSDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
from lib.invoke import tf_run
import lib.config as config
from lib.hcl.aws_vpc import AWSProvider, VPCResource, InternetGatewayResource, RouteEntry, RouteResource, SubnetResource, RTAssociationResource, SecurityGroupEntry, \
    SGResource, Resources, Variables, Variable, VPCConfig


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
    owner = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))
    vars = attr.ib(validator=io(str))
    hcl = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("image"),
            json_data.get("owner"),
            json_data.get("user"),
            json_data.get("vars"),
            json_data.get("hcl"),
            )


class CloudDriver(object):
    VERSION = '3.0.0'
    DRIVER_CONFIG = "aws.json"
    NETWORK_CONFIG = "main.tf.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.path_map = PathMap()
        self.ask = Inquire()

        if not config.env_name:
            raise AWSDriverError("no environment specified")

        self.path_map.map(config.env_name, PathType.IMAGE)
        self.path_map.map(config.env_name, PathType.CLUSTER)
        self.path_map.map(config.env_name, PathType.NETWORK)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise AWSDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        cb_rel = CBRelease()

        os_choice = [i for i in self.config.build.keys()]

        self.ask.ask_list(os_choice)

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

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name", "string"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR", "string"),
            ("region_name", region, "Region name", "string"),
        ]

        if config.cloud_zone:
            print(f"Using single zone: {config.cloud_zone}")
            subnet_count += 1
            if config.cloud_zone not in zone_list:
                raise AWSDriverError(f"zone {config.cloud_zone} not found in region {region}")
            var_list.append(
                ("cf_subnet_az_1", config.cloud_zone, "Availability Zone", "string")
            )
            var_list.append(
                ("cf_subnet_cidr_1", subnet_list[1], "Subnet CIDR", "string")
            )
        else:
            print(f"Using multiple zones: {','.join(zone_list)}")
            for n, zone in enumerate(zone_list):
                subnet_count += 1
                var_list.append(
                    (f"cf_subnet_az_{n+1}", zone, "Availability Zone", "string")
                )
                var_list.append(
                    (f"cf_subnet_cidr_{n+1}", subnet_list[n+1], "Subnet CIDR", "string")
                )

        provider_block = AWSProvider.for_region("region_name").as_dict

        cf_vpc = VPCResource.construct("cf_vpc_cidr", "cf_env_name").as_dict

        cf_gw = InternetGatewayResource.construct("cf_vpc", "cf_env_name").as_dict

        route_entry = RouteEntry.construct("cf_gw", "cf_vpc", "cf_env_name")
        route_entry.add("0.0.0.0/0", "cf_gw")
        cf_rt = RouteResource.construct(route_entry.as_dict).as_dict

        subnet_struct = SubnetResource.build()
        association_struct = RTAssociationResource.build()
        for i in range(subnet_count):
            subnet_name = f"cf_subnet_{i+1}"
            subnet_struct.add(subnet_name, f"cf_subnet_az_{i+1}", f"cf_subnet_cidr_{i+1}", True, "cf_env_name", "cf_vpc")
            association_struct.add("cf_rt", subnet_name)
        subnet_resources = subnet_struct.as_dict
        rt_association_resources = association_struct.as_dict

        sg_entry = SecurityGroupEntry.construct("cf_vpc", "cf_env_name")
        sg_entry.add_ingress("0.0.0.0/0", 22, "tcp", 22)
        sg_entry.add_ingress("0.0.0.0/0", 8091, "tcp", 8097)
        sg_entry.add_ingress("0.0.0.0/0", 9123, "tcp", 9123)
        sg_entry.add_ingress("0.0.0.0/0", 9140, "tcp", 9140)
        sg_entry.add_ingress("0.0.0.0/0", 11210, "tcp", 11210)
        sg_entry.add_ingress("0.0.0.0/0", 11280, "tcp", 11280)
        sg_entry.add_ingress("0.0.0.0/0", 11207, "tcp", 11207)
        sg_entry.add_ingress("0.0.0.0/0", 18091, "tcp", 18097)
        cf_sg = SGResource.construct(sg_entry.as_dict).as_dict

        resource_block = Resources.build()
        resource_block.add(cf_vpc)
        resource_block.add(subnet_resources)
        resource_block.add(rt_association_resources)
        resource_block.add(cf_gw)
        resource_block.add(cf_rt)
        resource_block.add(cf_sg)

        var_struct = Variables.build()
        for item in var_list:
            var_struct.add(Variable.construct(item[0], item[1], item[2], item[3]).as_dict)

        vpc_config = VPCConfig.build().add(provider_block).add(resource_block.as_dict).add(var_struct.as_dict).as_dict

        cfg_file_prefix, net_cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            with open(net_cfg_file, 'w') as cfg_file:
                json.dump(vpc_config, cfg_file, indent=2)
        except Exception as err:
            raise AWSDriverError(f"can not write to network config file {net_cfg_file}: {err}")

        try:
            print("")
            print(f"Creating VPC ...")
            tf = tf_run(working_dir=cfg_file_prefix)
            tf.init()
            if not tf.validate():
                raise AWSDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise AWSDriverError(f"can not create VPC: {err}")

    def destroy_net(self):
        cfg_file_prefix, net_cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            if Inquire().ask_yn(f"Remove VPC for {config.env_name}", default=False):
                tf = tf_run(working_dir=cfg_file_prefix)
                if not tf.validate():
                    tf.init()
                tf.destroy()
        except Exception as err:
            raise AWSDriverError(f"can not destroy VPC: {err}")
