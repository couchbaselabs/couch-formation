#!/usr/bin/env -S python3 -W ignore

import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.vmware import vmware


def main():
    driver = vmware()
    driver.vmware_get_build_pwd_encrypted()


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
