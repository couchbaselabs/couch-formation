#!/usr/bin/env -S python3 -W ignore

import os
import sys
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib import invoke
from lib.envmgr import envmgr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packer', action='store_true')
    parser.add_argument('--tf', action='store_true')
    args = parser.parse_args()

    if args.tf:
        env = envmgr()
        env.set_env(99, None, None, 1, 1)
        env.set_cloud('aws')
        env_text = env.get_env
        env_text = env_text.replace(':', '-')
        print(f"Creating test environment {env_text}...")
        env.create_env(overwrite=True)

        print("Deleting test environment ...")
        env.remove_env()

    if args.packer:
        pr = invoke.packer_run()
    else:
        tf = invoke.tf_run()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
