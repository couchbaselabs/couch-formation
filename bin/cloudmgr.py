#!/usr/bin/env python3

#
# Couchbase Cluster Manager 3.0
#

import signal
import warnings
from lib.exceptions import *
from lib.args import Parameters
from lib.util.envmgr import LogViewer
from lib.util.namegen import get_random_name
import lib.config as config
from lib.util.envmgr import PathMap, CatalogManager, EnvUtil, CatalogRoot
from lib.util.logging import CustomFormatter

VERSION = '3.0.0-rc1'
warnings.filterwarnings("ignore")
logger = logging.getLogger()


def break_signal_handler(signum, frame):
    print("")
    print("Break received, aborting.")
    sys.exit(1)


class CloudManager(object):

    def __init__(self, parameters):
        self.args = parameters
        self.verb = self.args.command
        config.enable_cloud(self.args.cloud)

    def run(self):
        logger.info(f"Couch Formation ({VERSION})")
        logger.info(f"Cloud Driver {config.cloud.upper()} version {config.cloud_driver_version}")
        logger.info(f"Cloud Operator {config.cloud.upper()} version {config.cloud_operator_version}")

        if self.verb == 'version':
            sys.exit(0)

        if self.args.verbose:
            config.cloud_base().get_info()

        if self.verb == 'image':
            config.env_name = config.cloud
            if self.args.image_command == "build":
                config.catalog_target = CatalogRoot.IMAGE
                config.cloud_operator().create_image()
        elif self.verb == 'create':
            if not config.env_name:
                config.env_name = get_random_name()
            config.cloud_operator().create_nodes(self.args.create_command)
        elif self.verb == 'deploy':
            config.cloud_operator().deploy_nodes(self.args.deploy_command)
        elif self.verb == 'destroy':
            config.cloud_operator().destroy_nodes(self.args.destroy_command)
        elif self.verb == 'remove':
            EnvUtil().env_remove()
        elif self.verb == 'list':
            if self.args.list_command == "images":
                config.env_name = config.cloud
                config.cloud_operator().list_images()
            elif self.args.list_command == "nodes":
                path_map = PathMap(config.env_name, config.cloud)
                cm = CatalogManager(path_map.get_root)
                cm.catalog_list()
        elif self.verb == 'show':
            if self.args.show_command == "nodes":
                config.cloud_operator().show_nodes(self.args.show_node_command)
        elif self.verb == 'net':
            print("Not implemented")
        elif self.verb == 'vpc':
            if self.args.vpc_command == 'create':
                config.cloud_operator().create_net()
            elif self.args.vpc_command == 'destroy':
                config.cloud_operator().destroy_net()
            elif self.args.vpc_command == 'clean':
                config.cloud_operator().clean_net()
        elif self.verb == 'ssh':
            print("Not implemented")
        elif self.verb == 'logs':
            LogViewer(self.args).print_log(lines=self.args.count)
        elif self.verb == 'db':
            if self.args.db_command == "check":
                path_map = PathMap(config.env_name, config.cloud)
                cm = CatalogManager(path_map.get_root)
                cm.check(fix=self.args.fix)


def main():
    global logger
    arg_parser = Parameters()
    arg_parser.update_config()
    parameters = arg_parser.args
    signal.signal(signal.SIGINT, break_signal_handler)

    try:
        if parameters.debug:
            logger.setLevel(logging.DEBUG)

            try:
                open(config.default_debug_file, 'w').close()
            except Exception as err:
                print(f"[!] Warning: can not clear log file {config.default_debug_file}: {err}")

            file_handler = logging.FileHandler(config.default_debug_file)
            file_formatter = logging.Formatter(logging.BASIC_FORMAT)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        elif parameters.verbose or parameters.command == 'version':
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.ERROR)
    except (ValueError, KeyError):
        pass

    screen_handler = logging.StreamHandler()
    screen_handler.setFormatter(CustomFormatter())
    logger.addHandler(screen_handler)

    session = CloudManager(parameters)
    session.run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
