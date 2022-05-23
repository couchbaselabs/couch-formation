##
##

import logging
import os


class log_file(object):

    def __init__(self, name, path=None, filename=None, level=None, overwrite=True):
        if filename:
            self.default_debug_file = path + '/' + filename if path else filename
        else:
            self.default_debug_file = path + '/deploy.log' if path else 'deploy.log'
        self.debug_file = os.environ.get("CLOUD_MGR_DEBUG_FILE", self.default_debug_file)
        self._logger = logging.getLogger(name)
        self.handler = logging.FileHandler(self.debug_file)
        self.formatter = logging.Formatter(logging.BASIC_FORMAT)
        self.handler.setFormatter(self.formatter)
        self.debug = False
        default_level = 3

        if overwrite:
            try:
                open(self.debug_file, 'w').close()
            except Exception as err:
                print(f"warning: can not clear log file {self.debug_file}: {err}")

        try:
            default_level = int(os.environ['CLOUD_MGR_DEBUG_FILE']) if 'CLOUD_MGR_DEBUG_FILE' in os.environ else 1
        except ValueError:
            print(f"warning: ignoring logging: environment variable CLOUD_MGR_DEBUG_FILE should be a number")

        self.debug_level = level if level else default_level

        try:
            if overwrite:
                open(self.debug_file, 'w').close()

            if self.debug_level == 0:
                self._logger.setLevel(logging.DEBUG)
            elif self.debug_level == 1:
                self._logger.setLevel(logging.INFO)
            elif self.debug_level == 2:
                self._logger.setLevel(logging.ERROR)
            else:
                self._logger.setLevel(logging.CRITICAL)

            self._logger.addHandler(self.handler)
            self.debug = True
        except Exception as err:
            print(f"warning: can not initialize logging: {err}")

    @property
    def logger(self):
        return self._logger
