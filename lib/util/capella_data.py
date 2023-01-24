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
from lib.drivers.gcp import GCPDiskTypes
from lib.drivers.network import NetworkDriver


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cluster_name = None
        self.single_az = True
        self.provider = "aws"
        self.region = None
        self.project = None
        self.network = None
        self.support_package = None
        # self.cluster_size = 3
        self.machine_type = None
        # self.services = []
        self.disk_iops = None
        self.disk_size = None
        self.disk_type = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        cidr_util = NetworkDriver()

        print("")
        in_progress = self.env_cfg.get("capella_base_in_progress")

        if in_progress is not None and in_progress is False:
            print("Cloud settings have been configured")

            self.region = self.env_cfg.get("capella_region")
            self.project = self.env_cfg.get("capella_project")
            self.cluster_name = self.env_cfg.get("capella_cluster_name")
            self.provider = self.env_cfg.get("capella_provider")
            self.network = self.env_cfg.get("capella_network")
            self.single_az = self.env_cfg.get("capella_single_az")
            self.support_package = self.env_cfg.get("capella_support_package")
            print(f"Region          = {self.region}")
            print(f"Project         = {self.project}")
            print(f"Cluster Name    = {self.cluster_name}")
            print(f"Provider        = {self.provider}")
            print(f"Network         = {self.network}")
            print(f"Single AZ       = {self.single_az}")
            print(f"Support Package = {self.support_package}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(capella_base_in_progress=True)

        self.cluster_name = config.env_name
        self.project = f"{self.cluster_name}_project"

        self.provider = Inquire().ask_list_basic("Cloud provider", config.cloud_base().CLOUD_PROVIDER)

        self.single_az = Inquire().ask_bool("Single AZ", recommendation="false")

        self.region = Inquire().ask_list_basic("Cloud region", config.cloud_base(cloud=self.provider).regions)

        for net in config.cloud_network().cidr_list:
            cidr_util.add_network(net)

        self.network = cidr_util.get_next_network()

        self.support_package = Inquire().ask_list_basic("Support package", config.cloud_base().SUPPORT_PACKAGE)

        self.env_cfg.update(capella_region=self.region)
        self.env_cfg.update(capella_project=self.project)
        self.env_cfg.update(capella_cluster_name=self.cluster_name)
        self.env_cfg.update(capella_provider=self.provider)
        self.env_cfg.update(capella_network=self.network)
        self.env_cfg.update(capella_single_az=self.single_az)
        self.env_cfg.update(capella_support_package=self.support_package)
        self.env_cfg.update(capella_base_in_progress=False)

    def get_node_settings(self, default: bool = True):
        in_progress = self.env_cfg.get("capella_node_in_progress")

        print("")
        if in_progress is not None and (in_progress is False or default is False):
            print("Node settings")

            self.instance_type = self.env_cfg.get("capella_machine_type")
            self.disk_type = self.env_cfg.get("capella_root_type")
            self.disk_size = self.env_cfg.get("capella_root_size")
            self.disk_iops = self.env_cfg.get("capella_root_iops")
            print(f"Machine Type = {self.instance_type}")
            print(f"Disk Type    = {self.disk_type}")
            print(f"Disk Size    = {self.disk_size}")
            print(f"Disk IOPS    = {self.disk_iops}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(capella_node_in_progress=True)

        machine_list = config.cloud_machine_type(cloud=self.provider).list()

        selection = Inquire().ask_list_dict("Select machine type", machine_list)
        self.machine_type = selection['name']

        disk_list = config.cloud_machine_type(cloud=self.provider).disk_types()

        selection = Inquire().ask_list_dict("Select disk type", disk_list)
        self.disk_type = selection['type']

        self.disk_size = Inquire().ask_int("Volume size", 250, 100)

        if selection['iops']:
            self.disk_iops = Inquire().ask_int("Volume IOPS", selection['iops'], selection['iops'], selection['max'])

        self.env_cfg.update(capella_machine_type=self.instance_type)
        self.env_cfg.update(capella_root_type=self.disk_type)
        self.env_cfg.update(capella_root_size=self.disk_size)
        self.env_cfg.update(capella_root_iops=self.disk_iops)
        self.env_cfg.update(capella_node_in_progress=False)
