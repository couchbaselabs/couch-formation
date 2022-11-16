##
##

import logging
import os
from enum import Enum
from typing import Union


class SSHExtensions(Enum):
    EXT = ".pem"


class FileType(Enum):
    SSH = SSHExtensions.EXT.value


class FileManager(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def absolute_path(self, name: str, file_type: Union[FileType, None] = None) -> str:
        file_name = name
        if file_type:
            file_ext = os.path.splitext(name)
            if len(file_ext[1]) == 0:
                file_name = name + str(file_type.value)

