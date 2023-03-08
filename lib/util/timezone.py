##
##

import logging
import datetime
import pytz
import os


class TimeZone(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.os_timezone = None

    def get_timezone(self):
        local_code = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()
        tzpath = '/etc/localtime'

        if os.path.exists(tzpath) and os.path.islink(tzpath):
            link_path = os.path.realpath(tzpath)
            start = link_path.find("/") + 1
            while start != 0:
                link_path = link_path[start:]
                try:
                    pytz.timezone(link_path)
                    return link_path
                except pytz.UnknownTimeZoneError:
                    pass
                start = link_path.find("/") + 1

        for name in pytz.all_timezones:
            tzone = pytz.timezone(name)
            code = datetime.datetime.now(tzone).tzname()
            if code == local_code:
                self.os_timezone = tzone
                return self.os_timezone
