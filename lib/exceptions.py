##
##

import sys
import os
import inspect


class fatalError(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        print("Error: {} in {} {} at line {}: {}".format(type(self).__name__, filename, function, line, message))
        sys.exit(1)


class nonFatalError(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = "Error: {} in {} {} at line {}: {}".format(
            type(self).__name__, filename, function, line, message)
        super().__init__(self.message)


class DirectoryStructureError(fatalError):
    pass


class VarFileError(fatalError):
    pass


class PackerRunError(fatalError):
    pass


class TerraformRunError(fatalError):
    pass


class ImageMgmtError(fatalError):
    pass


class RunMgmtError(fatalError):
    pass


class SSHError(fatalError):
    pass


class ImageNameFormatError(fatalError):
    pass


class AWSDriverError(fatalError):
    pass


class GCPDriverError(fatalError):
    pass


class AzureDriverError(fatalError):
    pass


class VMwareDriverError(fatalError):
    pass


class ToolboxError(fatalError):
    pass


class TemplateError(fatalError):
    pass


class EnvMgrError(fatalError):
    pass


class ClusterMgrError(fatalError):
    pass


class NetworkMgrError(fatalError):
    pass


class TFGenError(fatalError):
    pass

