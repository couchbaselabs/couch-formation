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
import lib.config as config
from lib.config import OperatingMode

VERSION = '3.0a2'
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
        config.process_params(parameters)
        config.enable_cloud(self.args.cloud)

    def run_v3(self):
        if self.verb == 'image':
            print("Not implemented")
        elif self.verb == 'create':
            print("Not implemented")
        elif self.verb == 'deploy':
            print("Not implemented")
        elif self.verb == 'destroy':
            print("Not implemented")
        elif self.verb == 'remove':
            print("Not implemented")
        elif self.verb == 'remove':
            print("Not implemented")
        elif self.verb == 'list':
            print("Not implemented")
        elif self.verb == 'net':
            print("Not implemented")
        elif self.verb == 'vpc':
            if config.operating_mode == OperatingMode.CREATE.value:
                config.cloud_operator().create_net()
            elif config.operating_mode == OperatingMode.DESTROY.value:
                config.cloud_operator().destroy_net()
        elif self.verb == 'ssh':
            print("Not implemented")

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


def main():
    global logger
    arg_parser = Parameters()
    parameters = arg_parser.args
    signal.signal(signal.SIGINT, break_signal_handler)

    try:
        debug_level = int(os.environ['CF_DEBUG_LEVEL'])
        logging.basicConfig()
        if debug_level == 0:
            logger.setLevel(logging.DEBUG)
        elif debug_level == 1:
            logger.setLevel(logging.INFO)
        elif debug_level == 2:
            logger.setLevel(logging.ERROR)
        else:
            logger.setLevel(logging.CRITICAL)
    except (ValueError, KeyError):
        pass

    session = CloudManager(parameters)
    if config.env_name:
        session.run_v3()
    else:
        session.run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
