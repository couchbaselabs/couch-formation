##
##

import logging
import time
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import AWSDriverError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.aws_image import AWSImageDataRecord
from lib.util.cfgmgr import ConfigMgr
from lib.drivers.aws import AWSEbsDiskTypes


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_public_ip = None
        self.vpc_id = None
        self.subnet_list = []
        self.security_group_id = None
        self.env_ssh_key = None
        self.env_ssh_fingerprint = None
        self.env_ssh_filename = None
        self.image_release = None
        self.image_type = None
        self.image_version = None
        self.image_user = None
        self.ami_id = None
        self.region = None
        self.cb_index_mem_type = None
        self.disk_iops = None
        self.disk_size = None
        self.disk_type = None
        self.instance_type = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        vpc_list = []

        print("")
        in_progress = self.env_cfg.get("aws_base_in_progress")

        if in_progress is not None and in_progress is False:
            print("Cloud infrastructure is configured")

            self.region = self.env_cfg.get("aws_region")
            self.vpc_id = self.env_cfg.get("aws_vpc_id")
            self.subnet_list = self.env_cfg.get("aws_subnet_list")
            self.security_group_id = self.env_cfg.get("aws_security_group_id")
            self.use_public_ip = self.env_cfg.get("net_use_public_ip")
            print(f"Region           = {self.region}")
            print(f"VPC              = {self.vpc_id}")
            print(f"Subnets          = {','.join(list(i['name'] for i in self.subnet_list))}")
            print(f"Security Group   = {self.security_group_id}")
            print(f"Assign Public IP = {self.use_public_ip}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(aws_base_in_progress=True)

        self.region = config.cloud_base().region

        self.use_public_ip = Inquire().ask_bool("Assign a public IP")

        try:
            vpc_list = config.cloud_network().list(filter_keys_exist=["environment_tag"])
        except EmptyResultSet:
            pass

        env_vpc = next((d for d in vpc_list if d.get('environment_tag') == config.env_name), None)
        if env_vpc:
            self.vpc_id = env_vpc.get("id")
        else:
            print(f"No network found for environment {config.env_name}")
            if Inquire().ask_bool("Create cloud infrastructure for the environment"):
                config.cloud_operator().create_net()
                time.sleep(3)
                vpc_data = config.cloud_operator().list_net()
                self.vpc_id = vpc_data.get("network_name", {}).get("value", None)
                if not self.vpc_id:
                    raise AWSDriverError("can not get ID of newly created VPC")
            else:
                print(f"Environment {config.env_name} will be deployed on existing cloud infrastructure")
                vpc_list = config.cloud_network().list()
                selection = Inquire().ask_list_dict("Please select a VPC", vpc_list)
                self.vpc_id = selection.get("id")

        subnets = config.cloud_subnet().list(self.vpc_id)
        subnets = sorted(subnets, key=lambda d: d['cidr'])
        self.subnet_list.clear()
        for s in subnets:
            self.subnet_list.append(s)

        sec_groups = config.cloud_security_group().list(self.vpc_id)
        security_group = next((i for i in sec_groups if i['environment_tag'] == config.env_name), None)
        if security_group:
            self.security_group_id = security_group['id']
        else:
            selection = Inquire().ask_list_dict("Please select a security group", sec_groups)
            self.security_group_id = selection['id']

        self.env_cfg.update(aws_region=self.region)
        self.env_cfg.update(aws_vpc_id=self.vpc_id)
        self.env_cfg.update(aws_subnet_list=self.subnet_list)
        self.env_cfg.update(aws_security_group_id=self.security_group_id)
        self.env_cfg.update(net_use_public_ip=self.use_public_ip)
        self.env_cfg.update(aws_base_in_progress=False)

    def get_image(self):
        in_progress = self.env_cfg.get("aws_image_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Image is configured")

            self.image_user = self.env_cfg.get("ssh_user_name")
            self.ami_id = self.env_cfg.get("aws_ami_id")
            self.image_version = self.env_cfg.get("cbs_version")
            print(f"SSH User Name = {self.image_user}")
            print(f"AMI ID        = {self.ami_id}")
            print(f"CBS Version   = {self.image_version}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(aws_image_in_progress=True)

        image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])

        image = Inquire().ask_list_dict(f"Select {config.cloud} image", image_list, sort_key="date")

        self.ami_id = image['name']
        self.image_release = image['release_tag']
        self.image_type = image['type_tag']
        self.image_version = image['version_tag']

        distro_table = AWSImageDataRecord.by_version(self.image_type, self.image_release, config.cloud_operator().config.build)

        self.image_user = distro_table.user

        self.env_cfg.update(ssh_user_name=self.image_user)
        self.env_cfg.update(aws_ami_id=self.ami_id)
        self.env_cfg.update(cbs_version=self.image_version)
        self.env_cfg.update(aws_image_in_progress=False)

    def get_keys(self):
        key_list = []

        in_progress = self.env_cfg.get("ssh_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("SSH key is configured")

            self.env_ssh_key = self.env_cfg.get("aws_key_pair")
            self.env_ssh_fingerprint = self.env_cfg.get("ssh_fingerprint")
            self.env_ssh_filename = self.env_cfg.get("ssh_private_key")
            print(f"Key-pair             = {self.env_ssh_key}")
            print(f"Fingerprint          = {self.env_ssh_fingerprint}")
            print(f"Private Key Filename = {self.env_ssh_filename}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(ssh_in_progress=True)

        try:
            key_list = config.ssh_key().list(filter_keys_exist=["environment_tag"])
        except EmptyResultSet:
            pass

        env_ssh = next((d for d in key_list if d.get('environment_tag') == config.env_name), None)
        if not env_ssh:
            print(f"No SSH key found for environment {config.env_name}")
            if Inquire().ask_bool("Add SSH key to the environment"):
                config.cloud_operator().create_key()
                env_ssh = config.cloud_operator().list_key()
            else:
                key_list = config.ssh_key().list()
                env_ssh = Inquire().ask_list_dict("Please select a key-pair", key_list)

        self.env_ssh_key = env_ssh.get("name")
        self.env_ssh_fingerprint = env_ssh.get("fingerprint")
        self.env_ssh_filename = FileManager().get_key_by_fingerprint(self.env_ssh_fingerprint)

        self.env_cfg.update(aws_key_pair=self.env_ssh_key)
        self.env_cfg.update(ssh_fingerprint=self.env_ssh_fingerprint)
        self.env_cfg.update(ssh_private_key=self.env_ssh_filename)
        self.env_cfg.update(ssh_in_progress=False)

    def get_cluster_settings(self):
        option_list = [
            {
                'name': 'default',
                'description': 'Standard Index Storage'
            },
            {
                'name': 'memopt',
                'description': 'Memory-optimized'
            },
        ]

        in_progress = self.env_cfg.get("cbs_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Cluster settings are configured")

            self.cb_index_mem_type = self.env_cfg.get("cbs_index_memory")
            print(f"CBS Index Memory = {self.cb_index_mem_type}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(cbs_in_progress=True)

        selection = Inquire().ask_list_dict('Select index storage option', option_list)
        self.cb_index_mem_type = selection['name']

        self.env_cfg.update(cbs_index_memory=self.cb_index_mem_type)
        self.env_cfg.update(cbs_in_progress=False)

    def get_node_settings(self, default: bool = True):
        in_progress = self.env_cfg.get("aws_node_in_progress")

        print("")
        if in_progress is not None and (in_progress is False or default is False):
            print("Node settings")

            self.instance_type = self.env_cfg.get("aws_machine_type")
            self.disk_type = self.env_cfg.get("aws_root_type")
            self.disk_size = self.env_cfg.get("aws_root_size")
            self.disk_iops = self.env_cfg.get("aws_root_iops")
            print(f"Machine Type = {self.instance_type}")
            print(f"Disk Type    = {self.disk_type}")
            print(f"Disk Size    = {self.disk_size}")
            print(f"Disk IOPS    = {self.disk_iops}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(aws_node_in_progress=True)

        machine_list = config.cloud_machine_type().list()

        selection = Inquire().ask_machine_type("Select machine type", machine_list)

        self.instance_type = selection['name']

        selection = Inquire().ask_list_dict("Select disk type", AWSEbsDiskTypes.ebs_type_list, default_value=("type", "gp3"))
        self.disk_type = selection['type']
        self.disk_size = Inquire().ask_int("Volume size", 250, 100)

        if selection['iops']:
            self.disk_iops = Inquire().ask_int("Volume IOPS", selection['iops'], selection['iops'], selection['max'])

        self.env_cfg.update(aws_machine_type=self.instance_type)
        self.env_cfg.update(aws_root_type=self.disk_type)
        self.env_cfg.update(aws_root_size=self.disk_size)
        self.env_cfg.update(aws_root_iops=self.disk_iops)
        self.env_cfg.update(aws_node_in_progress=False)
