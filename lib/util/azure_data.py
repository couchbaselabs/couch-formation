##
##

import logging
import os
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import AzureDataError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.azure_image import AzureImageDataRecord
from lib.util.cfgmgr import ConfigMgr
from lib.drivers.azure import AzureDiskTypes, AzureImagePublishers


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.azure_image_rg = None
        self.disk_iops = 0
        self.disk_size = None
        self.disk_type = None
        self.instance_type = None
        self.cb_index_mem_type = None
        self.image_user = None
        self.generic_image_user = None
        self.image_version = None
        self.image_type = None
        self.image_release = None
        self.image = None
        self.image_publisher = None
        self.image_offer = None
        self.image_sku = None
        self.public_key = None
        self.ssh_fingerprint = None
        self.private_key = None
        self.azure_nsg = None
        self.subnet_list = []
        self.network = None
        self.use_public_ip = None
        self.azure_resource_group = None
        self.region = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        rg_list = []

        print("")
        in_progress = self.env_cfg.get("azure_base_in_progress")

        if in_progress is not None and in_progress is False:
            print("Cloud infrastructure is configured")

            self.region = self.env_cfg.get("azure_region")
            self.azure_resource_group = self.env_cfg.get("azure_resource_group")
            self.azure_nsg = self.env_cfg.get("azure_security_group")
            self.network = self.env_cfg.get("azure_network")
            self.subnet_list = self.env_cfg.get("azure_subnet_list")
            self.use_public_ip = self.env_cfg.get("net_use_public_ip")
            print(f"Location         = {self.region}")
            print(f"Resource Group   = {self.azure_resource_group}")
            print(f"Security Group   = {self.azure_nsg}")
            print(f"Network          = {self.network}")
            subnet_display = ','.join(list(f"{i['name']}/{i['zone']}" for i in self.subnet_list))
            print(f"Subnets          = {subnet_display}")
            print(f"Assign Public IP = {self.use_public_ip}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                os.environ['AZURE_LOCATION'] = self.region
                os.environ['AZURE_RESOURCE_GROUP'] = self.azure_resource_group
                return

        self.env_cfg.update(azure_base_in_progress=True)

        self.region = config.cloud_base().region

        if not self.region:
            location_list = config.cloud_base().list_locations()
            result = Inquire().ask_list_dict('Azure Location', location_list)
            self.region = result['name']

        os.environ['AZURE_LOCATION'] = self.region

        try:
            rg_list = config.cloud_base().list_rg(self.region)
        except EmptyResultSet:
            pass

        env_rg = next((d for d in rg_list if d.get('name') == f"{config.env_name}-rg"), None)
        if env_rg:
            self.azure_resource_group = env_rg.get("name")
            network_list = config.cloud_network().list(self.azure_resource_group)
            env_vpc = next((d for d in network_list if d.get('name') == f"{config.env_name}-vpc"), None)
            if env_vpc:
                self.network = env_vpc.get("name")
            else:
                raise AzureDataError(f"can not find {config.env_name} network in resource group {self.azure_resource_group}")
        else:
            print(f"No resource group found for environment {config.env_name}")
            if Inquire().ask_bool("Create cloud infrastructure for the environment"):
                config.cloud_operator().create_net()
                vpc_data = config.cloud_operator().list_net()
                self.azure_resource_group = vpc_data.get("resource_group", {}).get("value", None)
                self.network = vpc_data.get("network_name", {}).get("value", None)
                if not self.network:
                    raise AzureDataError("can not get names of newly created resources")
                print(f"Created {config.env_name} network {self.network} in resource group {self.azure_resource_group}")
            else:
                print(f"Environment {config.env_name} will be deployed on existing cloud infrastructure")
                selection = Inquire().ask_list_dict("Please select a resource group", rg_list, hide_key=["id"])
                self.azure_resource_group = selection.get("name")
                vpc_list = config.cloud_network().list(self.azure_resource_group)
                selection = Inquire().ask_list_dict("Please select a network", vpc_list, hide_key=["id", "cidr", "subnets"])
                self.network = selection.get("name")

        os.environ['AZURE_RESOURCE_GROUP'] = self.azure_resource_group

        self.use_public_ip = Inquire().ask_bool("Assign a public IP")

        subnets = config.cloud_subnet().list(self.network, self.azure_resource_group)
        subnets = sorted(subnets, key=lambda d: d['cidr'])

        if len(subnets) > 1:
            subnet_data = Inquire().ask_list_dict("Please choose a subnet", subnets, hide_key=["id", "routes"])
        else:
            subnet_data = subnets[0]

        self.subnet_list.clear()
        for zone in config.cloud_base().azure_availability_zones:
            subnet_record = {}
            subnet_record.update(subnet_data)
            subnet_record.update({"zone": zone})
            self.subnet_list.append(subnet_record)

        self.azure_nsg = subnet_data['nsg']

        self.env_cfg.update(azure_region=self.region)
        self.env_cfg.update(azure_resource_group=self.azure_resource_group)
        self.env_cfg.update(azure_security_group=self.azure_nsg)
        self.env_cfg.update(azure_network=self.network)
        self.env_cfg.update(azure_subnet_list=self.subnet_list)
        self.env_cfg.update(net_use_public_ip=self.use_public_ip)
        self.env_cfg.update(azure_base_in_progress=False)

    def get_image(self, node_type: str = None):
        in_progress = self.env_cfg.get("azure_image_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Image is configured")

            self.image_user = self.env_cfg.get("ssh_user_name")
            self.generic_image_user = self.env_cfg.get("ssh_generic_user_name")
            self.image = self.env_cfg.get("azure_image")
            self.image_publisher = self.env_cfg.get("azure_image_publisher")
            self.image_offer = self.env_cfg.get("azure_image_offer")
            self.image_sku = self.env_cfg.get("azure_image_sku")
            self.azure_image_rg = self.env_cfg.get("azure_image_resource_group")
            self.image_version = self.env_cfg.get("cbs_version")
            print(f"SSH User Name        = {self.image_user}")
            print(f"Generic User Name    = {self.generic_image_user}")
            print(f"Image Name           = {self.image}")
            print(f"Image Publisher      = {self.image_publisher}")
            print(f"Image Offer          = {self.image_offer}")
            print(f"Image Sku            = {self.image_sku}")
            print(f"Image Resource Group = {self.azure_image_rg}")
            print(f"CBS Version          = {self.image_version}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(azure_image_in_progress=True)

        if node_type == "generic":
            self.generic_image_user = "sysadmin"
            self.image_user = self.env_cfg.get("ssh_user_name")
            self.image_version = self.env_cfg.get("cbs_version")
            publisher = Inquire().ask_list_dict('Image distribution', AzureImagePublishers.publishers)
            self.image_publisher = publisher["name"]
            image_list_struct = config.cloud_image().public(self.region, publisher["name"])
            offer_list = list(i["name"] for i in image_list_struct)
            self.image_offer = Inquire().ask_list_basic('Image Offer', offer_list)
            offer = next(i for i in image_list_struct if i["name"] == self.image_offer)
            self.image_sku = Inquire().ask_list_basic('Image SKU', offer["skus"], sort=True, reverse_sort=True)
            self.image = self.env_cfg.get("azure_image")
            self.azure_image_rg = self.env_cfg.get("azure_image_resource_group")
        else:
            image_list = config.cloud_image().list(filter_keys_exist=["release_tag", "type_tag", "version_tag"])
            image = Inquire().ask_list_dict(f"Select {config.cloud} image", image_list, sort_key="name", hide_key=["id"])
            self.image = image['name']
            self.azure_image_rg = image['resource_group']
            self.image_release = image['release_tag']
            self.image_type = image['type_tag']
            self.image_version = image['version_tag']
            self.image_publisher = self.env_cfg.get("azure_image_publisher")
            self.image_offer = self.env_cfg.get("azure_image_offer")
            self.image_sku = self.env_cfg.get("azure_image_sku")
            self.generic_image_user = self.env_cfg.get("ssh_generic_user_name")
            distro_table = AzureImageDataRecord.by_version(self.image_type, self.image_release, config.cloud_operator().config.build)
            self.image_user = distro_table.user

        self.env_cfg.update(ssh_user_name=self.image_user)
        self.env_cfg.update(ssh_generic_user_name=self.generic_image_user)
        self.env_cfg.update(azure_image=self.image)
        self.env_cfg.update(azure_image_publisher=self.image_publisher)
        self.env_cfg.update(azure_image_offer=self.image_offer)
        self.env_cfg.update(azure_image_sku=self.image_sku)
        self.env_cfg.update(azure_image_resource_group=self.azure_image_rg)
        self.env_cfg.update(cbs_version=self.image_version)
        self.env_cfg.update(azure_image_in_progress=False)

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
            raise AzureDataError(f"can not find any SSH private key files, please create a SSH key")

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
        in_progress = self.env_cfg.get("azure_node_in_progress")

        print("")
        if in_progress is not None and (in_progress is False or default is False):
            print("Node settings")

            self.instance_type = self.env_cfg.get("azure_machine_type")
            self.disk_type = self.env_cfg.get("azure_root_type")
            self.disk_size = self.env_cfg.get("azure_root_size")
            print(f"Machine Type = {self.instance_type}")
            print(f"Disk Type    = {self.disk_type}")
            print(f"Disk Size    = {self.disk_size}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(azure_node_in_progress=True)

        machine_list = config.cloud_machine_type().list()

        selection = Inquire().ask_machine_type("Select machine type", machine_list)

        self.instance_type = selection['name']

        selection = Inquire().ask_list_dict("Select disk type", AzureDiskTypes.disk_type_list, default_value=("type", "StandardSSD_LRS"))
        self.disk_type = selection['type']
        self.disk_size = Inquire().ask_int("Volume size", 250, 100)

        self.env_cfg.update(azure_machine_type=self.instance_type)
        self.env_cfg.update(azure_root_type=self.disk_type)
        self.env_cfg.update(azure_root_size=self.disk_size)
        self.env_cfg.update(azure_node_in_progress=False)
