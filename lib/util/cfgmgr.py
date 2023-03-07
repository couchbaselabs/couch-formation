##
##

import logging
import attr
import json
import os
import time
from attr.validators import instance_of as io
from lib.exceptions import ConfigManagerError


@attr.s
class SSHSettings(object):
    name = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    public_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    private_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    user_name = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    fingerprint = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

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
    subnet_list = attr.ib(validator=attr.validators.optional(io(list[str])), default=None)
    security_group_id = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_iops = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    node_map_cluster = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_app = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_sgw = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_generic = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    sgw_node_list = attr.ib(validator=attr.validators.optional(io(list)), default=None)
    base_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    image_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    node_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_cluster = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_app = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_sgw = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_generic = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    sgw_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPSettings(object):
    region = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    image = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    machine_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    private_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    network = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    subnet_list = attr.ib(validator=attr.validators.optional(io(list[str])), default=None)
    project = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    account_email = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    account_file = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    node_map_cluster = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_app = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_sgw = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_generic = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    sgw_node_list = attr.ib(validator=attr.validators.optional(io(list)), default=None)
    base_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    image_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    node_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_cluster = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_app = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_sgw = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_generic = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    sgw_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureSettings(object):
    region = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    image = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    machine_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    private_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    network = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    subnet_list = attr.ib(validator=attr.validators.optional(io(list[str])), default=None)
    resource_group = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    image_resource_group = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    security_group = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    node_map_cluster = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_app = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_sgw = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_generic = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    sgw_node_list = attr.ib(validator=attr.validators.optional(io(list)), default=None)
    base_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    image_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    node_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_cluster = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_app = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_sgw = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_generic = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    sgw_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CBSettings(object):
    index_memory = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    version = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    sgw_version = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaSettings(object):
    base_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    node_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_cluster = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    region = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    project = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    machine_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_iops = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_type = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    network = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    single_az = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    cluster_name = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    provider = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    support_package = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    node_map_cluster = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_sgw = attr.ib(validator=attr.validators.optional(io(dict)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VMWareSettings(object):
    hostname = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    username = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    password = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    datacenter = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    dc_folder = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    network_folder = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    cluster = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    datastore = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    dvs = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    template = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    private_key = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    network = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    resource_group = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    root_size = attr.ib(validator=attr.validators.optional(io(str)), default=None)
    node_map_cluster = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_app = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_sgw = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    node_map_generic = attr.ib(validator=attr.validators.optional(io(dict)), default=None)
    sgw_node_list = attr.ib(validator=attr.validators.optional(io(list)), default=None)
    base_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    image_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    node_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_cluster = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_app = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_sgw = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    map_in_progress_generic = attr.ib(validator=attr.validators.optional(io(bool)), default=None)
    sgw_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class NetSettings(object):
    use_public_ip = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GeneralConfig(object):
    map_in_progress = attr.ib(validator=attr.validators.optional(io(bool)), default=None)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class Config(object):
    ssh = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "SSHSettings"})
    aws = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "AWSSettings"})
    gcp = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "GCPSettings"})
    azure = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "AzureSettings"})
    capella = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "CapellaSettings"})
    vmware = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "VMWareSettings"})
    cbs = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "CBSettings"})
    net = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "NetSettings"})
    cfg = attr.ib(validator=attr.validators.optional(io(dict)), default=None, metadata={"_class_name": "GeneralConfig"})

    @property
    def as_dict(self):
        return self.__dict__


class ConfigMgr(object):

    def __init__(self, filename):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.filename = filename
        self.config_data = {}
        self.retry_count = 10
        self.unlock_file()
        if not self.exists():
            self.create()

    def get_config(self) -> bool:
        try:
            with open(self.filename, 'r') as config_file:
                data_read = json.load(config_file)
                self.config_data = Config(
                    data_read.get('ssh'),
                    data_read.get('aws'),
                    data_read.get('gcp'),
                    data_read.get('azure'),
                    data_read.get('capella'),
                    data_read.get('vmware'),
                    data_read.get('cbs'),
                    data_read.get('net'),
                    data_read.get('cfg')
                ).as_dict
            return True
        except Exception as err:
            raise ConfigManagerError(f"can not read config file {self.filename}: {err}")

    def update(self, **kwargs) -> None:
        self.get_config()
        for arg in kwargs.keys():
            prefix, suffix = arg.split("_", 1)
            for category in Config.__attrs_attrs__:
                if category.name == prefix:
                    _class_name = category.metadata['_class_name']
                    _config_class = globals()[_class_name]
                    for attribute in _config_class.__attrs_attrs__:
                        if suffix == attribute.name:
                            part = {suffix: kwargs[arg]}
                            if self.config_data[prefix] is None:
                                self.config_data[prefix] = {}
                            self.config_data[prefix].update(part)
        self.write_config()

    def get(self, key: str):
        self.get_config()
        prefix, suffix = key.split("_", 1)
        for category in Config.__attrs_attrs__:
            if category.name == prefix:
                _class_name = category.metadata['_class_name']
                _config_class = globals()[_class_name]
                for attribute in _config_class.__attrs_attrs__:
                    if suffix == attribute.name:
                        if self.config_data[prefix] is None:
                            self.config_data[prefix] = {}
                        return self.config_data[prefix].get(suffix)

    def write_config(self) -> None:
        try:
            self.lock_wait()
            self.lock_file()
            with open(self.filename, 'w') as config_file:
                json.dump(self.config_data, config_file)
            self.unlock_file()
        except Exception as err:
            raise ConfigManagerError(f"can not write config file {self.filename}: {err}")

    def exists(self) -> bool:
        if os.path.exists(self.filename):
            return True
        return False

    def create(self) -> None:
        self.write_config()

    def lock_file(self) -> None:
        lock_file = f"{self.filename}.lck"
        open(lock_file, 'w').close()

    def unlock_file(self) -> None:
        if self.filename == "." or self.filename == ".." or self.filename == "*" or len(self.filename) == 0:
            raise ConfigManagerError(f"unlock_file: unsafe remove operation on file \"{self.filename}\"")
        lock_file = f"{self.filename}.lck"
        if os.path.exists(lock_file):
            os.remove(lock_file)

    def check_lock(self) -> bool:
        lock_file = f"{self.filename}.lck"
        if os.path.exists(lock_file):
            raise ConfigManagerError("configuration file locked")
        return True

    def lock_wait(self) -> bool:
        factor = 0.01
        for retry_number in range(self.retry_count + 1):
            try:
                return self.check_lock()
            except ConfigManagerError:
                if retry_number == self.retry_count:
                    raise ConfigManagerError("timeout waiting on file lock")
                wait = factor
                wait *= (2 ** (retry_number + 1))
                time.sleep(wait)
