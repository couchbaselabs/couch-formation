##
##

import os
import logging
import attr
from attr.validators import instance_of as io
from enum import Enum
from typing import Union
from lib.util.generator import Generator
import lib.util.namegen
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


class DatabaseDirectory(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        if 'CLOUD_MANAGER_DATABASE_LOCATION' in os.environ:
            self.location = os.environ['CLOUD_MANAGER_DATABASE_LOCATION']
        else:
            self.location = f"{config.package_dir}/db"

        self.image_dir = f"{self.location}/img"
        self.environment_dir = f"{self.location}/env"

        self.path_check(self.location)
        self.path_check(self.image_dir)
        self.path_check(self.environment_dir)

    def path_check(self, path):
        if not os.path.exists(path):
            self.logger.info(f"creating directory {path}")
            try:
                self.logger.info(f"creating directory {path}")
                os.mkdir(path)
            except Exception as err:
                raise DirectoryStructureError(f"can not create db {path}: {err}")

    def image_dir(self):
        dir_key = f"{config.cloud}_image"
        uuid = Generator.get_uuid(dir_key)
        img_dir = f"{self.image_dir}/{uuid}"
        self.path_check(img_dir)
        self.logger.info(f"using image repository {img_dir} for cloud {config.cloud}")
        return img_dir

    def env_dir(self, name):
        uuid = Generator.get_uuid(name)
        env_dir = f"{self.environment_dir}/{uuid}"
        self.path_check(env_dir)
        self.logger.info(f"using environment repository {env_dir} for {name}")
        return env_dir


@attr.s
class CloudEnv(object):
    name = attr.ib(validator=io(str))
    repo = attr.ib(validator=io(str))
    db_dir = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, name: str, repo: str, db_dir: str):
        return cls(
            name,
            repo,
            db_dir,
            )


class PathMap(object):

    def __init__(self):
        self.path = {}
        if 'CLOUD_MANAGER_DATABASE_LOCATION' in os.environ:
            self.root = os.environ['CLOUD_MANAGER_DATABASE_LOCATION']
        else:
            self.root = f"{config.package_dir}/db"

    def map(self, name: str, mode: Enum) -> None:
        suffix = self.map_suffix(mode.value)
        uuid = Generator.get_uuid(name + suffix)
        path_dir = f"{self.root}/{uuid}"
        self.path_check(path_dir)
        self.path[mode.name.lower()] = {
            'path': path_dir,
            'file': None
        }
        logger.debug(f"mapping path {path_dir} for {name}")

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

    def use(self, file: str, mode: Enum) -> tuple[str, str]:
        self.path[mode.name.lower()]['file'] = self.path_prefix(mode) + file
        return self.path[mode.name.lower()]['path'], self.path[mode.name.lower()]['file']

    def file(self, mode: Enum) -> Union[str, None]:
        return self.path.get(mode.name.lower(), None).get('file', None)

    def exists(self, mode: Enum) -> Union[str, bool]:
        file_name = self.path.get(mode.name.lower(), False).get('file', False)
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
        return self.__dict__


class EnvironmentManager(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create(self):
        if config.env_name:
            env_name = config.env_name
        else:
            env_name = lib.util.namegen.get_random_name()

        self.logger.info(f"operating on environment {env_name}")

        db = DatabaseDirectory()
        env_dir = db.env_dir(env_name)

        return CloudEnv(env_name, env_dir, db.location)
