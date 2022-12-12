##
##

import logging
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import AzureDataError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.azure_image import AzureImageDataRecord
from lib.util.cfgmgr import ConfigMgr
from lib.drivers.azure import AzureDiskTypes


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
