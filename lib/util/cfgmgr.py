##
##

import logging


class EnvConfig(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
