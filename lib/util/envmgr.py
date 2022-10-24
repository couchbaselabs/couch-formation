##
##

import os
import logging
from lib.util.generator import Generator
import lib.util.namegen
import lib.config as config
from lib.config import RunMode
from lib.exceptions import DirectoryStructureError


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
        return img_dir

    def env_dir(self, name):
        uuid = Generator.get_uuid(name)
        env_dir = f"{self.environment_dir}/{uuid}"
        self.path_check(env_dir)
        return env_dir


class EnvironmentManager(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create(self):
        if config.env_name:
            env_name = config.env_name
        else:
            env_name = lib.util.namegen.get_random_name()


