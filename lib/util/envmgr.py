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
from lib.util.generator import Generator
import lib.config as config
from lib.exceptions import DirectoryStructureError

logger = logging.getLogger(__name__)


class PathType(Enum):
    IMAGE = 0
    NETWORK = 1
    CLUSTER = 2
    APP = 3
    SGW = 4
    CONFIG = 5
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


class PathMap(object):

    def __init__(self, name: str, cloud: str):
        self.path = {'cloud': cloud}
        self.cloud = cloud
        self.name = name
        if 'CLOUD_MANAGER_DATABASE_LOCATION' in os.environ:
            self.root = os.environ['CLOUD_MANAGER_DATABASE_LOCATION']
        else:
            self.root = f"{config.package_dir}/db"
        self.path['root'] = self.root
        self.cm = CatalogManager(self.root)

    def map(self, mode: Enum) -> None:
        suffix = self.map_suffix(mode.value)
        if mode.value == PathType.IMAGE.value:
            name_prefix = self.cloud
        else:
            name_prefix = self.name
        uuid = Generator.get_uuid(name_prefix + suffix)
        path_dir = f"{self.root}/{uuid}"
        self.path_check(path_dir)
        self.path[mode.name.lower()] = {
            'path': path_dir,
            'file': None
        }
        self.cm.update(name_prefix, self.as_dict)
        logger.debug(f"mapping path {path_dir} for {name_prefix}")

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
        if mode.value == PathType.IMAGE.value:
            name_prefix = self.cloud
        else:
            name_prefix = self.name
        self.path[mode.name.lower()]['file'] = self.path_prefix(mode) + file
        self.cm.update(name_prefix, self.as_dict)
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
    def as_dict(self):
        return self.__dict__['path']


class CatalogManager(object):

    def __init__(self, location):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not os.path.exists(location):
            raise DirectoryStructureError(f"can not find catalog location {location}")
        self._catalog = location + '/catalog.json'
        self._catalog_backup = location + '/catalog.backup'
        if not os.path.exists(self._catalog):
            logger.debug(f"initializing new catalog file at {self._catalog}")
            empty = {}
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
