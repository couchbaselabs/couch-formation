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


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cluster_name = None
        self.single_az = True
        self.provider = "aws"
        self.region = None
        self.project = None
        self.network = "10.1.0.0/16"
        self.support_package = "DeveloperPro"
        # self.cluster_size = 3
        # self.machine_type = None
        # self.services = []
        # self.root_volume_iops = "0"
        # self.root_volume_size = "100"
        # self.root_volume_type = "GP3"

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        network_list = []

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
