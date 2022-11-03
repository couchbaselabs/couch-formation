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
        pass
