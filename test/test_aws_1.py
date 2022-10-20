#!/usr/bin/env python3

import warnings
from lib.drivers.aws import CloudDriver


def test_aws_driver_1():
    warnings.filterwarnings("ignore")
    driver = CloudDriver()

    vpc_id = driver.create_vpc("pytest-vpc", "10.99.0.0/16")
    sg_id = driver.create_security_group("test-sg", "TestSG", vpc_id)
    ami_id = driver.create_ami("pytest-image", "ami-0fb653ca2d3203ac1")
    sg_list = driver.get_security_group_list(vpc_id)
    vpc_list = driver.get_vpc_list()
    ami_list = driver.get_ami_id()

    found = False
    for vpc in vpc_list:
        if vpc['id'] == vpc_id:
            found = True
            break
    assert found is True

    found = False
    for sg in sg_list:
        if sg['id'] == sg_id:
            found = True
            break
    assert found is True

    found = False
    for ami in ami_list:
        if ami['name'] == ami_id:
            found = True
            break
    assert found is True

    driver.delete_security_group(sg_id)
    driver.delete_vpc(vpc_id)
    driver.delete_ami(ami_id)
