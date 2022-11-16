#!/usr/bin/env python3

import warnings
from lib.drivers.network import NetworkDriver


def test_gcp_driver_1():
    warnings.filterwarnings("ignore")
    cidr_util = NetworkDriver()
    module = __import__('lib.drivers.gcp')
    driver = module.drivers.gcp
    base = getattr(driver, 'CloudBase')
    network = getattr(driver, 'Network')
    subnet = getattr(driver, 'Subnet')
    # security_group = getattr(driver, 'SecurityGroup')
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
    assert any(i['name'] == 'n2-standard-2' for i in instance_type_list) is True

    instance_details = machine_type().details('n2-standard-2')
    assert instance_details['name'] == "n2-standard-2"
    assert instance_details['cpu'] == 2
    assert instance_details['memory'] == 8192

    print(f"Network: {vpc_cidr}")
    print(f"Subnet : {subnet_list[1]}")
    print(f"Zone   : {zone_list[0]}")

    network_name = network().create("pytest-vpc")
    # sg_id = AWSSecurityGroup().create("pytest-sg", "TestSG", vpc_id)
    ssh_key = ssh_key().public_key("mminichino-default-key-pair")
    subnet_name = subnet().create("pytest-subnet-01", network_name, subnet_list[1])

    instance_name = instance().run("pytest-instance", "ubuntu-2004-focal-v20220110", zone_list[0], network_name, subnet_name, ssh_key)
    image_name = image().create("pytest-image", "ubuntu-2004-focal-v20220110")

    # sg_list = AWSSecurityGroup().list(vpc_id)
    image_list = image().list()
    new_vpc_list = network().list()

    assert any(i['name'] == network_name for i in new_vpc_list) is True

    # assert any(i['id'] == sg_id for i in sg_list) is True

    assert any(i['name'] == image_name for i in image_list) is True

    instance().terminate(instance_name, zone_list[0])
    image().delete(image_name)
    # AWSSecurityGroup().delete(sg_id)
    subnet().delete(subnet_name)
    network().delete(network_name)
