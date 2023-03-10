#!/usr/bin/env python3

import warnings
from lib.drivers.network import NetworkDriver


def test_azure_driver_1():
    warnings.filterwarnings("ignore")
    cidr_util = NetworkDriver()
    module = __import__('lib.drivers.azure')
    driver = module.drivers.azure
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
    azure_location = base().region

    instance_type_list = machine_type().list()
    assert any(i['name'] == 'Standard_D2_v4' for i in instance_type_list) is True

    instance_details = machine_type().details('Standard_D2_v4')
    assert instance_details['name'] == "Standard_D2_v4"
    assert instance_details['cpu'] == 2
    assert instance_details['memory'] == 8192

    print(f"Network: {vpc_cidr}")
    print(f"Subnet : {subnet_list[1]}")
    print(f"Zone   : {zone_list[0]}")

    azure_rg_struct = base().create_rg("pytest-rg", azure_location)
    if not azure_rg_struct.get('name'):
        raise Exception(f"resource group creation failed")
    azure_rg = azure_rg_struct['name']

    network_name = network().create("pytest-vpc", vpc_cidr, azure_rg)
    sg_name = security_group().create("pytest-sg", azure_rg)
    ssh_key = ssh_key().public_key("mminichino-default-key-pair")
    subnet_name = subnet().create("pytest-subnet-01", network_name, subnet_list[1], sg_name, azure_rg)

    instance_name = instance().run("pytest-instance",
                                   ("Canonical", "0001-com-ubuntu-server-focal", "20_04-lts"),
                                   zone_list[0],
                                   network_name,
                                   subnet_name,
                                   "ubuntu",
                                   ssh_key,
                                   machine_type="Standard_D2_v4",
                                   resource_group=azure_rg)

    image_name = image().create("pytest-image",
                                instance_name,
                                resource_group=azure_rg)

    sg_list = security_group().list(azure_rg)
    image_list = image().list(resource_group=azure_rg)
    new_vpc_list = network().list(azure_rg)

    assert any(i['name'] == network_name for i in new_vpc_list) is True

    assert any(i['name'] == sg_name for i in sg_list) is True

    assert any(i['name'] == image_name for i in image_list) is True

    instance().terminate(instance_name, resource_group=azure_rg)
    image().delete(image_name, resource_group=azure_rg)
    subnet().delete(network_name, subnet_name, resource_group=azure_rg)
    security_group().delete(sg_name, resource_group=azure_rg)
    network().delete(network_name, resource_group=azure_rg)
    base().delete_rg("pytest-rg")
