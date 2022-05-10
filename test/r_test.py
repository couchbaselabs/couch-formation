#!/usr/bin/env -S python3 -W ignore

import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib import invoke


def main():
    pr = invoke.packer_run()
    pr.build('/Users/michaelminichino/IdeaProjects/terraform-couchbase/aws/packer', 'centos-8.pkrvars.hcl', 'linux.pkr.hcl')


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
