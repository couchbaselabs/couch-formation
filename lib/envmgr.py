##
##

import logging
import os
import re
from shutil import copyfile
from lib.location import location
from lib.exceptions import EnvMgrError
from lib.ask import ask


class envmgr(object):
    VARIABLES = [
        ('CB_CLUSTER_NAME', 'cb_cluster_name', 'get_cb_cluster_name', None),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.lc = location()
        self.cloud = None
        self.packer_dir = None
        self.tf_dir = None
        self.env_type = None
        self.env_num = None
        self.dev_num = None
        self.test_num = None
        self.prod_num = None
        self.app_num = None
        self.sgw_num = None
        self.working_dir = None
        self.working_app_dir = None
        self.working_sgw_dir = None
        self.cb_cluster_name = None
        self.cluster_tf_file_name = 'cluster.tf'
        self.variable_tf_file_name = 'variables.tf'

    def set_cloud(self, cloud: str):
        self.cloud = cloud

        if self.cloud == 'aws':
            self.packer_dir = self.lc.aws_packer
            self.tf_dir = self.lc.aws_tf
        elif self.cloud == 'gcp':
            self.packer_dir = self.lc.gcp_packer
            self.tf_dir = self.lc.gcp_tf
        elif self.cloud == 'azure':
            self.packer_dir = self.lc.azure_packer
            self.tf_dir = self.lc.azure_tf
        elif self.cloud == 'vmware':
            self.packer_dir = self.lc.vmware_packer
            self.tf_dir = self.lc.vmware_tf
        else:
            raise EnvMgrError(f"unknown cloud {self.cloud}")

    def set_env(self, dev_num=None, test_num=None, prod_num=None, app_num=None, sgw_num=None):
        if dev_num:
            self.env_type = 'dev'
            self.env_num = dev_num
        elif test_num:
            self.env_type = 'test'
            self.env_num = test_num
        elif prod_num:
            self.env_type = 'prod'
            self.env_num = prod_num
        else:
            raise EnvMgrError("no environment specified")

        if app_num:
            self.app_num = app_num

        if sgw_num:
            self.sgw_num = sgw_num

    @property
    def get_env(self) -> str:
        env_string = f"{self.env_type}:{self.env_num:02d}"
        return env_string

    @property
    def get_app_env(self) -> str:
        app_env_string = f"{self.env_type}{self.env_num:02d}:app{self.app_num:02d}"
        return app_env_string

    @property
    def get_sgw_env(self) -> str:
        sgw_env_string = f"{self.env_type}{self.env_num:02d}:sgw{self.sgw_num:02d}"
        return sgw_env_string

    def get_cb_cluster_name(self, select=True, default=None, write=None):
        inquire = ask()

        if write:
            self.cb_cluster_name = write
            return self.cb_cluster_name

        if self.cb_cluster_name:
            return self.cb_cluster_name

        if self.env_type:
            self.cb_cluster_name = f"{self.env_type}{self.env_num:02d}db"
        else:
            self.cb_cluster_name = 'cbdb'

        if select:
            selection = inquire.ask_text('Couchbase Cluster Name', self.cb_cluster_name, default=default)
            self.cb_cluster_name = selection

        return self.cb_cluster_name

    def create_env(self, overwrite=False, create=True):
        if self.env_type:
            dev_directory = "dev-{:02d}".format(self.env_num)
            self.working_dir = self.tf_dir + '/' + dev_directory
        else:
            raise EnvMgrError("Environment not specified.")

        if self.app_num:
            self.working_app_dir = self.working_dir + '/' + "app-{:02d}".format(self.app_num)

        if self.sgw_num:
            self.working_sgw_dir = self.working_dir + '/' + "sgw-{:02d}".format(self.sgw_num)

        if create:
            try:
                self.create_env_dir(overwrite=overwrite)
            except Exception as err:
                raise EnvMgrError(f"can not create environment structure: {err}")

    @property
    def env_dir(self):
        return self.working_dir

    @property
    def app_env_dir(self):
        return self.working_app_dir

    @property
    def sgw_env_dir(self):
        return self.working_sgw_dir

    @property
    def all_app_dirs(self):
        for file_name in os.listdir(self.working_dir):
            if re.match(r'app-[0-9]+', file_name) or re.match(r'sgw-[0-9]+', file_name):
                yield file_name

    def get_tf_var_file(self):
        tf_var_file = self.env_dir + '/' + self.variable_tf_file_name
        if os.path.exists(tf_var_file):
            return tf_var_file
        else:
            return None

    def get_cluster_var_file(self):
        cluster_var_file = self.env_dir + '/' + self.cluster_tf_file_name
        if os.path.exists(cluster_var_file):
            return cluster_var_file
        else:
            return None

    def create_env_dir(self, overwrite=False):
        copy_files = [
            'locals.json',
            'main.tf',
            'variables.template',
            'outputs.tf',
        ]
        app_files = [
            'app_main.tf',
            'app_outputs.tf',
        ]
        sgw_files = [
            'sgw_main.tf',
            'sgw_outputs.tf',
        ]

        print(f"Creating directory structure for {self.get_env}")

        if not os.path.exists(self.working_dir):
            try:
                self.logger.info("Creating %s" % self.working_dir)
                os.mkdir(self.working_dir)
            except Exception as err:
                raise EnvMgrError(f"can not create {self.working_dir}: {err}")

        if self.working_app_dir:
            if not os.path.exists(self.working_app_dir):
                try:
                    self.logger.info("Creating %s" % self.working_app_dir)
                    os.mkdir(self.working_app_dir)
                except Exception as err:
                    raise EnvMgrError(f"can not create {self.working_app_dir}: {err}")

        if self.working_sgw_dir:
            if not os.path.exists(self.working_sgw_dir):
                try:
                    self.logger.info("Creating %s" % self.working_sgw_dir)
                    os.mkdir(self.working_sgw_dir)
                except Exception as err:
                    raise EnvMgrError(f"can not create {self.working_sgw_dir}: {err}")

        for file_name in copy_files:
            source = self.tf_dir + '/' + file_name
            destination = self.working_dir + '/' + file_name
            if not os.path.exists(destination) or overwrite:
                try:
                    self.logger.info("Copying %s -> %s" % (source, destination))
                    copyfile(source, destination)
                except Exception as err:
                    raise EnvMgrError(f"can not copy {source} -> {destination}: {err}")

        if self.working_app_dir:
            for file_name in app_files:
                source = self.tf_dir + '/' + file_name
                destination = self.working_app_dir + '/' + file_name
                if not os.path.exists(destination) or overwrite:
                    try:
                        self.logger.info("Copying %s -> %s" % (source, destination))
                        copyfile(source, destination)
                    except Exception as err:
                        raise EnvMgrError(f"can not copy {source} -> {destination}: {err}")

        if self.working_sgw_dir:
            for file_name in sgw_files:
                source = self.tf_dir + '/' + file_name
                destination = self.working_sgw_dir + '/' + file_name
                if not os.path.exists(destination) or overwrite:
                    try:
                        self.logger.info("Copying %s -> %s" % (source, destination))
                        copyfile(source, destination)
                    except Exception as err:
                        raise EnvMgrError(f"can not copy {source} -> {destination}: {err}")
