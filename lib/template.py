##
##

import logging


class template(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

