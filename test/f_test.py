#!/usr/bin/env -S python3 -W ignore

import os
import sys
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.netmgr import network_manager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--domain', action='store')
    parser.add_argument('--cloud', action='store', default='aws')
    args = parser.parse_args()

    nm = network_manager(args)
    nm.load_domain(select=False)
    nm.load_network(select=False)

    domain = nm.get_domain_name()
    servers = nm.get_dns_server_list()
    print(f"{domain}")
    print(f"{servers}")
    cidr = nm.get_network_cidr()
    mask = nm.get_network_mask()
    gateway = nm.get_network_gateway()
    omit = nm.get_network_omit()
    print(f"{cidr}")
    print(f"{mask}")
    print(f"{gateway}")
    print(f"{omit}")


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
