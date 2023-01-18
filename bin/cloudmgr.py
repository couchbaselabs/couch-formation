#!/usr/bin/env python3

#
# Couchbase Cluster Manager
#

import signal
import warnings
import logging
from lib.exceptions import *
from lib.args import Parameters
from lib.imagemgr import image_manager
from lib.runmgr import run_manager
from lib.netmgr import network_manager
from lib.util.envmgr import LogViewer
from lib.util.namegen import get_random_name
import lib.config as config
from lib.config import OperatingMode
from lib.util.envmgr import PathMap, CatalogManager
from lib.util.logging import CustomFormatter

VERSION = '3.0.0-a4'
warnings.filterwarnings("ignore")
logger = logging.getLogger()


def break_signal_handler(signum, frame):
    print("")
    print("Break received, aborting.")
    sys.exit(1)


class CloudManager(object):

    def __init__(self, parameters):
        print(f"Couch Formation ({VERSION})")
        self.args = parameters
        self.verb = self.args.command
        # config.process_params(parameters)
        config.enable_cloud(self.args.cloud)

    def run_v3(self):
        if self.verb == 'image':
            config.env_name = config.cloud
            if config.operating_mode == OperatingMode.BUILD.value:
                config.cloud_operator().create_image()
        elif self.verb == 'create':
            if not config.env_name:
                config.env_name = get_random_name()
            config.cloud_operator().create_nodes(self.args.create_command)
        elif self.verb == 'deploy':
            print("Not implemented")
        elif self.verb == 'destroy':
            config.cloud_operator().destroy_nodes(self.args.destroy_command)
        elif self.verb == 'remove':
            print("Not implemented")
        elif self.verb == 'remove':
            print("Not implemented")
        elif self.verb == 'list':
            if self.args.list_command == "images":
                config.env_name = config.cloud
                config.cloud_operator().list_images()
        elif self.verb == 'show':
            if self.args.show_command == "nodes":
                config.cloud_operator().show_nodes(self.args.show_node_command)
        elif self.verb == 'net':
            print("Not implemented")
        elif self.verb == 'vpc':
            if config.operating_mode == OperatingMode.CREATE.value:
                config.cloud_operator().create_net()
            elif config.operating_mode == OperatingMode.DESTROY.value:
                config.cloud_operator().destroy_net()
        elif self.verb == 'ssh':
            print("Not implemented")
        elif self.verb == 'logs':
            LogViewer(self.args).print_log(lines=self.args.count)
        elif self.verb == 'db':
            if self.args.db_command == "check":
                path_map = PathMap(config.env_name, config.cloud)
                cm = CatalogManager(path_map.get_root)
                cm.check(fix=self.args.fix)

    def run(self):
        if self.verb == 'image':
            task = image_manager(self.args)
            if self.args.list:
                task.list_images()
            elif self.args.delete:
                task.delete_images()
            elif self.args.build:
                task.build_images()
            sys.exit(0)
        elif self.verb == 'create':
            task = run_manager(self.args)
            task.build_env()
            sys.exit(0)
        elif self.verb == 'deploy':
            task = run_manager(self.args)
            task.deploy_env()
            sys.exit(0)
        elif self.verb == 'destroy':
            task = run_manager(self.args)
            task.destroy_env()
            sys.exit(0)
        elif self.verb == 'remove':
            task = run_manager(self.args)
            task.remove_env()
            sys.exit(0)
        elif self.verb == 'list':
            task = run_manager(self.args)
            if self.args.all:
                task.list_all()
            else:
                task.list_env()
            sys.exit(0)
        elif self.verb == 'net':
            task = network_manager(self.args)
            if self.args.list:
                task.list_data()
            elif self.args.domain:
                task.add_domain()
            elif self.args.cidr:
                task.add_network()
            sys.exit(0)
        elif self.verb == 'vpc':
            print("Not implemented")
        elif self.verb == 'ssh':
            print("Not implemented")
        elif self.verb == 'logs':
            LogViewer(self.args).print_log(lines=self.args.count)


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
        elif parameters.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.ERROR)
    except (ValueError, KeyError):
        pass

    screen_handler = logging.StreamHandler()
    screen_handler.setFormatter(CustomFormatter())
    logger.addHandler(screen_handler)

    session = CloudManager(parameters)
    session.run_v3()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
