##
##

import sys
import os
import inspect


class capellaError(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        print("Error: {} in {} {} at line {}: {}".format(type(self).__name__, filename, function, line, message))
        sys.exit(1)


class capellaException(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = "Error: {} in {} {} at line {}: {}".format(
            type(self).__name__, filename, function, line, message)
        super().__init__(self.message)


class CapellaMissingAuthKey(capellaError):
    pass


class CapellaMissingSecretKey(capellaError):
    pass


class CapellaMissingClusterName(capellaError):
    pass


class CapellaHTTPException(capellaException):
    pass


class CapellaGeneralError(capellaError):
    pass


class CapellaNotAuthorized(capellaError):
    pass


class CapellaRequestValidationError(capellaException):
    pass


class CapellaInternalServerError(capellaException):
    pass


class CapellaClusterNotFound(capellaError):
    pass


class CapellaConnectException(capellaException):
    pass


class CapellaNotImplemented(capellaError):
    pass

