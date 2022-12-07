##
##

import logging
import json
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.exceptions import AWSDriverError, EmptyResultSet
from lib.drivers.cbrelease import CBRelease
from lib.drivers.network import NetworkDriver
from lib.util.inquire import Inquire
from lib.util.filemgr import FileManager
from lib.invoke import tf_run, packer_run
from lib.util.cfgmgr import ConfigMgr
from lib.util.aws_data import DataCollect
import lib.config as config
from lib.hcl.aws_vpc import AWSProvider, VPCResource, InternetGatewayResource, RouteEntry, RouteResource, SubnetResource, RTAssociationResource, SecurityGroupEntry, \
    SGResource, Resources, VPCConfig
from lib.hcl.aws_image import Packer, PackerElement, RequiredPlugins, AmazonPlugin, AmazonPluginSettings, ImageMain, Source, SourceType, NodeType, NodeElements, \
    ImageBuild, BuildConfig, BuildElements, Shell, ShellElements, AWSImageDataRecord
from lib.hcl.common import Variable, Variables, Locals, LocalVar, NodeMain, NullResource, NullResourceBlock, NullResourceBody, DependsOn, InLine, Connection, ConnectionElements, \
    RemoteExec, ForEach, Provisioner, Triggers, Output, OutputValue, Build, Entry, ResourceBlock, NodeBuild
from lib.hcl.aws_instance import AWSInstance, BlockDevice, EbsElements, RootElements, NodeConfiguration


class CloudDriver(object):
    VERSION = '3.0.0'
    HOST_PREP_REPO = "couchbaselabs/couchbase-hostprep"
    DRIVER_CONFIG = "aws.json"
    NETWORK_CONFIG = "main.tf.json"
    IMAGE_CONFIG = "main.pkr.json"
    CONFIG_FILE = "config.json"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.ask = Inquire()

        if not config.env_name:
            raise AWSDriverError("no environment specified")

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

        self.driver_config = self.path_map.root + "/" + CloudDriver.DRIVER_CONFIG
        try:
            self.get_config()
        except Exception as err:
            raise AWSDriverError(f"can not read config file: {err}")

    def get_config(self):
        with open(self.driver_config, 'r') as config_file:
            cfg_text = config_file.read()
            cfg_json = json.loads(cfg_text)
        config_file.close()

        self.config = Build.from_config(cfg_json)

    def create_image(self):
        cb_rel = CBRelease()

        region = config.cloud_base().region

        print(f"Configuring image in region {region}")

        os_list = [i for i in self.config.build.keys()]
        os_choice = self.ask.ask_list_basic("Select OS", os_list)

        distro_list = Entry.from_config(os_choice, self.config.build)

        distro_choice = self.ask.ask_list_dict("Select OS revision", distro_list.versions)

        distro_table = AWSImageDataRecord.from_config(distro_choice)

        release_list = cb_rel.get_cb_version(os_choice, distro_table.version)

        cb_release_choice = self.ask.ask_list_basic("Select CBS release", release_list)

        var_list = [
            ("os_linux_type", os_choice, "OS Name"),
            ("region_name", region, "Region name"),
            ("cb_version", cb_release_choice, "CBS Revision"),
            ("host_prep_repo", CloudDriver.HOST_PREP_REPO, "Host Prep Utility"),
            ("os_image_name", distro_table.image, "Image"),
            ("os_image_owner", distro_table.owner, "Image Owner"),
            ("os_image_user", distro_table.user, "Image User"),
            ("os_linux_release", distro_table.version, "OS Revision"),
        ]

        packer_block = Packer.construct(
            PackerElement.construct(
                RequiredPlugins.construct(
                    AmazonPlugin.construct(
                        AmazonPluginSettings.construct("github.com/hashicorp/amazon", "1.1.1")
                        .as_dict)
                    .as_dict)
                .as_dict)
            .as_dict)

        locals_block = Locals.construct(LocalVar.build().add("timestamp", "${formatdate(\"MMDDYY-hhmm\", timestamp())}").as_dict)

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
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        packer_config = ImageMain.build()\
            .add(packer_block.as_dict)\
            .add(locals_block.as_dict)\
            .add(source_block.as_dict)\
            .add(build_block.as_dict)\
            .add(var_block.as_dict).as_dict

        self.path_map.map(PathType.IMAGE)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.IMAGE_CONFIG, PathType.IMAGE)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(packer_config, cfg_file_h, indent=2)
        except Exception as err:
            raise AWSDriverError(f"can not write to image config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Building {os_choice} {distro_table.version} {cb_release_choice} image in {config.cloud}")
            pr = packer_run(working_dir=cfg_file.file_path)
            pr.init(cfg_file.file_name)
            pr.build_gen(cfg_file.file_name)
        except Exception as err:
            AWSDriverError(f"can not build image: {err}")

    def list_images(self):
        image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])
        self.ask.list_dict(f"Images in cloud {config.cloud}", image_list, sort_key="date")

    def create_nodes(self, node_type: str):
        dc = DataCollect()

        dc.get_infrastructure()
        dc.get_keys()
        dc.get_image()
        dc.get_cluster_settings()
        dc.get_node_settings()

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name"),
            ("region_name", dc.region, "Region name"),
            ("ami_id", dc.ami_id, "AMI Id"),
            ("ssh_user", dc.image_user, "Admin Username"),
            ("ssh_key", dc.env_ssh_key, "SSH key-pair name"),
            ("ssh_private_key", dc.env_ssh_filename, "SSH filename"),
            ("vpc_id", dc.vpc_id, "VPC ID"),
            ("security_group_ids", [dc.security_group_id], "Security group"),
            ("instance_type", dc.instance_type, "Instance type"),
            ("index_memory", dc.cb_index_mem_type, "Index memory setting"),
            ("root_volume_iops", str(dc.disk_iops), "Volume IOPS"),
            ("root_volume_size", str(dc.disk_size), "Volume size"),
            ("root_volume_type", dc.disk_type, "EBS type"),
        ]

        if node_type == "app":
            self.path_map.map(PathType.APP)
        elif node_type == "sgw":
            self.path_map.map(PathType.SGW)
        elif node_type == "generic":
            self.path_map.map(PathType.GENERIC)
        else:
            self.path_map.map(PathType.CLUSTER)

        print(f"Configuring {self.path_map.last_mapped} nodes in region {dc.region}")

        var_block = Variables.build()
        for item in var_list:
            var_block.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        locals_block = Locals.construct(LocalVar.build()
                                        .add("cluster_init_name", config.env_name)
                                        .add("rally_node", "${element([for node in aws_instance.couchbase_nodes: node.private_ip], 0)}")
                                        .add("rally_node_public", "${element([for node in aws_instance.couchbase_nodes: node.public_ip], 0)}")
                                        .as_dict)

        null_resource_block = NullResource.build().add(
            NullResourceBlock.construct(
                NullResourceBody
                .build()
                .add(Connection.build()
                     .add(
                    ConnectionElements.construct(
                        "${var.use_public_ip ? each.value.public_ip : each.value.private_ip}",
                        "ssh_private_key",
                        "ssh_user").as_dict)
                     .as_dict)
                .add(DependsOn.build()
                     .add("${aws_instance.couchbase_nodes}")
                     .add("${time_sleep.pause}").as_dict)
                .add(ForEach.construct("${aws_instance.couchbase_nodes}").as_dict)
                .add(Provisioner.build()
                     .add(RemoteExec.build()
                          .add(InLine.build()
                               .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node} -n ${local.cluster_init_name}")
                               .as_dict)
                          .as_dict)
                     .as_dict)
                .add(Triggers.build()
                     .add("cb_nodes", "${join(\",\", keys(aws_instance.couchbase_nodes))}")
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
                        "${var.use_public_ip ? local.rally_node_public : local.rally_node}",
                        "ssh_private_key",
                        "ssh_user").as_dict)
                     .as_dict)
                .add(DependsOn.build()
                     .add("${null_resource.couchbase-init}").as_dict)
                .add(Provisioner.build()
                     .add(RemoteExec.build()
                          .add(InLine.build()
                               .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m rebalance -r ${local.rally_node}")
                               .as_dict)
                          .as_dict)
                     .as_dict)
                .add(Triggers.build()
                     .add("cb_nodes", "${join(\",\", keys(aws_instance.couchbase_nodes))}")
                     .as_dict)
                .as_dict
            )
            .as_name("couchbase-rebalance")
        )

        output_block = Output.build().add(
            OutputValue.build()
            .add("${[for instance in aws_instance.couchbase_nodes: instance.private_ip]}")
            .as_name("node-private")
        ).add(
            OutputValue.build()
            .add("${var.use_public_ip ? [for instance in aws_instance.couchbase_nodes: instance.public_ip] : null}")
            .as_name("node-public")
        )

        swap_disk_block = BlockDevice.build().add(
            EbsElements.construct(
                "/dev/xvdb",
                "root_volume_iops",
                "node_ram",
                "root_volume_type"
            ).as_dict
        ).as_dict
        instance_block = AWSInstance.build().add(
            NodeBuild.construct(
                NodeConfiguration.construct(
                    "cf_env_name",
                    "ami_id",
                    "node_zone",
                    "cluster_spec",
                    "instance_type",
                    "ssh_key",
                    Provisioner.build()
                    .add(RemoteExec.build().add(Connection.build().add(
                          ConnectionElements.construct(
                            "${var.use_public_ip ? each.value.public_ip : each.value.private_ip}",
                            "ssh_private_key",
                            "ssh_user")
                          .as_dict)
                        .as_dict)
                         .add(InLine.build()
                              .add("sudo /usr/local/hostprep/bin/refresh.sh")
                              .add("sudo /usr/local/hostprep/bin/configure-swap.sh -o ${each.value.node_swap} -d /dev/xvdb")
                              .add("sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${self.private_ip} -e %{if var.use_public_ip}${self.public_ip}%{else}none%{endif} -s ${each.value.node_services} -o ${var.index_memory} -g ${each.value.node_zone}")
                              .as_dict)
                         .as_dict)
                    .as_dict,
                    RootElements.construct(
                        "root_volume_iops",
                        "root_volume_size",
                        "root_volume_type"
                    ).as_dict,
                    "node_subnet",
                    "security_group_ids",
                    "node_services",
                    swap_disk_block
                ).as_dict
            ).as_name("couchbase_nodes")
        )

        resource_block = ResourceBlock.build()
        resource_block.add(instance_block.as_dict)
        resource_block.add(null_resource_block.as_dict)

        main_config = NodeMain.build()\
            .add(locals_block.as_dict) \
            .add(resource_block.as_dict) \
            .add(output_block.as_dict) \
            .add(var_block.as_dict).as_dict

        print(json.dumps(main_config, indent=2))

    def create_net(self):
        cidr_util = NetworkDriver()
        subnet_count = 0

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        vpc_cidr = cidr_util.get_next_network()
        subnet_list = list(cidr_util.get_next_subnet())
        zone_list = config.cloud_base().zones()
        region = config.cloud_base().region

        print(f"Configuring VPC in region {region}")

        var_list = [
            ("cf_env_name", config.env_name, "Environment Name"),
            ("cf_vpc_cidr", vpc_cidr, "VPC CIDR"),
            ("region_name", region, "Region name"),
        ]

        if config.cloud_zone:
            print(f"Using single zone: {config.cloud_zone}")
            subnet_count += 1
            if config.cloud_zone not in zone_list:
                raise AWSDriverError(f"zone {config.cloud_zone} not found in region {region}")
            var_list.append(
                ("cf_subnet_az_1", config.cloud_zone, "Availability Zone", "string")
            )
            var_list.append(
                ("cf_subnet_cidr_1", subnet_list[1], "Subnet CIDR", "string")
            )
        else:
            print(f"Using multiple zones: {','.join(zone_list)}")
            for n, zone in enumerate(zone_list):
                subnet_count += 1
                var_list.append(
                    (f"cf_subnet_az_{n+1}", zone, "Availability Zone", "string")
                )
                var_list.append(
                    (f"cf_subnet_cidr_{n+1}", subnet_list[n+1], "Subnet CIDR", "string")
                )

        provider_block = AWSProvider.for_region("region_name")

        cf_vpc = VPCResource.construct("cf_vpc_cidr", "cf_env_name").as_dict

        cf_gw = InternetGatewayResource.construct("cf_vpc", "cf_env_name").as_dict

        route_entry = RouteEntry.construct("cf_gw", "cf_vpc", "cf_env_name")
        route_entry.add("0.0.0.0/0", "cf_gw")
        cf_rt = RouteResource.construct(route_entry.as_dict).as_dict

        subnet_struct = SubnetResource.build()
        association_struct = RTAssociationResource.build()
        for i in range(subnet_count):
            subnet_name = f"cf_subnet_{i+1}"
            subnet_struct.add(subnet_name, f"cf_subnet_az_{i+1}", f"cf_subnet_cidr_{i+1}", True, "cf_env_name", "cf_vpc")
            association_struct.add("cf_rt", subnet_name)
        subnet_resources = subnet_struct.as_dict
        rt_association_resources = association_struct.as_dict

        sg_entry = SecurityGroupEntry.construct("cf_vpc", "cf_env_name")
        sg_entry.add_ingress("0.0.0.0/0", 22, "tcp", 22)
        sg_entry.add_ingress("0.0.0.0/0", 8091, "tcp", 8097)
        sg_entry.add_ingress("0.0.0.0/0", 9123, "tcp", 9123)
        sg_entry.add_ingress("0.0.0.0/0", 9140, "tcp", 9140)
        sg_entry.add_ingress("0.0.0.0/0", 11210, "tcp", 11210)
        sg_entry.add_ingress("0.0.0.0/0", 11280, "tcp", 11280)
        sg_entry.add_ingress("0.0.0.0/0", 11207, "tcp", 11207)
        sg_entry.add_ingress("0.0.0.0/0", 18091, "tcp", 18097)
        sg_entry.add_ingress("0.0.0.0/0", 4984, "tcp", 4986)
        cf_sg = SGResource.construct(sg_entry.as_dict).as_dict

        resource_block = Resources.build()
        resource_block.add(cf_vpc)
        resource_block.add(subnet_resources)
        resource_block.add(rt_association_resources)
        resource_block.add(cf_gw)
        resource_block.add(cf_rt)
        resource_block.add(cf_sg)

        output_block = Output.build()
        output_block.add(
            OutputValue.build()
            .add("aws_vpc.cf_vpc.id")
            .as_name("network_name")
        )
        for i in range(subnet_count):
            subnet_name = f"cf_subnet_{i + 1}"
            output_block.add(
                OutputValue.build()
                .add(f"aws_subnet.{subnet_name}")
                .as_name(subnet_name)
            )

        var_struct = Variables.build()
        for item in var_list:
            var_struct.add(Variable.construct(item[0], item[1], item[2]).as_dict)

        vpc_config = VPCConfig.build() \
            .add(provider_block.as_dict) \
            .add(resource_block.as_dict) \
            .add(output_block.as_dict) \
            .add(var_struct.as_dict).as_dict

        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            with open(cfg_file.file_name, 'w') as cfg_file_h:
                json.dump(vpc_config, cfg_file_h, indent=2)
        except Exception as err:
            raise AWSDriverError(f"can not write to network config file {cfg_file.file_name}: {err}")

        try:
            print("")
            print(f"Creating VPC ...")
            tf = tf_run(working_dir=cfg_file.file_path)
            tf.init()
            if not tf.validate():
                raise AWSDriverError("Environment is not configured properly, please check the log and try again.")
            tf.apply()
        except Exception as err:
            raise AWSDriverError(f"can not create VPC: {err}")

    def list_net(self):
        self.path_map.map(PathType.NETWORK)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(CloudDriver.NETWORK_CONFIG, PathType.NETWORK)
        try:
            tf = tf_run(working_dir=cfg_file.file_path)
            vpc_data = tf.output(quiet=True)
            return vpc_data
        except Exception as err:
            raise AWSDriverError(f"can not list VPC: {err}")

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
            raise AWSDriverError(f"can not destroy VPC: {err}")

    def create_key(self):
        try:
            key_file_list = FileManager.list_private_key_files()
        except EmptyResultSet:
            raise AWSDriverError(f"can not find any SSH private key files, please create a SSH key")

        ssh_key = self.ask.ask_list_dict("Select SSH private key file", key_file_list, hide_key=["fingerprint"])

        key_info = config.ssh_key().create(f"{config.env_name}-key", ssh_key["file"], {"Environment": config.env_name})

        self.env_cfg.update(ssh_name=key_info['name'], ssh_fingerprint=key_info['fingerprint'])

    def list_key(self):
        try:
            key_name = self.env_cfg.get("ssh_name")
            return config.ssh_key().details(key_name)
        except Exception as err:
            raise AWSDriverError(f"can not list SSH key: {err}")
