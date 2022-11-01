#!/usr/bin/env python3

import warnings
from lib.drivers.network import NetworkDriver


def test_aws_driver_1():
    warnings.filterwarnings("ignore")
    cidr_util = NetworkDriver()
    module = __import__('lib.drivers.aws')
    driver = module.drivers.aws
    base = getattr(driver, 'CloudBase')
    network = getattr(driver, 'Network')
    subnet = getattr(driver, 'Subnet')
    security_group = getattr(driver, 'SecurityGroup')
    machine_type = getattr(driver, 'MachineType')
    instance = getattr(driver, 'Instance')
    ssh_key = getattr(driver, 'SSHKey')
    image = getattr(driver, 'Image')

    for net in network().cidr_list:
        cidr_util.add_network(net)

    vpc_cidr = cidr_util.get_next_network()
    subnet_list = list(cidr_util.get_next_subnet())
    zone_list = base().zones()

    instance_type_list = machine_type().list()
    assert any(i['name'] == 'm5.large' for i in instance_type_list) is True

    instance_details = machine_type().details('m5.large')
    assert instance_details['name'] == "m5.large"
    assert instance_details['cpu'] == 2
    assert instance_details['memory'] == 8192

    print(f"Network: {vpc_cidr}")
    print(f"Subnet : {subnet_list[1]}")
    print(f"Zone   : {zone_list[0]}")

    vpc_id = network().create("pytest-vpc", vpc_cidr)
    sg_id = security_group().create("pytest-sg", "TestSG", vpc_id)
    ssh_key_name = ssh_key().create("pytest-key")
    subnet_id = subnet().create("pytest-subnet-01", vpc_id, zone_list[0], subnet_list[1])

    instance_id = instance().run("pytest-instance", "ami-0fb653ca2d3203ac1", ssh_key_name, sg_id, subnet_id)
    ami_id = image().create("pytest-image", instance_id)

    sg_list = security_group().list(vpc_id)
    ami_list = image().list()
    new_vpc_list = network().list()

    assert any(i['id'] == vpc_id for i in new_vpc_list) is True

    assert any(i['id'] == sg_id for i in sg_list) is True

    assert any(i['name'] == ami_id for i in ami_list) is True

    instance().terminate(instance_id)
    image().delete(ami_id)
    security_group().delete(sg_id)
    subnet().delete(subnet_id)
    network().delete(vpc_id)
    ssh_key().delete(ssh_key_name)
