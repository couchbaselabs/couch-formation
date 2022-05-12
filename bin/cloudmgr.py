#!/usr/bin/env -S python3 -W ignore

'''
Couchbase Cluster Manager
'''

import signal
import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.exceptions import *
from lib.args import params
from lib.imagemgr import image_manager

VERSION = '2.0-alpha-1'


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
            sys.exit(0)
        elif self.verb == 'create':
            sys.exit(0)
        elif self.verb == 'destroy':
            sys.exit(0)
        elif self.verb == 'list':
            sys.exit(0)


def main():
    arg_parser = params()
    parameters = arg_parser.parser.parse_args()
    signal.signal(signal.SIGINT, break_signal_handler)

    session = cloud_manager(parameters)
    session.run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
