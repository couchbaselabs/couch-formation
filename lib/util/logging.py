##
##

import logging


class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"
    format_level = "%(levelname)s"
    format_name = "%(name)s"
    format_message = "%(message)s"
    format_line = "(%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: f"{grey}{format_level}{reset} - {format_message}",
        logging.INFO: f"{green}{format_level}{reset} - {format_message}",
        logging.WARNING: f"{yellow}{format_level}{reset} - {format_message}",
        logging.ERROR: f"{red}{format_level}{reset} - {format_name} - {format_message} {format_line}",
        logging.CRITICAL: f"{red}{format_level}{reset} - {format_name} - {format_message} {format_line}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
