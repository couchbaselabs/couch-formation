##
##

import logging
import json
from lib.util.envmgr import PathMap, PathType, ConfigFile, CatalogManager
from lib.exceptions import GCPDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
import lib.config as config
from lib.invoke import tf_run, packer_run
from lib.util.cfgmgr import ConfigMgr
from lib.util.gcp_data import DataCollect
from lib.util.common_data import ClusterCollect
from lib.hcl.gcp_vpc import GCPProvider, NetworkResource, SubnetResource, FirewallResource, VPCConfig, Resources
from lib.hcl.gcp_image import Packer, PackerElement, RequiredPlugins, GooglePlugin, GooglePluginSettings, ImageMain, Source, SourceType, NodeType, NodeElements, \
    ImageBuild, BuildConfig, BuildElements, Shell, ShellElements, GCPImageDataRecord
from lib.hcl.common import Variable, Variables, Locals, LocalVar, NodeMain, NullResource, NullResourceBlock, NullResourceBody, DependsOn, InLine, Connection, ConnectionElements, \
    RemoteExec, ForEach, Provisioner, Triggers, Output, OutputValue, Build, Entry, ResourceBlock, NodeBuild, TimeSleep, DataResource
from lib.hcl.gcp_instance import NodeConfiguration, TerraformElement, RequiredProvider, GCPInstance, GCPTerraformProvider, GCPDisk, GCPProviderBlock, ImageData


class CloudDriver(object):
    VERSION = '3.0.1'
    HOST_PREP_REPO = "couchbaselabs/couchbase-hostprep"
    DRIVER_CONFIG = "gcp.json"
    NETWORK_CONFIG = "main.tf.json"
    MAIN_CONFIG = "main.tf.json"
    IMAGE_CONFIG = "main.pkr.json"
    CONFIG_FILE = "config.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise GCPDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise GCPDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        cb_rel = CBRelease()

        gcp_zone = config.cloud_base().gcp_zone
        gcp_account_file = config.cloud_base().account_file
        gcp_project = config.cloud_base().project

        print(f"Configuring image in zone {gcp_zone}")

        os_list = [i for i in self.config.build.keys()]
        os_choice = self.ask.ask_list_basic("Select OS", os_list)

        distro_list = Entry.from_config(os_choice, self.config.build)

        distro_choice = self.ask.ask_list_dict("Select OS revision", distro_list.versions)

        distro_table = GCPImageDataRecord.from_config(distro_choice)

        release_list = cb_rel.get_cb_version(os_choice, distro_table.version)

        cb_release_choice = self.ask.ask_list_basic("Select CBS release", release_list)

        var_list = [
            ("os_linux_type", os_choice, "OS Name", "string"),
            ("gcp_account_file", gcp_account_file, "Zone name", "string"),
            ("gcp_project", gcp_project, "Zone name", "string"),
            ("gcp_zone", gcp_zone, "Zone name", "string"),
            ("cb_version", cb_release_choice, "CBS Revision", "string"),
            ("host_prep_repo", CloudDriver.HOST_PREP_REPO, "Host Prep Utility", "string"),
            ("os_image_name", distro_table.image, "Image", "string"),
            ("os_image_family", distro_table.family, "Image Owner", "string"),
            ("os_image_user", distro_table.user, "Image User", "string"),
            ("os_linux_release", distro_table.version, "OS Revision", "string"),
        ]

        packer_block = Packer.construct(
            PackerElement.construct(
                RequiredPlugins.construct(
                    GooglePlugin.construct(
                        GooglePluginSettings.construct("github.com/hashicorp/googlecompute", "1.0.16")
                        .as_dict)
                    .as_dict)
                .as_dict)
            .as_dict)

        locals_block = Locals.construct(LocalVar.build().add("timestamp", "${formatdate(\"MMDDYY-hhmm\", timestamp())}").as_dict)

        source_block = Source.construct(
            SourceType.construct(
                NodeType.construct(
                    NodeElements.construct('os_linux_type',
                                           "os_linux_release",
                                           "n2-standard-2",
                                           "gcp_zone",
                                           "gcp_project",
                                           "gcp_account_file",
                                           "os_image_name",
                                           "os_image_family",
                                           "os_image_user",
                                           "cb_version")
                    .as_dict)
                .as_key("cb-node"))
            .as_key("googlecompute"))

        build_block = ImageBuild.construct(
            BuildConfig.construct(
                BuildElements.construct(os_choice,
                                        distro_table.version,
                                        Shell.construct(
                                            ShellElements.construct([
                                                "SW_VERSION=${var.cb_version}"
                                            ],
                                                [
                                                    "echo Installing Couchbase",
                                                    "sleep 30",
                                                    "curl -sfL https://raw.githubusercontent.com/${var.host_prep_repo}/main/bin/bootstrap.sh | sudo -E bash -",
                                                    "sudo git clone https://github.com/${var.host_prep_repo} /usr/local/hostprep",
                                                    "sudo /usr/local/hostprep/bin/hostprep.sh -t couchbase -v ${var.cb_version}"
                                                ])
                                            .as_dict)
                                        .as_dict,
                                        "googlecompute",
                                        "cb-node")
                .as_dict)
            .as_dict)

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        packer_config = ImageMain.build() \
            .add(packer_block.as_dict) \
            .add(locals_block.as_dict) \
            .add(source_block.as_dict) \
            .add(build_block.as_dict) \
            .add(var_block.as_dict).as_dict

        self.path_map.map(PathType.IMAGE)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.IMAGE_CONFIG, PathType.IMAGE)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(packer_config, cfg_file_h, indent=2)
        except Exception as err:
            raise GCPDriverError(f"can not write to image config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Building {os_choice} {distro_table.version} {cb_release_choice} image in {config.cloud}")
            pr = packer_run(working_dir=cfg_file.file_path)
            pr.init(cfg_file.file_name)
            pr.build_gen(cfg_file.file_name)
        except Exception as err:
            GCPDriverError(f"can not build image: {err}")

    def list_images(self):
        image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])
        self.ask.list_dict(f"Images in cloud {config.cloud}", image_list, sort_key="date", hide_key=["link"])

    def create_nodes(self, node_type: str):
        cluster_build = False
        sync_gateway_build = False
        app_build = False
        locals_block = None
        null_resource_block = None
        swap_disk_block = None

        dc = DataCollect()
        cluster = ClusterCollect()

        dc.get_infrastructure()
        dc.get_keys()
        dc.get_image(node_type)
        dc.get_cluster_settings(node_type)
        cluster.create_cloud(node_type, dc)

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name"),
            ("region_name", dc.region, "Region name"),
            ("image", dc.generic_image if node_type == "generic" else dc.image, "Image name"),
            ("ssh_user", dc.generic_image_user if node_type == "generic" else dc.image_user, "Admin Username"),
            ("ssh_public_key", dc.public_key, "SSH public key filename"),
            ("ssh_private_key", dc.private_key, "SSH private key filename"),
            ("network", dc.network, "Network name"),
            ("gcp_project", dc.gcp_project, "GCP project"),
            ("gcp_image_project", dc.gcp_image_project if node_type == "generic" else dc.gcp_project, "Image project"),
            ("instance_type", dc.instance_type, "Instance type"),
            ("gcp_account_file", dc.gcp_account_file, "Account file"),
            ("gcp_service_account_email", dc.gcp_account_email, "Account email"),
            ("root_volume_size", str(dc.disk_size), "Volume size"),
            ("root_volume_type", dc.disk_type, "Disk type"),
            ("use_public_ip", dc.use_public_ip, "Use public or private IP for SSH"),
            ("cluster_spec", cluster.cluster_map, "Node map"),
        ]

        if node_type == "app":
            app_build = True
            path_type = PathType.APP
            path_file = CloudDriver.MAIN_CONFIG
        elif node_type == "sgw":
            path_type = PathType.SGW
            path_file = CloudDriver.MAIN_CONFIG
            sync_gateway_build = True
            cluster_data = self.list_nodes('cluster')
            cluster.create_sgw(cluster_data)
            var_list.extend(
                [
                    ("cb_node_1", cluster.cluster_node_list[0], "CBS node IP address"),
                    ("sgw_version", cluster.sgw_version, "SGW software version")
                ]
            )
        elif node_type == "generic":
            path_type = PathType.GENERIC
            path_file = CloudDriver.MAIN_CONFIG
        else:
            var_list.extend(
                [
                    ("index_memory", dc.cb_index_mem_type, "Index memory setting"),
                    ("cb_cluster_name", f"{config.env_name}-db", "Couchbase cluster name")
                ]
            )
            path_type = PathType.CLUSTER
            path_file = CloudDriver.MAIN_CONFIG
            cluster_build = True

        print(f"Configuring {self.path_map.last_mapped} nodes in region {dc.region}")

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        header_block = TerraformElement.construct(RequiredProvider.construct(GCPTerraformProvider.construct("hashicorp/google").as_dict).as_dict)

        provider_block = GCPProviderBlock.construct("gcp_account_file", "gcp_project", "region_name")

        if cluster_build:
            locals_block = Locals.construct(LocalVar.build()
                                            .add("cluster_init_name", "${var.cb_cluster_name}")
                                            .add("rally_node", "${element([for node in google_compute_instance.couchbase_nodes: node.network_interface.0.network_ip], 0)}")
                                            .add("rally_node_public", "${var.use_public_ip ? element([for node in google_compute_instance.couchbase_nodes: node.network_interface.0.access_config.0.nat_ip], 0) : null}")
                                            .as_dict)

            null_resource_block = NullResource.build().add(
                NullResourceBlock.construct(
                    NullResourceBody
                    .build()
                    .add(Connection.build()
                         .add(
                        ConnectionElements.construct(
                            "var.use_public_ip ? each.value.network_interface.0.access_config.0.nat_ip : each.value.network_interface.0.network_ip",
                            "ssh_private_key",
                            "ssh_user").as_dict)
                         .as_dict)
                    .add(DependsOn.build()
                         .add("google_compute_instance.couchbase_nodes")
                         .add("time_sleep.pause").as_dict)
                    .add(ForEach.construct("${google_compute_instance.couchbase_nodes}").as_dict)
                    .add(Provisioner.build()
                         .add(RemoteExec.build()
                              .add(InLine.build()
                                   .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node} -n ${local.cluster_init_name}")
                                   .as_dict)
                              .as_dict)
                         .as_dict)
                    .add(Triggers.build()
                         .add("cb_nodes", "${join(\",\", keys(google_compute_instance.couchbase_nodes))}")
                         .as_dict)
                    .as_dict
                )
                .as_name("couchbase-init")
            ).add(
                NullResourceBlock.construct(
                    NullResourceBody
                    .build()
                    .add(Connection.build()
                         .add(
                        ConnectionElements.construct(
                            "var.use_public_ip ? local.rally_node_public : local.rally_node",
                            "ssh_private_key",
                            "ssh_user").as_dict)
                         .as_dict)
                    .add(DependsOn.build()
                         .add("null_resource.couchbase-init").as_dict)
                    .add(Provisioner.build()
                         .add(RemoteExec.build()
                              .add(InLine.build()
                                   .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m rebalance -r ${local.rally_node}")
                                   .as_dict)
                              .as_dict)
                         .as_dict)
                    .add(Triggers.build()
                         .add("cb_nodes", "${join(\",\", keys(google_compute_instance.couchbase_nodes))}")
                         .as_dict)
                    .as_dict
                )
                .as_name("couchbase-rebalance")
            )

            inline_build = InLine.build() \
                .add("sudo /usr/local/hostprep/bin/refresh.sh") \
                .add("sudo /usr/local/hostprep/bin/configure-swap.sh -o ${each.value.node_swap} -d /dev/xvdb") \
                .add("sudo /usr/local/hostprep/bin/clusterinit.sh "
                     "-m write "
                     "-i ${self.network_interface.0.network_ip} "
                     "-e %{if var.use_public_ip}${self.network_interface.0.access_config.0.nat_ip}%{else}none%{endif} "
                     "-s ${each.value.node_services} "
                     "-o ${var.index_memory} "
                     "-g ${each.value.node_zone}") \
                .as_dict
        elif sync_gateway_build:
            inline_build = InLine.build() \
                .add("sudo /usr/local/hostprep/bin/refresh.sh") \
                .add("sudo /usr/local/hostprep/bin/hostprep.sh -t sgw -g ${var.sgw_version}") \
                .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m sgw -r ${var.cb_node_1}") \
                .as_dict
        elif app_build:
            inline_build = InLine.build() \
                .add("sudo /usr/local/hostprep/bin/refresh.sh") \
                .add("sudo /usr/local/hostprep/bin/hostprep.sh -t sdk") \
                .as_dict
        else:
            inline_build = None

        if inline_build:
            provisioner_block = Provisioner.build() \
                .add(RemoteExec.build().add(Connection.build().add(
                    ConnectionElements.construct(
                        "var.use_public_ip ? self.network_interface.0.access_config.0.nat_ip : self.network_interface.0.network_ip",
                        "ssh_private_key",
                        "ssh_user")
                    .as_dict)
                    .as_dict)
                 .add(inline_build)
                 .as_dict).as_contents
        else:
            provisioner_block = None

        output_block = Output.build().add(
            OutputValue.build()
            .add("${[for instance in google_compute_instance.couchbase_nodes: instance.network_interface.0.network_ip]}")
            .as_name("node-private")
        ).add(
            OutputValue.build()
            .add("${var.use_public_ip ? [for instance in google_compute_instance.couchbase_nodes: instance.network_interface.0.access_config.0.nat_ip] : null}")
            .as_name("node-public")
        )

        if cluster.node_swap:
            swap_disk_block = GCPDisk.construct(
                "swap_disk",
                "cluster_spec",
                "gcp_project",
                "node_ram",
                "root_volume_type",
                "node_zone"
            ).as_dict

        instance_block = GCPInstance.build().add(
            NodeBuild.construct(
                NodeConfiguration.construct(
                    "cb_image",
                    "root_volume_size",
                    "root_volume_type",
                    "cluster_spec",
                    "instance_type",
                    "ssh_user",
                    "ssh_public_key",
                    "node_subnet",
                    "gcp_project",
                    "gcp_service_account_email",
                    "node_zone",
                    provisioner_block,
                    swap_disk_block
                ).as_dict
            ).as_name("couchbase_nodes")
        )

        time_sleep_block = TimeSleep.construct("google_compute_instance", "couchbase_nodes")

        data_block = DataResource.build().add(
            ImageData.construct("cb_image", "image", "gcp_image_project").as_dict
        )

        resource_block = ResourceBlock.build()
        resource_block.add(instance_block.as_dict)
        resource_block.add(time_sleep_block.as_dict)

        main_config = NodeMain.build() \
            .add(header_block.as_dict) \
            .add(provider_block.as_dict) \
            .add(data_block.as_dict) \
            .add(resource_block.as_dict) \
            .add(output_block.as_dict) \
            .add(var_block.as_dict)

        if cluster_build:
            main_config.add(locals_block.as_dict)
            resource_block.add(null_resource_block.as_dict)

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(main_config.as_dict, cfg_file_h, indent=2)
        except Exception as err:
            raise GCPDriverError(f"can not write to main config file {cfg_file.file_name}: {err}")

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
                raise GCPDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise GCPDriverError(f"can not deploy nodes: {err}")

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
                raise GCPDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise GCPDriverError(f"can not deploy nodes: {err}")

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
            raise GCPDriverError(f"can not list nodes: {err}")

    def destroy_nodes(self, node_type: str):
        self.logger.info(f"Removing components for cloud {config.cloud} node type {node_type}")
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
            raise GCPDriverError(f"can not destroy nodes: {err}")

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
            raise GCPDriverError(f"can not clean nodes: {err}")

    def create_net(self):
        cidr_util = NetworkDriver()

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        vpc_cidr = cidr_util.get_next_network()
        subnet_list = list(cidr_util.get_next_subnet())
        region = config.cloud_base().region
        project = config.cloud_base().project
        account_file = config.cloud_base().account_file

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR"),
            ("region_name", region, "Region name"),
            ("cf_gcp_account_file", account_file, "Region name"),
            ("cf_gcp_project", project, "Region name"),
            ("cf_subnet_cidr_1", subnet_list[1], "Region name"),
        ]

        provider_block = GCPProvider.for_region("cf_gcp_account_file", "cf_gcp_project", "region_name")

        network_block = NetworkResource.construct(False, "cf_env_name")

        subnet_block = SubnetResource.construct("cf_subnet_cidr_1", "cf_env_name", "cf_vpc", "region_name")

        firewall_block = FirewallResource.build("cf_env_name", "cf_vpc", "cf_vpc_cidr")
        firewall_block.add("cf-fw-cb",
                           ["8091-8097", "9123", "9140", "11210", "11280", "11207", "18091-18097", "4984-4986"],
                           "tcp",
                           "cf_env_name",
                           "cf_vpc",
                           ["0.0.0.0/0"])
        firewall_block.add("cf-fw-ssh", ["22"], "tcp", "cf_env_name", "cf_vpc", ["0.0.0.0/0"])

        resource_block = Resources.build()
        resource_block.add(network_block.as_dict)
        resource_block.add(subnet_block.as_dict)
        resource_block.add(firewall_block.as_dict)

        output_block = Output.build()
        output_block.add(
            OutputValue.build()
            .add("${google_compute_network.cf_vpc.name}")
            .as_name("network_name")
        )
        output_block.add(
            OutputValue.build()
            .add("${google_compute_subnetwork.cf_subnet_1}")
            .as_name("cf_subnet_1")
        )

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        vpc_config = VPCConfig.build()\
            .add(provider_block.as_dict)\
            .add(resource_block.as_dict)\
            .add(output_block.as_dict)\
            .add(var_block.as_dict).as_dict

        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(vpc_config, cfg_file_h, indent=2)
        except Exception as err:
            raise GCPDriverError(f"can not write to network config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Creating VPC ...")
            tf = tf_run(working_dir=cfg_file.file_path)
            tf.init()
            if not tf.validate():
                raise GCPDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise GCPDriverError(f"can not create VPC: {err}")

    def list_net(self):
        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            vpc_data = tf.output(quiet=True)
            return vpc_data
        except Exception as err:
            raise GCPDriverError(f"can not list network: {err}")

    def destroy_net(self):
        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            if Inquire().ask_yn(f"Remove VPC for {config.env_name}", default=False):
                tf = tf_run(working_dir=cfg_file.file_path)
                if not tf.validate():
                    tf.init()
                tf.destroy()
        except Exception as err:
            raise GCPDriverError(f"can not destroy VPC: {err}")

    def clean_net(self):
        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            if not tf.validate():
                tf.init()
            resources = tf.list()
            for resource in resources.splitlines():
                self.logger.info(f"Removing resource {resource}")
                tf.remove(resource)
        except Exception as err:
            raise GCPDriverError(f"can not clean VPC: {err}")
