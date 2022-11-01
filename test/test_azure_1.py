#!/usr/bin/env python3

import warnings
from lib.drivers.azure import AZBase, AZNetwork, AZSubnet, AZMachineType
from lib.drivers.network import NetworkDriver


def test_azure_driver_1():
    warnings.filterwarnings("ignore")
    network = NetworkDriver()

    for item in AZNetwork().list():
        for net in item['cidr']:
            network.add_network(net)

    vpc_cidr = network.get_next_network()
    subnet_list = list(network.get_next_subnet())
    zone_list = AZBase().zones()

    instance_type_list = AZMachineType().list()
    assert any(i['name'] == 'Standard_D2_v4' for i in instance_type_list) is True

    instance_details = AZMachineType().details('Standard_D2_v4')
    assert instance_details['name'] == "Standard_D2_v4"
    assert instance_details['cpu'] == 2
    assert instance_details['memory'] == 8192

    # vpc_id = AWSvpc().create("pytest-vpc", vpc_cidr)
    # sg_id = AWSSecurityGroup().create("pytest-sg", "TestSG", vpc_id)
    # ssh_key = AWSkey().create("pytest-key")
    # subnet_id = AWSSubnet().create("pytest-subnet-01", vpc_id, zone_list[0], subnet_list[1])
    #
    # instance = AWSInstance().run("pytest-instance", "ami-0fb653ca2d3203ac1", ssh_key, sg_id, subnet_id)
    # ami_id = AWSami().create("pytest-image", instance)
    #
    # sg_list = AWSSecurityGroup().list(vpc_id)
    # ami_list = AWSami().list()
    # new_vpc_list = AWSvpc().list()
    #
    # assert any(i['id'] == vpc_id for i in new_vpc_list) is True
    #
    # assert any(i['id'] == sg_id for i in sg_list) is True
    #
    # assert any(i['name'] == ami_id for i in ami_list) is True
    #
    # AWSInstance().terminate(instance)
    # AWSami().delete(ami_id)
    # AWSSecurityGroup().delete(sg_id)
    # AWSSubnet().delete(subnet_id)
    # AWSvpc().delete(vpc_id)
    # AWSkey().delete(ssh_key)
