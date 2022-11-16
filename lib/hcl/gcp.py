##
##

import logging
import attr
import json
from attr.validators import instance_of as io
from typing import Iterable
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.exceptions import GCPDriverError
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
import lib.config as config
from lib.invoke import tf_run
from lib.hcl.gcp_vpc import GCPProvider, NetworkResource, SubnetResource, FirewallResource, Variables, Variable, VPCConfig, Resources
from lib.hcl.gcp_image import Packer, PackerElement, RequiredPlugins, GooglePlugin, GooglePluginSettings, ImageMain, Locals, LocalVar, Source, SourceType, NodeType, NodeElements, \
    ImageBuild, BuildConfig, BuildElements, Shell, ShellElements


@attr.s
class Build(object):
    build = attr.ib(validator=io(dict))

    @classmethod
    def from_config(cls, json_data: dict):
        return cls(
            json_data.get("build"),
            )


@attr.s
class Entry(object):
    versions = attr.ib(validator=io(Iterable))

    @classmethod
    def from_config(cls, distro: str, json_data: dict):
        return cls(
            json_data.get(distro),
            )


@attr.s
class Record(object):
    version = attr.ib(validator=io(str))
    image = attr.ib(validator=io(str))
    family = attr.ib(validator=io(str))
    user = attr.ib(validator=io(str))
    vars = attr.ib(validator=io(str))
    hcl = attr.ib(validator=io(str))

    @classmethod
    def from_config(cls, json_data):
        return cls(
            json_data.get("version"),
            json_data.get("image"),
            json_data.get("family"),
            json_data.get("user"),
            json_data.get("vars"),
            json_data.get("hcl"),
            )


class CloudDriver(object):
    VERSION = '3.0.0'
    HOST_PREP_REPO = "couchbaselabs/couchbase-hostprep"
    DRIVER_CONFIG = "gcp.json"
    NETWORK_CONFIG = "main.tf.json"
    IMAGE_CONFIG = "main.pkr.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise GCPDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)

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

        distro_table = Record.from_config(distro_choice)

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

        locals_block = Locals.construct(LocalVar.construct("timestamp", "${formatdate(\"MMDDYY-hhmm\", timestamp())}").as_dict)

        source_block = Source.construct(
            SourceType.construct(
                NodeType.construct(
                    NodeElements.construct('os_linux_type', "os_linux_release", "c5.xlarge", "region_name", "os_image_name", "os_image_owner", "os_image_user", "cb_version")
                    .as_dict)
                .as_key("cb-node"))
            .as_key("amazon-ebs"))

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
                                        "amazon-ebs",
                                        "cb-node")
                .as_dict)
            .as_dict)

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2], item[3]).as_dict)

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
        self.ask.list_dict(f"Images in cloud {config.cloud}", image_list, sort_key="date")

    def create_nodes(self):
        self.path_map.map(PathType.CLUSTER)

    def create_net(self):
        cidr_util = NetworkDriver()
        subnet_count = 0

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        vpc_cidr = cidr_util.get_next_network()
        subnet_list = list(cidr_util.get_next_subnet())
        zone_list = config.cloud_base().zones()
        region = config.cloud_base().region
        project = config.cloud_base().project
        account_file = config.cloud_base().account_file

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name", "string"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR", "string"),
            ("region_name", region, "Region name", "string"),
            ("cf_gcp_account_file", account_file, "Region name", "string"),
            ("cf_gcp_project", project, "Region name", "string"),
            ("cf_subnet_cidr_1", subnet_list[1], "Region name", "string"),
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

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2], item[3]).as_dict)

        vpc_config = VPCConfig.build()\
            .add(provider_block.as_dict)\
            .add(resource_block.as_dict)\
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
