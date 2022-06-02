##
##

import os.path
import re
from shutil import copyfile
from lib.exceptions import *
from lib.aws import aws
from lib.gcp import gcp
from lib.azure import azure
from lib.vmware import vmware
from lib.location import location
from lib.template import template
from lib.varfile import varfile
from lib.cbrelmgr import cbrelease
from lib.ssh import ssh
from lib.toolbox import toolbox
from lib.invoke import tf_run
from lib.envmgr import envmgr
from lib.clustermgr import clustermgr
from lib.netmgr import network_manager
from lib.ask import ask
from lib.tfparser import tfgen
from lib.constants import CLUSTER_CONFIG, APP_CONFIG, SGW_CONFIG, STD_CONFIG


class run_manager(object):

    def __init__(self, parameters):
        self.cloud = parameters.cloud
        self.args = parameters
        self.lc = location()
        self.env = envmgr()
        self.var_template_file = 'variables.template'
        self.var_standalone_file = 'standalone.template'
        self.variable_file_name = 'variables.tf'
        self.lc.set_cloud(self.cloud)
        self.env.set_cloud(self.cloud)
        self.env.set_env(self.args.dev, self.args.test, self.args.prod, self.args.app, self.args.sgw, all_opt=self.args.all, standalone_opt=self.args.standalone)
        self.nm = network_manager(self.args)

    # def standalone_env(self):
    #     inquire = ask()
    #     previous_tf_vars = None
    #
    #     if self.cloud == 'aws':
    #         driver = aws()
    #         driver.aws_init()
    #     elif self.cloud == 'gcp':
    #         driver = gcp()
    #         driver.gcp_init()
    #         driver.gcp_prep(select=False)
    #     elif self.cloud == 'azure':
    #         driver = azure()
    #         driver.azure_init()
    #         driver.azure_prep()
    #     elif self.cloud == 'vmware':
    #         driver = vmware()
    #         driver.vmware_init()
    #         driver.vmware_set_cluster_name(self.env.get_cb_cluster_name(select=False))
    #         self.args.static = True
    #     else:
    #         raise RunMgmtError(f"unknown cloud {self.cloud}")
    #
    #     env_text = self.env.get_env
    #     env_text = env_text.replace(':', ' ')

    def build_env(self):
        inquire = ask()
        previous_tf_vars = None
        create_app_nodes = False
        create_sgw_nodes = False

        if self.cloud == 'aws':
            driver = aws()
            driver.aws_init()
        elif self.cloud == 'gcp':
            driver = gcp()
            driver.gcp_init()
            driver.gcp_prep(select=False)
        elif self.cloud == 'azure':
            driver = azure()
            driver.azure_init()
            driver.azure_prep()
        elif self.cloud == 'vmware':
            driver = vmware()
            driver.vmware_init()
            driver.vmware_set_cluster_name(self.env.get_cb_cluster_name(select=False))
            self.args.static = True
        else:
            raise RunMgmtError(f"unknown cloud {self.cloud}")

        env_text = self.env.get_env
        env_text = env_text.replace(':', ' ')

        print(f"Operating on environment {env_text}")
        self.env.create_env(overwrite=True)

        t = template()
        v = varfile()
        c = cbrelease()
        s = ssh()
        b = toolbox()
        build_variables = []

        v.set_cloud(self.cloud)

        try:
            if self.args.standalone:
                selected_image = driver.aws_get_market_ami()
                t.do_not_reuse('aws_market_name', 'gcp_cb_image', 'azure_image_name')
            else:
                selected_image = driver.get_image()
                linux_type = selected_image['type']
                linux_release = selected_image['release']
                v.set_os_name(linux_type)
                v.set_os_ver(linux_release)
                c.set_os_name(linux_type)
                c.set_os_ver(linux_release)
                t.do_not_reuse('os_image_user', 'ami_id', 'gcp_cb_image', 'azure_image_name', 'vsphere_template')
        except Exception as err:
            raise RunMgmtError(f"can not get image for deployment: {err}")

        if self.args.standalone:
            template_file_name = self.var_standalone_file
        else:
            template_file_name = self.var_template_file

        var_file = self.env.env_dir + '/' + self.variable_file_name
        template_file = self.lc.tf_dir + '/' + template_file_name
        previous_tf_var_file = self.env.get_tf_var_file()
        if previous_tf_var_file:
            previous_tf_vars = t.read_variable_file(previous_tf_var_file)

        try:
            t.read_file(template_file)
            requested_vars = t.get_file_parameters()

            if previous_tf_vars:
                t.get_previous_values(v, previous_tf_vars, v.VARIABLES)
            pass_variables = t.process_vars(v, requested_vars, v.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(c, previous_tf_vars, c.VARIABLES)
            pass_variables = t.process_vars(c, requested_vars, c.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(s, previous_tf_vars, s.VARIABLES)
            pass_variables = t.process_vars(s, requested_vars, s.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(b, previous_tf_vars, b.VARIABLES)
            pass_variables = t.process_vars(b, requested_vars, b.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(self.nm, previous_tf_vars, self.nm.VARIABLES)
            pass_variables = t.process_vars(self.nm, requested_vars, self.nm.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(self.env, previous_tf_vars, self.env.VARIABLES)
            pass_variables = t.process_vars(self.env, requested_vars, self.env.VARIABLES)
            build_variables = build_variables + pass_variables

            if previous_tf_vars:
                t.get_previous_values(driver, previous_tf_vars, driver.VARIABLES)
            pass_variables = t.process_vars(driver, requested_vars, driver.VARIABLES)
            build_variables = build_variables + pass_variables
        except Exception as err:
            raise RunMgmtError(f"can not process template {template_file}: {err}")

        print("Writing environment variables")

        try:
            t.process_template(build_variables)
            t.write_file(var_file)
        except Exception as err:
            raise RunMgmtError(f"can not write variables {var_file}: {err}")

        cm = clustermgr(driver, self.env, self.nm, self.args)

        print("")
        if self.args.standalone:
            if inquire.ask_yn('Create node configuration', default=True):
                print("")
                cm.create_node_config(STD_CONFIG, self.env.env_dir)
        else:
            if inquire.ask_yn('Create cluster configuration', default=True):
                print("")
                cm.create_node_config(CLUSTER_CONFIG, self.env.env_dir)

        print("")
        if self.env.app_env_dir:
            destination = self.env.app_env_dir + '/' + self.variable_file_name
            copyfile(var_file, destination)
            if inquire.ask_yn('Create app configuration', default=True):
                create_app_nodes = True
                print("")
                cm.create_node_config(APP_CONFIG, self.env.app_env_dir)

        print("")
        if self.env.sgw_env_dir:
            destination = self.env.sgw_env_dir + '/' + self.variable_file_name
            copyfile(var_file, destination)
            if inquire.ask_yn('Create SGW configuration', default=True):
                create_sgw_nodes = True
                print("")
                self.create_sgw_var_file(self.env.sgw_env_dir)
                cm.create_node_config(SGW_CONFIG, self.env.sgw_env_dir)

        print("")
        if not inquire.ask_yn("Proceed with environment deployment", default=True):
            return True

        print("")
        print("Beginning environment deploy process")

        try:
            tf = tf_run(working_dir=self.env.env_dir)
            tf.init()
            tf.apply()
        except Exception as err:
            raise RunMgmtError(f"can not deploy environment: {err}")

        if create_app_nodes:
            try:
                tf = tf_run(working_dir=self.env.app_env_dir)
                tf.init()
                tf.apply()
            except Exception as err:
                raise RunMgmtError(f"can not deploy environment: {err}")

        if create_sgw_nodes:
            try:
                self.create_cluster_var_file(self.env.env_dir, self.env.sgw_env_dir)
                tf = tf_run(working_dir=self.env.sgw_env_dir)
                tf.init()
                tf.apply()
            except Exception as err:
                raise RunMgmtError(f"can not deploy environment: {err}")

        self.list_env()

    def destroy_env(self):
        inquire = ask()
        self.env.create_env(create=False)
        env_text = self.env.get_env
        env_text = env_text.replace(':', '-')

        print(f"Cloud: {self.cloud} :: Environment {env_text}")

        try:
            if inquire.ask_yn(f"Remove instances for {env_text}", default=False):
                tf = tf_run(working_dir=self.env.env_dir)
                if not tf.validate():
                    tf.init()
                tf.destroy()
        except Exception as err:
            raise RunMgmtError(f"can not destroy environment: {err}")

        for app_env in self.env.all_app_dirs():
            try:
                app_env_dir = self.env.env_dir + '/' + app_env
                if not os.path.exists(app_env_dir + '/variables.tf'):
                    print(f"Skipping incomplete environment {app_env}")
                    continue
                if inquire.ask_yn(f"Remove instances for {app_env}", default=False):
                    tf = tf_run(working_dir=app_env_dir)
                    if not tf.validate():
                        tf.init()
                    tf.destroy()
            except Exception as err:
                raise RunMgmtError(f"can not destroy environment: {err}")

    def list_env(self):
        self.env.create_env(create=False)
        env_text = self.env.get_env
        env_text = env_text.replace(':', ' ')

        print(f"Cloud: {self.cloud} :: Environment {env_text}")

        try:
            tf = tf_run(working_dir=self.env.env_dir)
            env_data = tf.output(quiet=True)
            if env_data:
                print("Couchbase cluster:")
            for item in env_data:
                print(f"{item}:")
                for n, host in enumerate(env_data[item]['value']):
                    print(f" {n+1:d}) {host}")
        except Exception as err:
            raise RunMgmtError(f"can not deploy environment: {err}")

        for app_env in self.env.all_app_dirs():
            try:
                app_env_dir = self.env.env_dir + '/' + app_env
                tf = tf_run(working_dir=app_env_dir)
                env_data = tf.output(quiet=True)
                if env_data:
                    print(f"{app_env} node(s):")
                for item in env_data:
                    print(f"{item}:")
                    for n, host in enumerate(env_data[item]['value']):
                        print(f" {n + 1:d}) {host}")
            except Exception as err:
                raise RunMgmtError(f"can not deploy environment: {err}")

    def list_all(self):
        for cloud in self.lc.cloud_list:
            print(f" => Cloud {cloud}")
            for environment in self.env.all_env_dirs(cloud):
                app_envs = []
                env_dir = self.lc.package_dir + '/' + cloud + '/terraform/' + environment
                tf = tf_run(working_dir=env_dir)
                env_data = tf.output(quiet=True)
                if env_data:
                    running = 'yes'
                else:
                    running = 'no'
                for app_env in self.env.all_app_dirs(working_dir=env_dir):
                    app_envs.append(app_env)
                    env_dir = self.lc.package_dir + '/' + cloud + '/terraform/' + environment + '/' + app_env
                    tf = tf_run(working_dir=env_dir)
                    env_data = tf.output(quiet=True)
                    if env_data:
                        app_envs.append('yes')
                    else:
                        app_envs.append('no')
                print(f"      {environment.ljust(7)} active: {running.ljust(3)}", end='')
                for item in zip(*[iter(app_envs)] * 2):
                    print(f" {item[0]} active: {item[1].ljust(3)}", end='')
                print("")

    def create_cluster_var_file(self, env_dir, out_dir):
        var_filename = out_dir + '/cb_cluster.tf'
        try:
            var_file = tfgen(var_filename)
            var_file.open_file()
            tf = tf_run(working_dir=env_dir)
            env_data = tf.output(quiet=True)
            if not env_data:
                raise RunMgmtError("cluster was not created")
            for item in env_data:
                if item == 'node-private':
                    for n, host in enumerate(env_data[item]['value']):
                        var_file.tf_variable_str(f"cb_node_{n + 1}", host)
            var_file.close_file()
        except Exception as err:
            raise RunMgmtError(f"can not create cluster var file: {err}")

    def create_sgw_var_file(self, out_dir):
        var_filename = out_dir + '/sgw_config.tf'
        try:
            cbr = cbrelease()
            sgw_version = cbr.get_sgw_version()
            var_file = tfgen(var_filename)
            var_file.open_file()
            var_file.tf_variable_str("sgw_version", sgw_version)
            var_file.close_file()
        except Exception as err:
            raise RunMgmtError(f"can not create sync gateway var file: {err}")
