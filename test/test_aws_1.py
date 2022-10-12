#!/usr/bin/env python3

import os
import sys
import warnings

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.drivers.aws import AWS, AWSValues


def test_aws_driver_1():
    warnings.filterwarnings("ignore")
    driver = AWS()

    vpc_id = driver.create_vpc("10.99.0.0/16")
    sg_id = driver.create_security_group("test-sg", "TestSG", vpc_id)
    sg_list = driver.get_security_group_list(vpc_id)
    vpc_list = driver.get_vpc_list()

    found = False
    for vpc in vpc_list:
        if vpc['VpcId'] == vpc_id:
            found = True
            break
    assert found is True
    found = False
    for sg in sg_list:
        if sg['GroupId'] == sg_id:
            found = True
            break
    assert found is True

    driver.delete_security_group(sg_id)
    driver.delete_vpc(vpc_id)
