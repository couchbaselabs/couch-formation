#!/usr/bin/env -S python3 -W ignore

'''
Couchbase Cluster Manager
'''

import signal
import sys
import os
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.exceptions import *
from lib.args import params
from lib.imagemgr import image_manager
from lib.runmgr import run_manager
from lib.netmgr import network_manager

VERSION = '3.0-alpha-1'
logger = logging.getLogger()


def break_signal_handler(signum, frame):
    print("")
    print("Break received, aborting.")
    sys.exit(1)


class cloud_manager(object):

    def __init__(self, parameters):
        print("CB Environment Manager - version %s" % VERSION)
        self.args = parameters
        self.verb = self.args.command

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


def main():
    global logger
    arg_parser = params()
    parameters = arg_parser.parser.parse_args()
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

    session = cloud_manager(parameters)
    session.run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
