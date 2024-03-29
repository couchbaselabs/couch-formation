##
##

import logging
import json
import os
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.exceptions import AzureDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
import lib.config as config
from lib.invoke import tf_run, packer_run
from lib.util.cfgmgr import ConfigMgr
from lib.util.azure_data import DataCollect
from lib.util.common_data import ClusterCollect
from lib.hcl.azure_vpc import AzureProvider, RGResource, Resources, VPCConfig, VNetResource, NSGResource, NSGEntry, NSGElements
from lib.hcl.azure_image import Packer, PackerElement, RequiredPlugins, AzurePlugin, AzurePluginSettings, ImageMain, Source, SourceType, NodeType, NodeElements, \
    ImageBuild, BuildConfig, BuildElements, Shell, ShellElements, AzureImageDataRecord
from lib.hcl.common import Variable, Variables, Locals, LocalVar, NodeMain, NullResource, NullResourceBlock, NullResourceBody, DependsOn, InLine, Connection, ConnectionElements, \
    RemoteExec, ForEach, Provisioner, Triggers, Output, OutputValue, Build, Entry, ResourceBlock, NodeBuild, TimeSleep, DataResource, ResourceBuild
from lib.hcl.azure_instance import NodeConfiguration, TerraformElement, RequiredProvider, AzureInstance, AzureTerraformProvider, AzureProviderBlock, NICConfiguration, \
    NSGData, NICNSGConfiguration, AzureNetworkInterfaceNSG, AzureNetworkInterface, PublicIPConfiguration, DiskConfiguration, \
    SubnetData, AzureManagedDisk, AzureDiskAttachment, AttachedDiskConfiguration, ImageData, AzurePublicIP, SourceImageReference


class CloudDriver(object):
    VERSION = '3.0.1'
    HOST_PREP_REPO = "couchbaselabs/couchbase-hostprep"
    DRIVER_CONFIG = "azure.json"
    NETWORK_CONFIG = "main.tf.json"
    MAIN_CONFIG = "main.tf.json"
    IMAGE_CONFIG = "main.pkr.json"
    CONFIG_FILE = "config.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise AzureDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise AzureDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        cb_rel = CBRelease()

        azure_location = config.cloud_base().region

        if not azure_location:
            location_list = config.cloud_base().list_locations()
            result = Inquire().ask_list_dict('Azure Location', location_list)
            azure_location = result['name']

        os.environ['AZURE_LOCATION'] = azure_location

        azure_image_rg_name = f"cf-image-{azure_location}-rg"
        azure_rg = config.cloud_base().create_rg(
            azure_image_rg_name,
            azure_location,
            {
                "type": "couch-formation-image"
            }
        )
        if not azure_rg.get('name'):
            raise AzureDriverError(f"resource group creation failed: {azure_rg}")
        azure_resource_group = azure_rg['name']

        os.environ['AZURE_RESOURCE_GROUP'] = azure_resource_group

        print(f"Configuring image in location {azure_location}")

        os_list = [i for i in self.config.build.keys()]
        os_choice = self.ask.ask_list_basic("Select OS", os_list)

        distro_list = Entry.from_config(os_choice, self.config.build)

        distro_choice = self.ask.ask_list_dict("Select OS revision", distro_list.versions)

        distro_table = AzureImageDataRecord.from_config(distro_choice)

        release_list = cb_rel.get_cb_version(os_choice, distro_table.version)

        cb_release_choice = self.ask.ask_list_basic("Select CBS release", release_list)

        var_list = [
            ("os_linux_type", os_choice, "OS Name", "string"),
            ("os_linux_release", distro_table.version, "Zone name", "string"),
            ("azure_location", azure_location, "Zone name", "string"),
            ("cb_version", cb_release_choice, "CBS Revision", "string"),
            ("host_prep_repo", CloudDriver.HOST_PREP_REPO, "Host Prep Utility", "string"),
            ("os_image_offer", distro_table.offer, "Image", "string"),
            ("os_image_publisher", distro_table.publisher, "Image Owner", "string"),
            ("os_image_sku", distro_table.sku, "Image User", "string"),
            ("azure_resource_group", azure_resource_group, "OS Revision", "string"),
        ]

        packer_block = Packer.construct(
            PackerElement.construct(
                RequiredPlugins.construct(
                    AzurePlugin.construct(
                        AzurePluginSettings.construct("github.com/hashicorp/azure", "1.3.1")
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
                                           "Standard_DS2_v2",
                                           "azure_location",
                                           "azure_resource_group",
                                           "Linux",
                                           "os_image_offer",
                                           "os_image_publisher",
                                           "os_image_sku",
                                           "cb_version")
                    .as_dict)
                .as_key("cb-node"))
            .as_key("azure-arm"))

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
                                        "azure-arm",
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
            raise AzureDriverError(f"can not write to image config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Building {os_choice} {distro_table.version} {cb_release_choice} image in {config.cloud}")
            pr = packer_run(working_dir=cfg_file.file_path)
            pr.init(cfg_file.file_name)
            pr.build_gen(cfg_file.file_name)
        except Exception as err:
            AzureDriverError(f"can not build image: {err}")

    def list_images(self):
        azure_location = config.cloud_base().region
        if not azure_location:
            location_list = config.cloud_base().list_locations()
            result = Inquire().ask_list_dict('Azure Location', location_list)
            azure_location = result['name']
            os.environ['AZURE_LOCATION'] = azure_location
        image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])
        self.ask.list_dict(f"Images in cloud {config.cloud}", image_list, sort_key="name", hide_key=['id'])

    def create_nodes(self, node_type: str):
        cluster_build = False
        sync_gateway_build = False
        app_build = False
        generic_build = False
        locals_block = None
        null_resource_block = None
        swap_disk_block = None
        swap_disk_block_attach = None

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
            ("image", dc.image, "Image name"),
            ("image_publisher", dc.image_publisher, "Image Publisher"),
            ("image_offer", dc.image_offer, "Image Offer"),
            ("image_sku", dc.image_sku, "Image SKU"),
            ("ssh_user", dc.generic_image_user if node_type == "generic" else dc.image_user, "Admin Username"),
            ("ssh_public_key", dc.public_key, "SSH public key filename"),
            ("ssh_private_key", dc.private_key, "SSH private key filename"),
            ("network", dc.network, "Network name"),
            ("azure_resource_group", dc.azure_resource_group, "Security group"),
            ("image_resource_group", dc.azure_image_rg, "Image security group"),
            ("instance_type", dc.instance_type, "Instance type"),
            ("azure_nsg", dc.azure_nsg, "Account file"),
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
            generic_build = True
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

        header_block = TerraformElement.construct(RequiredProvider.construct(AzureTerraformProvider.construct("hashicorp/azurerm").as_dict).as_dict)

        provider_block = AzureProviderBlock.construct()

        if cluster_build:
            locals_block = Locals.construct(LocalVar.build()
                                            .add("cluster_init_name", "${var.cb_cluster_name}")
                                            .add("rally_node", "${element([for node in azurerm_linux_virtual_machine.couchbase_nodes: node.private_ip_address], 0)}")
                                            .add("rally_node_public",
                                                 "${element([for node in azurerm_linux_virtual_machine.couchbase_nodes: node.public_ip_address], 0)}")
                                            .as_dict)

            null_resource_block = NullResource.build().add(
                NullResourceBlock.construct(
                    NullResourceBody
                    .build()
                    .add(Connection.build()
                         .add(
                        ConnectionElements.construct(
                            "var.use_public_ip ? each.value.public_ip_address : each.value.private_ip_address",
                            "ssh_private_key",
                            "ssh_user").as_dict)
                         .as_dict)
                    .add(DependsOn.build()
                         .add("azurerm_linux_virtual_machine.couchbase_nodes")
                         .add("time_sleep.pause").as_dict)
                    .add(ForEach.construct("${azurerm_linux_virtual_machine.couchbase_nodes}").as_dict)
                    .add(Provisioner.build()
                         .add(RemoteExec.build()
                              .add(InLine.build()
                                   .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node} -n ${local.cluster_init_name}")
                                   .as_dict)
                              .as_dict)
                         .as_dict)
                    .add(Triggers.build()
                         .add("cb_nodes", "${join(\",\", keys(azurerm_linux_virtual_machine.couchbase_nodes))}")
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
                         .add("cb_nodes", "${join(\",\", keys(azurerm_linux_virtual_machine.couchbase_nodes))}")
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
                     "-i ${self.private_ip_address} "
                     "-e %{if var.use_public_ip}${self.public_ip_address}%{else}none%{endif} "
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
            provisioner_block = Provisioner.build()\
                    .add(RemoteExec.build().add(Connection.build().add(
                        ConnectionElements.construct(
                            "var.use_public_ip ? self.public_ip_address : self.private_ip_address",
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
            .add("${[for instance in azurerm_linux_virtual_machine.couchbase_nodes: instance.private_ip_address]}")
            .as_name("node-private")
        ).add(
            OutputValue.build()
            .add("${var.use_public_ip ? [for instance in azurerm_linux_virtual_machine.couchbase_nodes: instance.public_ip_address] : null}")
            .as_name("node-public")
        )

        time_sleep_block = TimeSleep.construct("azurerm_linux_virtual_machine", "couchbase_nodes")

        data_block = DataResource.build().add(
            NSGData.construct("cluster_nsg", "azure_nsg", "azure_resource_group").as_dict
        ).add(
            SubnetData.construct("cb_subnet", "cluster_spec", "node_subnet", "azure_resource_group", "network").as_dict
        )

        if generic_build:
            source_image_id = None
            source_image_reference = SourceImageReference.construct(
                "image_offer",
                "image_publisher",
                "image_sku"
            ).as_dict
        else:
            source_image_id = "${data.azurerm_image.cb_image.id}"
            source_image_reference = None
            data_block.add(
                ImageData.construct("cb_image", "image", "image_resource_group").as_dict
            )

        if cluster.node_swap:
            swap_disk_block = AzureManagedDisk.build().add(
                ResourceBuild.construct(
                    DiskConfiguration.construct(
                        "node_ram",
                        "cluster_spec",
                        "region_name",
                        "azure_resource_group",
                        "root_volume_type",
                        "node_zone").as_dict
                ).as_name("swap_disk")
            )
            swap_disk_block_attach = AzureDiskAttachment.build().add(
                ResourceBuild.construct(
                    AttachedDiskConfiguration.construct(
                        "cluster_spec",
                        "swap_disk",
                        "couchbase_nodes"
                    ).as_dict
                ).as_name("swap_disk")
            )

        instance_block = AzureInstance.build().add(
            NodeBuild.construct(
                NodeConfiguration.construct(
                    "root_volume_size",
                    "root_volume_type",
                    "cluster_spec",
                    "instance_type",
                    "ssh_user",
                    "ssh_public_key",
                    "region_name",
                    "azure_resource_group",
                    "node_nic",
                    "node_zone",
                    provisioner_block,
                    source_image_id,
                    source_image_reference
                ).as_dict
            ).as_name("couchbase_nodes")
        )

        network_block = AzureNetworkInterface.build().add(
            ResourceBuild.construct(
                NICConfiguration.construct(
                    "cluster_spec",
                    "node_external",
                    "cb_subnet",
                    "region_name",
                    "azure_resource_group"
                ).as_dict
            ).as_name("node_nic")
        )

        network_attach_block = AzureNetworkInterfaceNSG.build().add(
            ResourceBuild.construct(
                NICNSGConfiguration.construct(
                    "cluster_spec",
                    "node_nic",
                    "cluster_nsg"
                ).as_dict
            ).as_name("node_nsg")
        )

        public_ip_block = AzurePublicIP.build().add(
            ResourceBuild.construct(
                PublicIPConfiguration.construct(
                    "cluster_spec",
                    "use_public_ip",
                    "region_name",
                    "azure_resource_group",
                    "node_zone"
                ).as_dict
            ).as_name("node_external")
        )

        resource_block = ResourceBlock.build()
        resource_block.add(instance_block.as_dict)
        resource_block.add(network_block.as_dict)
        resource_block.add(network_attach_block.as_dict)
        resource_block.add(public_ip_block.as_dict)
        resource_block.add(time_sleep_block.as_dict)

        if cluster_build:
            resource_block.add(null_resource_block.as_dict)

        if cluster.node_swap:
            resource_block.add(swap_disk_block.as_dict)
            resource_block.add(swap_disk_block_attach.as_dict)

        main_config = NodeMain.build() \
            .add(header_block.as_dict) \
            .add(provider_block.as_dict) \
            .add(data_block.as_dict) \
            .add(resource_block.as_dict) \
            .add(output_block.as_dict) \
            .add(var_block.as_dict)

        if cluster_build:
            main_config.add(locals_block.as_dict)

        self.path_map.map(path_type)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(path_file, path_type)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(main_config.as_dict, cfg_file_h, indent=2)
        except Exception as err:
            raise AzureDriverError(f"can not write to main config file {cfg_file.file_name}: {err}")

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
                raise AzureDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise AzureDriverError(f"can not deploy nodes: {err}")

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
                raise AzureDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise AzureDriverError(f"can not deploy nodes: {err}")

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
            raise AzureDriverError(f"can not list nodes: {err}")

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
            raise AzureDriverError(f"can not destroy nodes: {err}")

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
            raise AzureDriverError(f"can not clean nodes: {err}")

    def create_net(self):
        cidr_util = NetworkDriver()

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        vpc_cidr = cidr_util.get_next_network()
        subnet_list = list(cidr_util.get_next_subnet())
        region = config.cloud_base().region

        if not region:
            location_list = config.cloud_base().list_locations()
            result = Inquire().ask_list_dict('Azure Location', location_list)
            region = result['name']
            os.environ['AZURE_LOCATION'] = region

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name", "string"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR", "string"),
            ("region_name", region, "Region name", "string"),
            ("cf_subnet_cidr_1", subnet_list[1], "Subnet CIDR", "string"),
        ]

        provider_block = AzureProvider.for_region()

        rg_block = RGResource.construct("region_name", "cf_env_name")

        vnet_block = VNetResource.construct("cf_vpc_cidr", "cf_rg", "cf_env_name", "cf_subnet_cidr_1", "cf_nsg")

        nsg_block = NSGResource.construct(
            NSGEntry.construct(
                NSGElements.construct("cf_rg", "cf_env_name")
                .add("AllowSSH", ["22"], 100)
                .add("AllowCB", ["8091-8097", "9123", "9140", "11210", "11280", "11207", "18091-18097", "4984-4986"], 101)
                .as_dict)
            .as_dict)

        resource_block = Resources.build()
        resource_block.add(rg_block.as_dict)
        resource_block.add(vnet_block.as_dict)
        resource_block.add(nsg_block.as_dict)

        output_block = Output.build()
        output_block.add(
            OutputValue.build()
            .add("${azurerm_virtual_network.cf_vpc.name}")
            .as_name("network_name")
        )
        output_block.add(
            OutputValue.build()
            .add("${azurerm_resource_group.cf_rg.name}")
            .as_name("resource_group")
        )

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        vpc_config = VPCConfig.build() \
            .add(provider_block.as_dict) \
            .add(resource_block.as_dict) \
            .add(output_block.as_dict) \
            .add(var_block.as_dict).as_dict

        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(vpc_config, cfg_file_h, indent=2)
        except Exception as err:
            raise AzureDriverError(f"can not write to network config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Creating VPC ...")
            tf = tf_run(working_dir=cfg_file.file_path)
            tf.init()
            if not tf.validate():
                raise AzureDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise AzureDriverError(f"can not create VPC: {err}")

    def list_net(self):
        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            vpc_data = tf.output(quiet=True)
            return vpc_data
        except Exception as err:
            raise AzureDriverError(f"can not list VPC: {err}")

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
            raise AzureDriverError(f"can not destroy VPC: {err}")

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
            raise AzureDriverError(f"can not clean VPC: {err}")
