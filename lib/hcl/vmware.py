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

    def create_nodes(self):
        pass

    def create_net(self):
        pass
