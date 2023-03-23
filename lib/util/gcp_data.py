##
##

import logging
import time

from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import GCPDataError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.gcp_image import GCPImageDataRecord
from lib.util.cfgmgr import ConfigMgr
from lib.drivers.gcp import GCPDiskTypes, GCPImageProjects


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_public_ip = None
        self.network = None
        self.subnet_list = []
        self.gcp_account_email = None
        self.gcp_project = None
        self.gcp_image_project = None
        self.gcp_account_file = None
        self.private_key = None
        self.ssh_fingerprint = None
        self.public_key = None
        self.image_release = None
        self.image_type = None
        self.image_version = None
        self.image_user = None
        self.generic_image_user = None
        self.image = None
        self.generic_image = None
        self.region = None
        self.cb_index_mem_type = None
        self.disk_iops = 0
        self.disk_size = None
        self.disk_type = None
        self.instance_type = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        network_list = []

        print("")
        in_progress = self.env_cfg.get("gcp_base_in_progress")

        if in_progress is not None and in_progress is False:
            print("Cloud infrastructure is configured")

            self.region = self.env_cfg.get("gcp_region")
            self.gcp_project = self.env_cfg.get("gcp_project")
            self.gcp_account_email = self.env_cfg.get("gcp_account_email")
            self.gcp_account_file = self.env_cfg.get("gcp_account_file")
            self.network = self.env_cfg.get("gcp_network")
            self.subnet_list = self.env_cfg.get("gcp_subnet_list")
            self.use_public_ip = self.env_cfg.get("net_use_public_ip")
            print(f"Region           = {self.region}")
            print(f"Project          = {self.gcp_project}")
            print(f"Account Email    = {self.gcp_account_email}")
            print(f"Account File     = {self.gcp_account_file}")
            print(f"Network          = {self.network}")
            subnet_display = ','.join(list(f"{i['name']}/{i['zone']}" for i in self.subnet_list))
            print(f"Subnets          = {subnet_display}")
            print(f"Assign Public IP = {self.use_public_ip}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(gcp_base_in_progress=True)

        self.region = config.cloud_base().region
        self.gcp_project = config.cloud_base().gcp_project
        self.gcp_account_file = config.cloud_base().gcp_account_file
        self.gcp_account_email = config.cloud_base().gcp_account_email

        self.use_public_ip = Inquire().ask_bool("Assign a public IP")

        try:
            network_list = config.cloud_network().list()
        except EmptyResultSet:
            pass

        env_vpc = next((d for d in network_list if d.get('name') == f"{config.env_name}-vpc"), None)
        if env_vpc:
            self.network = env_vpc.get("name")
        else:
            print(f"No network found for environment {config.env_name}")
            if Inquire().ask_bool("Create cloud infrastructure for the environment"):
                config.cloud_operator().create_net()
                time.sleep(3)
                vpc_data = config.cloud_operator().list_net()
                self.network = vpc_data.get("network_name", {}).get("value", None)
                if not self.network:
                    raise GCPDataError("can not get ID of newly created network")
                print(f"Created {config.env_name} network {self.network}")
            else:
                print(f"Environment {config.env_name} will be deployed on existing cloud infrastructure")
                vpc_list = config.cloud_network().list()
                selection = Inquire().ask_list_dict("Please select a network", vpc_list, hide_key=["subnets"])
                self.network = selection.get("name")

        subnets = config.cloud_subnet().list(self.network, self.region)
        subnets = sorted(subnets, key=lambda d: d['cidr'])

        if len(subnets) > 1:
            subnet_data = Inquire().ask_list_dict("Please choose a subnet", subnets)
        else:
            subnet_data = subnets[0]

        self.subnet_list.clear()
        for zone in config.cloud_base().gcp_zone_list:
            subnet_record = {}
            subnet_record.update(subnet_data)
            subnet_record.update({"zone": zone})
            self.subnet_list.append(subnet_record)

        self.env_cfg.update(gcp_region=self.region)
        self.env_cfg.update(gcp_project=self.gcp_project)
        self.env_cfg.update(gcp_account_email=self.gcp_account_email)
        self.env_cfg.update(gcp_account_file=self.gcp_account_file)
        self.env_cfg.update(gcp_network=self.network)
        self.env_cfg.update(gcp_subnet_list=self.subnet_list)
        self.env_cfg.update(net_use_public_ip=self.use_public_ip)
        self.env_cfg.update(gcp_base_in_progress=False)

    def get_image(self, node_type: str = None):
        in_progress = self.env_cfg.get("gcp_image_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Image is configured")

            self.image_user = self.env_cfg.get("ssh_user_name")
            self.generic_image_user = self.env_cfg.get("ssh_generic_user_name")
            self.image = self.env_cfg.get("gcp_image")
            self.generic_image = self.env_cfg.get("gcp_generic_image")
            self.gcp_image_project = self.env_cfg.get("gcp_image_project")
            self.image_version = self.env_cfg.get("cbs_version")
            print(f"SSH User Name     = {self.image_user}")
            print(f"Generic User Name = {self.generic_image_user}")
            print(f"Image Name        = {self.image}")
            print(f"Generic Image     = {self.generic_image}")
            print(f"Image Project     = {self.gcp_image_project}")
            print(f"CBS Version       = {self.image_version}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(gcp_image_in_progress=True)

        if node_type == "generic":
            image_type = Inquire().ask_list_dict('Image distribution', GCPImageProjects.projects)
            image_list = config.cloud_image().list(project=image_type["project"])
            self.gcp_image_project = image_type["project"]
        else:
            image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])
            self.gcp_image_project = self.env_cfg.get("gcp_image_project")

        image = Inquire().ask_list_dict(f"Select {config.cloud} image", image_list, sort_key="date", hide_key=["link"], reverse_sort=True)

        if node_type == "generic":
            self.generic_image_user = "admin"
            self.image_user = self.env_cfg.get("ssh_user_name")
            self.image_version = self.env_cfg.get("cbs_version")
            self.generic_image = image['name']
            self.image = self.env_cfg.get("gcp_image")
        else:
            self.generic_image = self.env_cfg.get("gcp_generic_image")
            self.image = image['name']
            self.image_release = image['release_tag']
            self.image_type = image['type_tag']
            self.image_version = image['version_tag']
            distro_table = GCPImageDataRecord.by_version(self.image_type, self.image_release, config.cloud_operator().config.build)
            self.generic_image_user = self.env_cfg.get("ssh_generic_user_name")
            self.image_user = distro_table.user

        self.env_cfg.update(ssh_user_name=self.image_user)
        self.env_cfg.update(ssh_generic_user_name=self.generic_image_user)
        self.env_cfg.update(gcp_image=self.image)
        self.env_cfg.update(gcp_image_project=self.gcp_image_project)
        self.env_cfg.update(gcp_generic_image=self.generic_image)
        self.env_cfg.update(cbs_version=self.image_version)
        self.env_cfg.update(gcp_image_in_progress=False)

    def get_keys(self):
        in_progress = self.env_cfg.get("ssh_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("SSH key is configured")

            self.private_key = self.env_cfg.get("ssh_private_key")
            self.ssh_fingerprint = self.env_cfg.get("ssh_fingerprint")
            self.public_key = self.env_cfg.get("ssh_public_key")
            print(f"Private Key       = {self.private_key}")
            print(f"Fingerprint       = {self.ssh_fingerprint}")
            print(f"Public Key        = {self.public_key}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(ssh_in_progress=True)

        try:
            key_file_list = FileManager.list_private_key_files()
            ssh_key = Inquire().ask_list_dict("Select SSH private key file", key_file_list, hide_key=["pub_fingerprint"])
            self.private_key = ssh_key.get("file")
            self.ssh_fingerprint = ssh_key.get("fingerprint")
        except EmptyResultSet:
            raise GCPDataError(f"can not find any SSH private key files, please create a SSH key")

        self.public_key = FileManager().get_ssh_public_key_file(self.private_key)

        self.env_cfg.update(ssh_private_key=self.private_key)
        self.env_cfg.update(ssh_fingerprint=self.ssh_fingerprint)
        self.env_cfg.update(ssh_public_key=self.public_key)
        self.env_cfg.update(ssh_in_progress=False)

    def get_cluster_settings(self, node_type: str = None):
        if node_type != "cluster":
            return
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
        in_progress = self.env_cfg.get("gcp_node_in_progress")

        print("")
        if in_progress is not None and (in_progress is False or default is False):
            print("Node settings")

            self.instance_type = self.env_cfg.get("gcp_machine_type")
            self.disk_type = self.env_cfg.get("gcp_root_type")
            self.disk_size = self.env_cfg.get("gcp_root_size")
            print(f"Machine Type = {self.instance_type}")
            print(f"Disk Type    = {self.disk_type}")
            print(f"Disk Size    = {self.disk_size}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(gcp_node_in_progress=True)

        machine_list = config.cloud_machine_type().list()

        selection = Inquire().ask_machine_type("Select machine type", machine_list)

        self.instance_type = selection['name']

        selection = Inquire().ask_list_dict("Select disk type", GCPDiskTypes.disk_type_list, default_value=("type", "pd-ssd"))
        self.disk_type = selection['type']
        self.disk_size = Inquire().ask_int("Volume size", 250, 100)

        self.env_cfg.update(gcp_machine_type=self.instance_type)
        self.env_cfg.update(gcp_root_type=self.disk_type)
        self.env_cfg.update(gcp_root_size=self.disk_size)
        self.env_cfg.update(gcp_node_in_progress=False)
