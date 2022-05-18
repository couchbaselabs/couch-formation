#!/usr/bin/env -S python3 -W ignore

import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.vmware import vmware


class Common(object):

    def __init__(self):
        self.data = 2


class First(object):

    def __init__(self, common):
        self.first = 1
        common.data = 3


class Second(object):

    def __init__(self, common):
        self.second = 2
        common.data = 4


def main():
    test = Common()
    f = First(test)
    print(test.data)
    s = Second(test)
    print(test.data)


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
