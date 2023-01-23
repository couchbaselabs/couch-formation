##
##

import sys
import os
import inspect
import logging


class FatalError(Exception):

    def __init__(self, message):
        import traceback
        logging.debug(traceback.print_exc())
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        logging.debug("Error: {} in {} {} at line {}: {}".format(type(self).__name__, filename, function, line, message))
        logging.error(f"{message} [{filename}:{line}]")
        sys.exit(1)


class NonFatalError(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = "Error: {} in {} {} at line {}: {}".format(
            type(self).__name__, filename, function, line, message)
        super().__init__(self.message)


class DirectoryStructureError(FatalError):
    pass


class VarFileError(FatalError):
    pass


class PackerRunError(FatalError):
    pass


class TerraformRunError(FatalError):
    pass


class ImageMgmtError(FatalError):
    pass


class RunMgmtError(FatalError):
    pass


class SSHError(FatalError):
    pass


class ImageNameFormatError(FatalError):
    pass


class AWSDriverError(FatalError):
    pass


class GCPDriverError(FatalError):
    pass


class AzureDriverError(FatalError):
    pass


class VMwareDriverError(FatalError):
    pass


class ToolboxError(FatalError):
    pass


class TemplateError(FatalError):
    pass


class EnvMgrError(FatalError):
    pass


class ClusterMgrError(FatalError):
    pass


class NetworkMgrError(FatalError):
    pass


class TFGenError(FatalError):
    pass


class CBReleaseManagerError(FatalError):
    pass


class EmptyResultSet(NonFatalError):
    pass


class MissingParameterError(FatalError):
    pass


class FileManagerError(FatalError):
    pass


class ConfigManagerError(FatalError):
    pass


class AWSDataError(FatalError):
    pass


class GCPDataError(FatalError):
    pass


class AzureDataError(FatalError):
    pass


class CapellaDriverError(FatalError):
    pass


class CatalogInvalid(FatalError):
    pass


class CapellaMissingSecretKey(FatalError):
    pass


class CapellaMissingAuthKey(FatalError):
    pass


class CapellaNotAuthorized(FatalError):
    pass


class CapellaForbidden(FatalError):
    pass


class CapellaNotImplemented(FatalError):
    pass


class CapellaRequestValidationError(FatalError):
    pass


class CapellaInternalServerError(FatalError):
    pass
