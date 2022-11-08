##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from typing import Iterable
from lib.util.envmgr import EnvironmentManager
from lib.exceptions import AWSDriverError
from lib.drivers.cbrelease import CBRelease
from lib.util.inquire import Inquire
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
    DRIVER_CONFIG = "aws.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        environment = EnvironmentManager()
        self.env = environment.create()
        self.ask = Inquire()

        self.driver_config = self.env.db_dir + "/" + CloudDriver.DRIVER_CONFIG
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

    def create_env(self):
        provider_block = AWSProvider.for_region("region_name").as_dict

        cf_vpc = VPCResource.construct("cf_vpc_cidr", "cf_env_name").as_dict

        cf_gw = InternetGatewayResource.construct("cf_vpc", "cf_env_name").as_dict

        route_entry = RouteEntry.construct("cf_gw", "cf_vpc", "cf_env_name")
        route_entry.add("0.0.0.0/0", "cf_gw")
        cf_rt = RouteResource.construct(route_entry.as_dict).as_dict

        subnet_list = [
            "cf_subnet_1",
            "cf_subnet_2",
            "cf_subnet_3"
        ]

        subnet_struct = SubnetResource.build()
        association_struct = RTAssociationResource.build()
        for item in subnet_list:
            subnet_struct.add(item, "cf_subnet_az_1", "cf_subnet_cidr_1", True, "cf_env_name", "cf_vpc")
            association_struct.add("cf_rt", item)
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

        var_list = [
            ("cf_env_name", "dev10db", "Couchbase cluster name", "string"),
            ("cf_subnet_az_1", "us-east-2a", "Availability Zone", "string"),
            ("cf_subnet_az_2", "us-east-2b", "Availability Zone", "string"),
            ("cf_subnet_az_3", "us-east-2c", "Availability Zone", "string"),
            ("cf_subnet_cidr_1", "10.11.1.0/24", "Subnet CIDR", "string"),
            ("cf_subnet_cidr_2", "10.11.2.0/24", "Subnet CIDR", "string"),
            ("cf_subnet_cidr_3", "10.11.3.0/24", "Subnet CIDR", "string"),
            ("cf_vpc_cidr", "10.11.0.0/16", "VPC CIDR", "string"),
            ("region_name", "us-east-2", "Region name", "string"),
        ]

        var_struct = Variables.build()
        for item in var_list:
            var_struct.add(Variable.construct(item[0], item[1], item[2], item[3]).as_dict)

        vpc_config = VPCConfig.build().add(provider_block).add(resource_block.as_dict).add(var_struct.as_dict).as_dict
        print(json.dumps(vpc_config, indent=2))
