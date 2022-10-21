#!/usr/bin/env python3

import warnings
from lib.drivers.aws import AWSInstance, AWSami, AWSSubnet, AWSkey, AWSvpc, AWSSecurityGroup, AWSBase
from lib.drivers.network import NetworkDriver


def test_aws_driver_1():
    warnings.filterwarnings("ignore")
    # driver = CloudDriver()
    network = NetworkDriver()

    for item in AWSvpc().list():
        network.add_network(item['cidr'])

    vpc_cidr = network.get_next_network()
    subnet_list = list(network.get_next_subnet())
    zone_list = AWSBase().zones()

    vpc_id = AWSvpc().create("pytest-vpc", vpc_cidr)
    sg_id = AWSSecurityGroup().create("pytest-sg", "TestSG", vpc_id)
    ssh_key = AWSkey().create("pytest-key")
    subnet_id = AWSSubnet().create("pytest-subnet-01", vpc_id, zone_list[0], subnet_list[1])

    instance = AWSInstance().run("pytest-instance", "ami-0fb653ca2d3203ac1", ssh_key, sg_id, subnet_id)
    ami_id = AWSami().create("pytest-image", instance)

    sg_list = AWSSecurityGroup().list(vpc_id)
    ami_list = AWSami().list()
    new_vpc_list = AWSvpc().list()

    found = False
    for vpc in new_vpc_list:
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

    AWSInstance().terminate(instance)
    AWSami().delete(ami_id)
    AWSSecurityGroup().delete(sg_id)
    AWSSubnet().delete(subnet_id)
    AWSvpc().delete(vpc_id)
    AWSkey().delete(ssh_key)
