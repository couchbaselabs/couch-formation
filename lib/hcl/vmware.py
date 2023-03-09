##
##

import logging
import json
import os
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.exceptions import VMwareDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
import lib.config as config
from lib.invoke import tf_run, packer_run
from lib.util.cfgmgr import ConfigMgr
from lib.util.vmware_data import DataCollect
from lib.util.filemgr import FileManager
from lib.util.common_data import ClusterCollect
from lib.util.timezone import TimeZone
from lib.hcl.common import Variable, Variables, Locals, LocalVar, NodeMain, NullResource, NullResourceBlock, NullResourceBody, DependsOn, InLine, Connection, ConnectionElements, \
    RemoteExec, ForEach, Provisioner, Triggers, Output, OutputValue, Build, Entry, ResourceBlock, NodeBuild, TimeSleep, DataResource, ResourceBuild
from lib.hcl.vmware_image import VMWareImageDataRecord, VMWarePlugin, VMWarePluginSettings, ImageMain, ImageBuild, Packer, PackerElement, RequiredPlugins, NodeElements, NodeType, \
    SourceType, BuildConfig, BuildElements, Shell, ShellElements, Source


class CloudDriver(object):
    VERSION = '3.0.0'
    HOST_PREP_REPO = "couchbaselabs/couchbase-hostprep"
    DRIVER_CONFIG = "vmware.json"
    NETWORK_CONFIG = "main.tf.json"
    MAIN_CONFIG = "main.tf.json"
    IMAGE_CONFIG = "main.pkr.json"
    CONFIG_FILE = "config.json"
    UBUNTU_BOOT_FILE = "user-data-ubuntu.pkrtpl.hcl"
    REDHAT_BOOT_FILE = "ks-cfg.pkrtpl.hcl"
    METADATA_BOOT_FILE = "meta-data"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise VMwareDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise VMwareDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        cb_rel = CBRelease()
        dc = DataCollect()

        dc.get_infrastructure()
        dc.get_build_password()
        dc.get_keys()

        print(f"Configuring vmware image")

        os_list = [i for i in self.config.build.keys()]
        os_choice = self.ask.ask_list_basic("Select OS", os_list)

        distro_list = Entry.from_config(os_choice, self.config.build)

        distro_choice = self.ask.ask_list_dict("Select OS revision", distro_list.versions)

        distro_table = VMWareImageDataRecord.from_config(distro_choice)

        release_list = cb_rel.get_cb_version(os_choice, distro_table.version)

        cb_release_choice = self.ask.ask_list_basic("Select CBS release", release_list)
        cb_rel_string = ''.join(cb_release_choice.replace('-', '.').split('.')[:-2])

        var_list = [
            ("os_linux_type", os_choice, "OS Name", "string"),
            ("vsphere_cluster", dc.vmware_cluster, "Zone name", "string"),
            ("vsphere_datacenter", dc.vmware_datacenter, "Zone name", "string"),
            ("vsphere_datastore", dc.vmware_datastore, "Zone name", "string"),
            ("cb_version", cb_release_choice, "CBS Revision", "string"),
            ("host_prep_repo", CloudDriver.HOST_PREP_REPO, "Host Prep Utility", "string"),
            ("vsphere_folder", dc.vmware_template_folder, "Host Prep Utility", "string"),
            ("vm_guest_os_type", distro_table.type, "Host Prep Utility", "string"),
            ("os_iso_checksum", distro_table.checksum, "Image", "string"),
            ("os_image_name", distro_table.image, "Image Owner", "string"),
            ("vsphere_network", dc.vmware_network, "Image User", "string"),
            ("vsphere_password", dc.vmware_password, "OS Revision", "string"),
            ("build_password", dc.vmware_build_password, "OS Revision", "string"),
            ("build_password_encrypted", dc.vmware_build_pwd_encrypted, "OS Revision", "string"),
            ("os_image_user", distro_table.user, "OS Revision", "string"),
            ("vm_disk_size", "100000", "OS Revision", "string"),
            ("vm_guest_os_language", "en_US", "OS Revision", "string"),
            ("vm_guest_os_keyboard", "us", "OS Revision", "string"),
            ("os_timezone", TimeZone().get_timezone(), "OS Revision", "string"),
            ("ssh_public_key", dc.public_key_data, "OS Revision", "string"),
            ("os_sw_url", distro_table.sw_url, "OS Revision", "string"),
            ("vsphere_username", dc.vmware_username, "OS Revision", "string"),
            ("vsphere_hostname", dc.vmware_hostname, "OS Revision", "string"),
            ("os_linux_release", distro_table.version, "OS Revision", "string"),
        ]

        if os_choice == "ubuntu":
            boot_command = [
                "\u003center\u003e\u003center\u003e\u003cf6\u003e\u003cesc\u003e\u003cwait\u003e ",
                "autoinstall ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
                "\u003center\u003e"
            ]
            http_content = {
                "/meta-data": "${file(\"meta-data\")}",
                "/user-data": "${templatefile(\"user-data-ubuntu.pkrtpl.hcl\", { build_username = var.os_image_user, build_password_encrypted = var.build_password_encrypted, vm_guest_os_language = var.vm_guest_os_language, vm_guest_os_keyboard = var.vm_guest_os_keyboard, vm_guest_os_timezone = var.os_timezone, build_key = var.ssh_public_key, sw_url = var.os_sw_url })}"
            }
            boot_files = [CloudDriver.UBUNTU_BOOT_FILE, CloudDriver.METADATA_BOOT_FILE]
        else:
            boot_command = [
                "\u003cup\u003e\u003cwait\u003e\u003ctab\u003e\u003cwait\u003e ",
                " inst.text ",
                "inst.ks=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ks.cfg ",
                "\u003center\u003e\u003cwait\u003e"
            ]
            http_content = {
                "/ks.cfg": "${templatefile(\"ks-cfg.pkrtpl.hcl\", { build_username = var.os_image_user, build_password_encrypted = var.build_password_encrypted, vm_guest_os_language = var.vm_guest_os_language, vm_guest_os_keyboard = var.vm_guest_os_keyboard, vm_guest_os_timezone = var.os_timezone, build_key = var.ssh_public_key, sw_url = var.os_sw_url })}"
            }
            boot_files = [CloudDriver.REDHAT_BOOT_FILE]

        packer_block = Packer.construct(
            PackerElement.construct(
                RequiredPlugins.construct(
                    VMWarePlugin.construct(
                        VMWarePluginSettings.construct("github.com/hashicorp/vmware", "1.0.3")
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
                                           boot_command,
                                           http_content,
                                           "vsphere_cluster",
                                           "vsphere_datacenter",
                                           "vsphere_datastore",
                                           "vsphere_folder",
                                           "vsphere_network",
                                           "vsphere_username",
                                           "vsphere_password",
                                           "vsphere_hostname",
                                           "os_image_name",
                                           "os_image_user",
                                           "os_iso_checksum",
                                           "build_password",
                                           "vm_disk_size",
                                           "vm_guest_os_type",
                                           cb_rel_string)
                    .as_dict)
                .as_key("cb-node"))
            .as_key("vsphere-iso"))

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
                                        "vsphere-iso",
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
            for boot_file in boot_files:
                FileManager().copy_config_file(boot_file, cfg_file.file_path)
        except Exception as err:
            raise VMwareDriverError(f"can not write image configuration: {err}")

        try:
            print("")
            print(f"Building {os_choice} {distro_table.version} {cb_release_choice} image in {config.cloud}")
            pr = packer_run(working_dir=cfg_file.file_path)
            pr.init(cfg_file.file_name)
            pr.build_gen(cfg_file.file_name)
        except Exception as err:
            VMwareDriverError(f"can not build image: {err}")

    def create_nodes(self, node_type: str):
        cluster_build = False
        sync_gateway_build = False
        locals_block = None
        null_resource_block = None
        swap_disk_block = None
        swap_disk_block_attach = None

        dc = DataCollect()
        cluster = ClusterCollect()

        dc.get_infrastructure()
        dc.get_keys()
        dc.get_domain()
        dc.get_image()
        dc.get_cluster_settings()
        dc.get_node_settings()
        print(dc.subnet_list)
        cluster.create_cloud(node_type, dc)

        var_list = [
            ("vsphere_cluster", dc.vmware_cluster, "Zone name", "string"),
            ("vsphere_datacenter", dc.vmware_datacenter, "Zone name", "string"),
            ("vsphere_datastore", dc.vmware_datastore, "Zone name", "string"),
            ("host_prep_repo", CloudDriver.HOST_PREP_REPO, "Host Prep Utility", "string"),
            ("vsphere_folder", config.env_name, "Host Prep Utility", "string"),
            ("vm_cpu_cores", dc.vm_cpu_cores, "Host Prep Utility", "string"),
            ("vm_mem_size", dc.vm_mem_size, "Image", "string"),
            ("vsphere_template", dc.vmware_template, "Image Owner", "string"),
            ("vsphere_network", dc.vmware_network, "Image User", "string"),
            ("vsphere_password", dc.vmware_password, "OS Revision", "string"),
            ("domain_name", dc.domain_name, "OS Revision", "string"),
            ("dns_domain_list", [dc.domain_name], "OS Revision", "list"),
            ("dns_server_list", dc.dns_server_list, "OS Revision", "list"),
            ("os_image_user", dc.image_user, "OS Revision", "string"),
            ("ssh_private_key", dc.private_key, "OS Revision", "string"),
            ("vsphere_username", dc.vmware_username, "OS Revision", "string"),
            ("vsphere_hostname", dc.vmware_hostname, "OS Revision", "string"),
            ("cb_cluster_name", config.env_name, "OS Revision", "string"),
        ]

        if node_type == "app":
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

        print(f"Configuring {self.path_map.last_mapped} nodes in cluster {dc.vmware_cluster}")

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
        else:
            inline_build = InLine.build() \
                .add("sudo /usr/local/hostprep/bin/refresh.sh") \
                .add("sudo /usr/local/hostprep/bin/hostprep.sh -t sdk") \
                .as_dict

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

        # data_block = DataResource.build().add(
        #     ImageData.construct("cb_image", "image", "image_resource_group").as_dict
        # ).add(
        #     NSGData.construct("cluster_nsg", "azure_nsg", "azure_resource_group").as_dict
        # ).add(
        #     SubnetData.construct("cb_subnet", "cluster_spec", "node_subnet", "azure_resource_group", "network").as_dict
        # )

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
                raise VMwareDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise VMwareDriverError(f"can not deploy nodes: {err}")

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
            raise VMwareDriverError(f"can not list nodes: {err}")

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
            raise VMwareDriverError(f"can not destroy nodes: {err}")

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
            raise VMwareDriverError(f"can not clean nodes: {err}")

    def create_net(self):
        pass
