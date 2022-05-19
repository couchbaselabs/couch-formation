#!/usr/bin/env -S python3 -W ignore

import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.azure import azure


def main():
    driver = azure()
    driver.azure_init()
    # driver.azure_get_availability_zone_list()
    driver.azure_get_subnet()

if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
