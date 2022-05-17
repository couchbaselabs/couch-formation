##
##

import logging
import os
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
        self.packer_vars = None
        self.tf_vars = None
        self.dev_num = None
        self.test_num = None
        self.prod_num = None
        self.app_num = None
        self.working_dir = None
        self.working_app_dir = None
        self.cb_cluster_name = None

    def set_cloud(self, cloud: str):
        self.cloud = cloud

        if self.cloud == 'aws':
            self.packer_vars = self.lc.aws_packer
            self.tf_vars = self.lc.aws_tf
        elif self.cloud == 'gcp':
            self.packer_vars = self.lc.gcp_packer
            self.tf_vars = self.lc.gcp_tf
        elif self.cloud == 'azure':
            self.packer_vars = self.lc.azure_packer
            self.tf_vars = self.lc.azure_tf
        elif self.cloud == 'vmware':
            self.packer_vars = self.lc.vmware_packer
            self.tf_vars = self.lc.vmware_tf
        else:
            raise EnvMgrError(f"unknown cloud {self.cloud}")

    def set_env(self, dev_num=None, test_num=None, prod_num=None, app_num=None):
        if dev_num:
            self.dev_num = dev_num
        elif test_num:
            self.test_num = test_num
        elif prod_num:
            self.prod_num = prod_num

        if app_num:
            self.app_num = app_num

    def get_env(self):
        return self.dev_num, self.test_num, self.prod_num, self.app_num

    def get_cb_cluster_name(self, default=None):
        inquire = ask()

        if self.dev_num:
            cluster_name = "dev{:02d}db".format(self.dev_num)
        elif self.test_num:
            cluster_name = "test{:02d}db".format(self.test_num)
        elif self.prod_num:
            cluster_name = "prod{:02d}db".format(self.prod_num)
        else:
            cluster_name = 'cbdb'
        selection = inquire.ask_text('Couchbase Cluster Name', cluster_name, default=default)
        self.cb_cluster_name = selection

        return self.cb_cluster_name

    def create_env(self, overwrite=False, create=True):
        if self.dev_num:
            dev_directory = "dev-{:02d}".format(self.dev_num)
            self.working_dir = self.tf_vars + '/' + dev_directory
        elif self.test_num:
            test_directory = "test-{:02d}".format(self.test_num)
            self.working_dir = self.tf_vars + '/' + test_directory
        elif self.prod_num:
            prod_directory = "prod-{:02d}".format(self.prod_num)
            self.working_dir = self.tf_vars + '/' + prod_directory
        else:
            raise EnvMgrError("Environment not specified.")

        if self.app_num:
            self.working_app_dir = self.working_dir + '/' + "app-{:02d}".format(self.app_num)

        if create:
            try:
                self.create_env_dir(overwrite=overwrite)
            except Exception as err:
                raise EnvMgrError(f"can not create environment structure: {err}")

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

        for file_name in copy_files:
            source = self.tf_vars + '/' + file_name
            destination = self.working_dir + '/' + file_name
            if not os.path.exists(destination) or overwrite:
                try:
                    self.logger.info("Copying %s -> %s" % (source, destination))
                    copyfile(source, destination)
                except Exception as err:
                    raise EnvMgrError(f"can not copy {source} -> {destination}: {err}")

        if self.working_app_dir:
            for file_name in app_files:
                source = self.tf_vars + '/' + file_name
                destination = self.working_app_dir + '/' + file_name
                if not os.path.exists(destination) or overwrite:
                    try:
                        self.logger.info("Copying %s -> %s" % (source, destination))
                        copyfile(source, destination)
                    except Exception as err:
                        raise EnvMgrError(f"can not copy {source} -> {destination}: {err}")
