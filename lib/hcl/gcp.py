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
    DRIVER_CONFIG = "gcp.json"
    NETWORK_CONFIG = "main.tf.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.path_map = PathMap.create()
        self.ask = Inquire()

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
        pass

    def create_nodes(self):
        pass

    def create_net(self):
        pass
