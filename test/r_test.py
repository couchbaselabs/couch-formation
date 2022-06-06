#!/usr/bin/env -S python3 -W ignore

import os
import sys
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib import invoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packer', action='store_true')
    parser.add_argument('--tf', action='store')
    args = parser.parse_args()

    if args.packer:
        pr = invoke.packer_run()
    else:
        tf = invoke.tf_run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
