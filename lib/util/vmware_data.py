##
##

import logging
import time

from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import VMWareDataError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.vmware_image import VMWareImageDataRecord
from lib.util.cfgmgr import ConfigMgr


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vmware_hostname = None
        self.vmware_username = None
        self.vmware_password = None
        self.vmware_datacenter = None
        self.vmware_dc_folder = None
        self.vmware_network_folder = None
        self.vmware_host_folder = None

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)
