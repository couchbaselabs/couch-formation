##
##

import logging


class CloudValues(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)


class CloudDriver(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_image(self):
        pass

    def create_env(self):
        pass
