##
##

import os
import logging
import attr
import json
from shutil import copyfile
from attr.validators import instance_of as io
from enum import Enum
from typing import Union
import functools
from lib.util.generator import Generator
import lib.config as config
from lib.exceptions import DirectoryStructureError, MissingParameterError, CatalogInvalid
from lib.util.cfgmgr import ConfigMgr
from lib.invoke import tf_run, packer_run
from lib.util.inquire import Inquire

logger = logging.getLogger(__name__)


@functools.total_ordering
class ValueOrderedEnum(Enum):
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class PathType(Enum):
    IMAGE = 0
    NETWORK = 1
    CLUSTER = 2
    APP = 3
    SGW = 4
    CONFIG = 5
    GENERIC = 6
    OTHER = 7


class PathFile(Enum):
    IMAGE = "main.pkr.json"
    NETWORK = "main.tf.json"
    CLUSTER = "main.tf.json"
    APP = "main.tf.json"
    SGW = "main.tf.json"
    CONFIG = "config.json"
    GENERIC = "main.tf.json"
    OTHER = None


class PathExec(Enum):
    IMAGE = 1
    NETWORK = 0
    CLUSTER = 0
    APP = 0
    SGW = 0
    CONFIG = 3
    GENERIC = 0
    OTHER = 3


class ExecType(Enum):
    TF_EXEC = 0
    PK_EXEC = 1
    OTHER = 3


class PathOrder(ValueOrderedEnum):
    IMAGE = 0
    NETWORK = 5
    CLUSTER = 4
    APP = 2
    SGW = 3
    CONFIG = 7
    GENERIC = 1
    OTHER = 6


@attr.s
class ConfigFile(object):
    file_path = attr.ib(validator=io(str))
    file_name = attr.ib(validator=io(str))

    @classmethod
    def from_catalog(cls, json_data: dict):
        return cls(
            json_data.get('path'),
            json_data.get('file'),
            )


@attr.s
class DatastoreEntry(object):
    cloud = attr.ib(validator=io(str))
    name = attr.ib(validator=io(str))
    mode = attr.ib(validator=io(str))

    @classmethod
    def build(cls, cloud: str, name: str, mode: str):
        return cls(
            cloud,
            name,
            mode
            )

    @property
    def as_str(self):
        return json.dumps(self.__dict__)


@attr.s
class BaseCatalogEntry(object):
    entry = attr.ib(validator=io(dict))

    @classmethod
    def create(cls, mode: str, path: str):
        return cls(
            {mode: path}
            )

    def as_key(self, key):
        response = {key: self.__dict__['entry']}
        return response


@attr.s
class NodeCatalogEntry(object):
    entry = attr.ib(validator=io(dict))

    @classmethod
    def create(cls, cloud: str, mode: str, path: str):
        return cls(
            BaseCatalogEntry.create(mode, path).as_key(cloud)
            )

    def as_key(self, key):
        response = {key: self.__dict__['entry']}
        return response


@attr.s
class DatastoreTuple(object):
    cloud = attr.ib(validator=io(str))
    mode = attr.ib(validator=io(Enum))
    path = attr.ib(validator=io(str))
    file = attr.ib(validator=io(str))
    switch = attr.ib(validator=io(Enum))
    exec = attr.ib(validator=attr.validators.instance_of((tf_run, packer_run, type(None))))

    @classmethod
    def build(cls, cloud: str, mode: Enum, path: str, file: str):
        switch = ExecType(PathExec[mode.name].value)
        if switch.value == ExecType.TF_EXEC.value:
            run_exec = tf_run(working_dir=path)
        elif switch.value == ExecType.PK_EXEC.value:
            run_exec = packer_run(working_dir=path)
        else:
            run_exec = None
        return cls(
            cloud,
            mode,
            path,
            file,
            switch,
            run_exec
            )

    @property
    def as_dict(self):
        return self.__dict__

    @property
    def as_tuple(self):
        return self.mode, self.path, self.file, self.switch, self.exec

    def validate(self):
        if self.switch.value == ExecType.TF_EXEC.value:
            if not self.exec.validate():
                self.exec.init()
        elif self.switch.value == ExecType.PK_EXEC.value:
            self.exec.init(self.file)

    def remove(self):
        if self.switch.value == ExecType.TF_EXEC.value:
            self.exec.destroy(quiet=True)


class PathMap(object):

    def __init__(self, name: str, cloud: str):
        self.path = {}
        self.cloud = cloud
        self.name = name
        if 'CLOUD_MANAGER_DATABASE_LOCATION' in os.environ:
            self.root = os.environ['CLOUD_MANAGER_DATABASE_LOCATION']
        else:
            self.root = f"{config.package_dir}/db"
        self.path['root'] = self.root
        self.cm = CatalogManager(self.root)
        self._last_mapped = None

    def map(self, mode: Enum) -> None:
        if mode.value == PathType.IMAGE.value:
            path_name = Generator.get_host_id()
        else:
            path_name = self.name
        uuid = Generator.get_uuid(DatastoreEntry.build(self.cloud, path_name, mode.name.lower()).as_str)
        path_dir = f"{self.root}/{uuid}"
        self.path_check(path_dir)
        self.path[mode.name.lower()] = {
            'path': path_dir,
            'file': None
        }
        if mode.value == PathType.IMAGE.value:
            self.cm.update('images', BaseCatalogEntry.create(mode.name.lower(), path_dir).as_key(self.cloud))
        else:
            self.cm.update('inventory', NodeCatalogEntry.create(self.cloud, mode.name.lower(), path_dir).as_key(self.name))
        self._last_mapped = mode.name.lower()
        logger.debug(f"mapping path {path_dir} for {self.name}")

    @staticmethod
    def map_suffix(mode) -> str:
        if mode == 0:
            return "-image"
        elif mode == 1:
            return "-network"
        elif mode == 2:
            return "-cluster"
        elif mode == 3:
            return "-app"
        elif mode == 4:
            return "-sgw"
        elif mode == 5:
            return "-config"
        elif mode == 6:
            return "-other"

    @staticmethod
    def path_check(path):
        if not os.path.exists(path):
            logger.debug(f"creating directory {path}")
            try:
                os.mkdir(path)
            except Exception as err:
                raise DirectoryStructureError(f"can not create path {path}: {err}")

    def use(self, file: str, mode: Enum) -> ConfigFile:
        self.path[mode.name.lower()]['file'] = self.path_prefix(mode) + file
        return ConfigFile.from_catalog(self.path[mode.name.lower()])

    def file(self, mode: Enum) -> Union[str, None]:
        return self.path.get(mode.name.lower(), {}).get('file')

    def exists(self, mode: Enum) -> Union[str, bool]:
        file_name = self.path.get(mode.name.lower(), {}).get('file')
        if file_name:
            return os.path.exists(file_name)
        else:
            return False

    def get_path(self, mode: Enum) -> str:
        try:
            return self.path[mode.name.lower()]['path']
        except KeyError:
            raise ValueError(f"path not mapped for {mode.name.lower()}")

    def path_prefix(self, mode: Enum) -> str:
        try:
            return self.path[mode.name.lower()]['path'] + '/'
        except KeyError:
            raise ValueError(f"path not mapped for {mode.name.lower()}")

    @property
    def last_mapped(self):
        return self._last_mapped

    @property
    def as_dict(self):
        return self.__dict__['path']

    @property
    def get_root(self):
        return self.root


class CatalogManager(object):

    def __init__(self, location):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not os.path.exists(location):
            raise DirectoryStructureError(f"can not find catalog location {location}")
        self._location = location
        self._catalog = location + '/catalog.json'
        self._catalog_backup = location + '/catalog.backup'
        self._leaf_list = []
        if not os.path.exists(self._catalog):
            logger.debug(f"initializing new catalog file at {self._catalog}")
            empty = {
                "config": {
                    "version": config.config_version
                }
            }
            try:
                with open(self._catalog, 'w') as catalog_file:
                    json.dump(empty, catalog_file)
            except Exception as err:
                raise DirectoryStructureError(f"can not write to catalog file {self._catalog}: {err}")

    def update(self, name: str, data: dict):
        contents = self.read_file()
        source = {name: data}
        contents = self.merge(source, contents)
        self.write_file(contents)

    def merge(self, src: dict, dst: dict):
        for key in src:
            if key in dst:
                if isinstance(src[key], dict) and isinstance(dst[key], dict):
                    dst[key] = self.merge(src[key], dst[key])
                    continue
            dst[key] = src[key]
        return dst

    def read_file(self) -> dict:
        try:
            with open(self._catalog, 'r') as catalog_file:
                data = json.load(catalog_file)
            return data
        except Exception as err:
            raise DirectoryStructureError(f"can not read catalog file {self._catalog}: {err}")

    def write_file(self, data: dict) -> None:
        try:
            copyfile(self._catalog, self._catalog_backup)
            with open(self._catalog, 'w') as catalog_file:
                json.dump(data, catalog_file)
        except Exception as err:
            raise DirectoryStructureError(f"can not read catalog file {self._catalog}: {err}")

    def check(self, fix: bool = False) -> None:
        contents = self.read_file()

        config_vers = contents.get('config', {}).get('version')

        if not config_vers:
            raise CatalogInvalid("can not determine catalog version")

        if config.config_version != config_vers:
            print(f"[!] Warning: catalog version mismatch: catalog version {config_vers} expected {config.config_version}")

        print("=== Phase 1 (checking leaf paths)")

        if contents.get('images'):
            contents['images'] = self.catalog_walk(contents.get('images'), fix)

        if contents.get('inventory'):
            for environment in contents.get('inventory'):
                contents['inventory'][environment] = self.catalog_walk(contents['inventory'].get(environment), fix)

        print("=== Phase 2 (check orphaned leafs)")

        self.check_leafs(fix)

        self.write_file(contents)

    def catalog_walk(self, contents: dict, fix: bool) -> dict:
        for item in contents:
            for leaf in contents[item]:
                leaf_path = contents[item][leaf]
                contents[item][leaf] = self.check_path(f"{item}.{leaf}", leaf_path, fix)
        return contents

    def check_path(self, node: str, path: str, fix: bool) -> str:
        basename = os.path.basename(path)
        self._leaf_list.append(basename)
        if not os.path.exists(path):
            print(f"[!] Invalid leaf for node {node}")
            if fix:
                new_path = f"{self._location}/{basename}"
                print(f"  => [i] repairing leaf {node} >> {basename}")
                return new_path
        return path

    @staticmethod
    def recursive_remove(path):
        file_list = []
        dir_list = []
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                full_path = os.path.join(root, name)
                if full_path not in file_list:
                    file_list.append(full_path)
            for name in dirs:
                full_path = os.path.join(root, name)
                if full_path not in dir_list:
                    dir_list.append(full_path)
            if root not in dir_list:
                dir_list.append(root)
        try:
            for file in file_list:
                os.remove(file)
            for directory in dir_list:
                os.rmdir(directory)
        except Exception as err:
            raise DirectoryStructureError(f"can not remove path {path}: {err}")

    def check_leafs(self, fix: bool) -> None:
        for name in os.listdir(self._location):
            full_path = f"{self._location}/{name}"
            if os.path.isdir(full_path):
                if name not in self._leaf_list:
                    print(f"[!] Orphaned leaf {name}")
                    if fix:
                        print(f"  => [i] removing orphaned leaf {name}")
                        self.recursive_remove(full_path)

    def get_environment(self, env_name: str):
        contents = self.read_file()
        if contents.get('inventory'):
            for environment in contents.get('inventory'):
                if env_name == environment:
                    for cloud in contents.get('inventory').get(environment):
                        yield cloud, contents['inventory'][environment][cloud]

    def remove_environment(self, env_name: str):
        contents = self.read_file()
        if contents.get('inventory'):
            if contents.get('inventory').get(env_name):
                del contents['inventory'][env_name]
        self.write_file(contents)

    def catalog_list(self) -> None:
        contents = self.read_file()
        if contents.get('inventory'):
            for environment in contents.get('inventory'):
                print(f"{environment}")
                for cloud in contents.get('inventory').get(environment):
                    print(f"  - {cloud}")
                    path_map = PathMap(environment, cloud)
                    path_map.map(PathType.CONFIG)
                    cfg_file: ConfigFile
                    cfg_file = path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
                    env_cfg = ConfigMgr(cfg_file.file_name)
                    region = env_cfg.get(f"{cloud}_region")
                    ssh_key = env_cfg.get("ssh_private_key")
                    if cloud == "aws":
                        network = env_cfg.get("aws_vpc_id")
                    else:
                        network = env_cfg.get(f"{cloud}_network")
                    print(f"    Region: {region}")
                    print(f"    SSK Key: {ssh_key}")
                    print(f"    Network: {network}")
                    for node_type in contents.get('inventory').get(environment).get(cloud):
                        cluster_map = env_cfg.get(f"{cloud}_node_map_{node_type}")
                        if cluster_map:
                            print(f"    - {node_type}")
                            if cloud == "capella":
                                for group in cluster_map['server_groups']:
                                    print(f"      Nodes:    {group['size']}")
                                    print(f"      Compute:  {group['compute']}")
                                    print(f"      Services: {','.join(group['services'])}")
                            else:
                                for node in cluster_map:
                                    print(f"      Name:     {node} ({cluster_map[node]['instance_type']})")
                                    if cluster_map[node]['node_services']:
                                        print(f"      Services: {cluster_map[node]['node_services']}")


class LogViewer(object):
    IMAGE_LOG = "build.log"
    DEPLOY_LOG = "deploy.log"

    def __init__(self, parameters):
        self.logger = logging.getLogger(self.__class__.__name__)

        if not config.env_name and not parameters.log_command == "image":
            raise MissingParameterError("environment name not specified, please use the --name parameter to select an environment")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.log_path = None
        self.log_file = None

        if parameters.log_command == "image":
            self.path_map.map(PathType.IMAGE)
            self.log_path = self.path_map.get_path(PathType.IMAGE)
            self.log_file = LogViewer.IMAGE_LOG
        elif parameters.log_command == "vpc":
            self.path_map.map(PathType.NETWORK)
            self.log_path = self.path_map.get_path(PathType.NETWORK)
            self.log_file = LogViewer.DEPLOY_LOG
        elif parameters.log_command == "app":
            self.path_map.map(PathType.APP)
            self.log_path = self.path_map.get_path(PathType.APP)
            self.log_file = LogViewer.DEPLOY_LOG
        elif parameters.log_command == "sgw":
            self.path_map.map(PathType.SGW)
            self.log_path = self.path_map.get_path(PathType.SGW)
            self.log_file = LogViewer.DEPLOY_LOG
        else:
            self.path_map.map(PathType.CLUSTER)
            self.log_path = self.path_map.get_path(PathType.CLUSTER)
            self.log_file = LogViewer.DEPLOY_LOG

    def print_log(self, lines=25):
        if not self.log_path:
            raise MissingParameterError(f"could not determine log path, please check the parameters and try again.")

        read_file = self.log_path + '/' + self.log_file

        if not os.path.exists(read_file):
            print(f"No log files found.")
            return

        with open(read_file, 'r') as log_file_h:
            for line in (log_file_h.readlines()[-lines:]):
                print(line, end='')


class DBPathMux(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def __call__(self, cloud: str, key: str, value: str):
        for e in PathType:
            if e.name.lower() == key:
                return DatastoreTuple.build(cloud, e, value, PathFile[e.name].value)


class EnvUtil(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cm = CatalogManager(config.catalog_root)
        self.mux = DBPathMux()

    def env_elements(self):
        for cloud, contents in self.cm.get_environment(config.env_name):
            elements = [PathOrder[k.upper()] for k in contents.keys()]
            elements = sorted(elements, key=lambda x: x.value)
            for element in elements:
                key = element.name.lower()
                yield self.mux(cloud, key, contents[key])

    def env_remove(self):
        if Inquire().ask_yn(f"Remove entire environment {config.env_name}", default=False):
            for element in self.env_elements():
                print(f"Removing {element.cloud} components for {element.mode.name.lower()}")
                element.validate()
                element.remove()
            self.cm.remove_environment(config.env_name)
