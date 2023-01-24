##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from typing import Iterable
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.util.cfgmgr import ConfigMgr
from lib.exceptions import CapellaDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
from lib.util.capella_data import DataCollect
from lib.util.common_data import ClusterCollect
from lib.invoke import tf_run
import lib.config as config
from lib.hcl.common import Variable, Variables, Locals, LocalVar, NodeMain, NullResource, NullResourceBlock, NullResourceBody, DependsOn, InLine, Connection, ConnectionElements, \
    RemoteExec, ForEach, Provisioner, Triggers, Output, OutputValue, Build, Entry, ResourceBlock, NodeBuild, TimeSleep, DataResource
from lib.hcl.capella_instance import CapellaCluster, CapellaProject, CapellaServices, CapellaClusterPlace, CapellaHostedCluster, CapellaServerSpec, CapellaSupportPackage, \
    CapellaProviderBlock, CapellaTerraformProvider, CapellaAWSStorage, CapellaGCPStorage, NodeConfiguration, TerraformElement, RequiredProvider


class CloudDriver(object):
    VERSION = '3.0.0'
    DRIVER_CONFIG = "capella.json"
    NETWORK_CONFIG = "main.tf.json"
    MAIN_CONFIG = "main.tf.json"
    CONFIG_FILE = "config.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise CapellaDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise CapellaDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        pass

    def create_nodes(self, node_type: str):
        dc = DataCollect()
        cluster = ClusterCollect()

        dc.get_infrastructure()
        cluster.create_capella(dc)

        if node_type == "app":
            print("Node type not available with Capella")
            return
        elif node_type == "sgw":
            print("Not implemented")
            return
        elif node_type == "generic":
            print("Node type not available with Capella")
            return
        else:
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG
            cluster_build = True

            print(f"Configuring {self.path_map.last_mapped} nodes in region {dc.region}")

            header_block = TerraformElement.construct(RequiredProvider.construct(CapellaTerraformProvider.construct("couchbasecloud/couchbasecapella", "0.2.2").as_dict).as_dict)

            provider_block = CapellaProviderBlock.construct()

            project_block = CapellaProject.construct("capella_project", dc.project)

            place_block = CapellaClusterPlace.build().add(
                CapellaHostedCluster.build().add(
                    dc.network,
                    dc.provider,
                    dc.region
                ).as_dict,
                dc.single_az
            )

            server_block = CapellaServerSpec.build()
            for n, server in enumerate(cluster.cluster_map.get('server_groups')):
                if dc.provider == "aws":
                    storage_block = CapellaAWSStorage.build().add(
                        server['root_volume_iops'],
                        server['root_volume_size'],
                        server['root_volume_type']
                    )
                else:
                    storage_block = CapellaGCPStorage.build().add(
                        server['root_volume_size'],
                        server['root_volume_type']
                    )
                server_block.add(
                    server['compute'],
                    server['services'],
                    server['size'],
                    storage_block.as_dict
                )

            instance_block = CapellaCluster.build().add(
                NodeBuild.construct(
                    NodeConfiguration.construct(
                        dc.cluster_name,
                        place_block.as_dict,
                        dc.project,
                        server_block.as_dict,
                        CapellaSupportPackage.build().add(dc.support_package).as_dict
                    ).as_dict
                ).as_name("capella_cluster")
            )

            resource_block = ResourceBlock.build()
            resource_block.add(instance_block.as_dict)
            # resource_block.add(project_block.as_dict)

            output_block = Output.build().add(
                OutputValue.build()
                .add("${couchbasecapella_hosted_cluster.capella_cluster.id}")
                .as_name("cluster-id")
            )

            main_config = NodeMain.build() \
                .add(header_block.as_dict) \
                .add(provider_block.as_dict) \
                .add(resource_block.as_dict) \
                .add(output_block.as_dict)

            self.path_map.map(path_type)
            cfg_file: ConfigFile
            cfg_file = self.path_map.use(path_file, path_type)
            try:
                with open(cfg_file.file_name, 'w') as cfg_file_h:
                    json.dump(main_config.as_dict, cfg_file_h, indent=2)
            except Exception as err:
                raise CapellaDriverError(f"can not write to main config file {cfg_file.file_name}: {err}")

            print("")
            if not Inquire().ask_yn(f"Proceed with deployment for {self.path_map.last_mapped} nodes for {config.env_name}", default=True):
                return
            print("")

            try:
                print("")
                print(f"Deploying nodes ...")
                tf = tf_run(working_dir=cfg_file.file_path)
                tf.init()
                if not tf.validate():
                    raise CapellaDriverError("Environment is not configured properly, please check the log and try again.")
                tf.apply()
            except Exception as err:
                raise CapellaDriverError(f"can not deploy nodes: {err}")

            self.show_nodes(node_type)

    def deploy_nodes(self, node_type: str):
        if node_type == "app":
            path_type = PathType.APP
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "sgw":
            path_type = PathType.SGW
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "generic":
            path_type = PathType.GENERIC
            path_file = CloudDriver.MAIN_CONFIG
        else:
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)

        try:
            print("")
            print(f"Deploying nodes ...")
            tf = tf_run(working_dir=cfg_file.file_path)
            tf.init()
            if not tf.validate():
                raise CapellaDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise CapellaDriverError(f"can not deploy nodes: {err}")

        self.show_nodes(node_type)

    def show_nodes(self, node_type: str):
        print(f"Cloud: {config.cloud} :: Environment {config.env_name}")
        env_data = self.list_nodes(node_type)
        for item in env_data:
            print(f"  [{item}]")
            if type(env_data[item]['value']) == list:
                for n, host in enumerate(env_data[item]['value']):
                    print(f"    {n + 1:d}) {host}")
            else:
                print(f"    {env_data[item]['value']}")

    def list_nodes(self, node_type: str):
        if node_type == "app":
            path_type = PathType.APP
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "sgw":
            path_type = PathType.SGW
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "generic":
            path_type = PathType.GENERIC
            path_file = CloudDriver.MAIN_CONFIG
        else:
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)
        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            node_data = tf.output(quiet=True)
            return node_data
        except Exception as err:
            raise CapellaDriverError(f"can not list nodes: {err}")

    def destroy_nodes(self, node_type: str):
        if node_type == "app":
            path_type = PathType.APP
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "sgw":
            path_type = PathType.SGW
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "generic":
            path_type = PathType.GENERIC
            path_file = CloudDriver.MAIN_CONFIG
        else:
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)

        try:
            if Inquire().ask_yn(f"Remove {self.path_map.last_mapped} nodes for {config.env_name}", default=False):
                tf = tf_run(working_dir=cfg_file.file_path)
                if not tf.validate():
                    tf.init()
                tf.destroy()
        except Exception as err:
            raise CapellaDriverError(f"can not destroy nodes: {err}")

    def clean_nodes(self, node_type: str):
        if node_type == "app":
            path_type = PathType.APP
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "sgw":
            path_type = PathType.SGW
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "generic":
            path_type = PathType.GENERIC
            path_file = CloudDriver.MAIN_CONFIG
        else:
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)

        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            if not tf.validate():
                tf.init()
            resources = tf.list()
            for resource in resources.splitlines():
                self.logger.info(f"Removing resource {resource}")
                tf.remove(resource)
        except Exception as err:
            raise CapellaDriverError(f"can not clean nodes: {err}")

    def create_net(self):
        pass
