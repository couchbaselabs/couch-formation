##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from lib.exceptions import ConfigManagerError
from shutil import copyfile


@attr.s
class SSHSettings(object):
    name = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    public_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    private_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    user_name = attr.ib(validator=attr.validators.optional(io(str)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AWSSettings(object):
    region = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    ami_id = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    machine_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    key_pair = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    vpc_id = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    subnet_ids = attr.ib(validator=attr.validators.optional(io(list[str])), default=None)
    security_group_id = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_iops = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CBSettings(object):
    index_memory = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    version = attr.ib(validator=attr.validators.optional(io(str)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Config(object):
    ssh = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "SSHSettings"})
    aws = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "AWSSettings"})
    cbs = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "CBSettings"})

    @property
    def as_dict(self):
        return self.__dict__


class ConfigMgr(object):

    def __init__(self, filename):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.filename = filename
        self.config_data = {}

    def get_config(self) -> bool:
        try:
            with open(self.filename, 'r') as config_file:
                data_read = json.load(config_file)
                for category in Config.__attrs_attrs__:
                    self.config_data[category.name] = Config(
                        data_read.get(category.name)
                    ).as_dict[category.name]
            return True
        except Exception as err:
            raise ConfigManagerError(f"can not read config file {self.filename}: {err}")

    def update_config(self, **kwargs) -> None:
        for arg in kwargs.keys():
            prefix, suffix = arg.split("_", 1)
            for category in Config.__attrs_attrs__:
                _class_name = category.metadata['_class_name']
                _config_class = globals()[_class_name]
                for attribute in _config_class.__attrs_attrs__:
                    if suffix == attribute.name:
                        part = {suffix: kwargs[arg]}
                        self.config_data[prefix].update(part)

    def write_config(self) -> None:
        try:
            with open(self.filename, 'w') as config_file:
                json.dump(self.config_data, config_file)
        except Exception as err:
            raise ConfigManagerError(f"can not read catalog file {self.filename}: {err}")
