##
##

import logging
import os
from enum import Enum
from typing import Union

HOME_DIRECTORY = os.path.expanduser('~')

SSH_PATHS = [
    HOME_DIRECTORY + '/.ssh',
    HOME_DIRECTORY,
    HOME_DIRECTORY + '/Documents',
    HOME_DIRECTORY + '/Downloads'
]


class SSHExtensions(Enum):
    EXT = ".pem"


class FileType(Enum):
    SSH = SSHExtensions.EXT.value


class FileManager(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def ssh_key_absolute_path(name: str) -> Union[str, None]:
        file_ext = os.path.splitext(name)
        if len(file_ext[1]) == 0:
            file_name = name + str(FileType.SSH.value)
        else:
            file_name = name

        for location in SSH_PATHS:
            for file_found in os.listdir(location):
                if file_found == file_name:
                    absolute_path = location + '/' + file_found
                    return absolute_path

        return None
