##
##

import logging
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from typing import Union
import os
from lib.varfile import varfile
from lib.ask import ask
from lib.exceptions import AzureDriverError
from lib.prereq import prereq


class azure(object):
    VARIABLES = [
        ('AZURE_DISK_SIZE', 'azure_disk_size', 'azure_get_root_size', None),
        ('AZURE_DISK_TYPE', 'azure_disk_type', 'azure_get_root_type', None),
        ('AZURE_IMAGE_NAME', 'azure_image_name', 'azure_get_image_name', None),
        ('AZURE_LOCATION', 'azure_location', 'azure_get_location', None),
        ('AZURE_MACHINE_TYPE', 'azure_machine_type', 'azure_get_machine_type', None),
        ('AZURE_NSG', 'azure_nsg', 'azure_get_nsg', None),
        ('AZURE_RG', 'azure_resource_group', 'azure_get_resource_group', None),
        ('AZURE_SUBNET', 'azure_subnet', 'azure_get_subnet', None),
        ('AZURE_SUBSCRIPTION_ID', 'azure_subscription_id', 'azure_get_subscription_id', None),
        ('AZURE_VNET', 'azure_vnet', 'azure_get_vnet', None),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()
        self.azure_subscription_id = None
        self.azure_resource_group = None
        self.azure_location = None
        self.azure_subnet = None
        self.azure_vnet = None
        self.azure_availability_zones = []
        self.azure_vnet = None
        self.azure_subnet_id = None
        self.azure_nsg = None
        self.azure_image_name = None
        self.azure_machine_type = None
        self.azure_disk_type = None
        self.azure_disk_size = None

    def azure_init(self):
        try:
            self.azure_get_subscription_id()
            self.azure_get_resource_group()
        except Exception as err:
            raise AzureDriverError(f"can not connect to Azure API: {err}")

    def azure_prep(self):
        try:
            self.azure_get_location()
        except Exception as err:
            raise AzureDriverError(f"Azure prep error: {err}")

    def azure_get_root_size(self, default=None, write=None) -> str:
        """Get Azure root disk size"""
        inquire = ask()

        if write:
            self.azure_disk_size = write
            return self.azure_disk_size

        if self.azure_disk_size:
            return self.azure_disk_size

        default_selection = self.vf.azure_get_default('root_size')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', recommendation=default_selection, default=default)
        self.azure_disk_size = selection
        return self.azure_disk_size

    def azure_get_root_type(self, default=None, write=None) -> str:
        """Get Azure root disk size"""
        inquire = ask()
        azure_type_list = [
            'Standard_LRS',
            'StandardSSD_ZRS',
            'Premium_LRS',
            'Premium_ZRS',
            'StandardSSD_LRS',
            'UltraSSD_LRS'
        ]

        if write:
            self.azure_disk_type = write
            return self.azure_disk_type

        if self.azure_disk_type:
            return self.azure_disk_type

        default_selection = self.vf.azure_get_default('root_type')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_list('Root volume type', azure_type_list, default=default_selection)
        self.azure_disk_type = azure_type_list[selection]
        return self.azure_disk_type

    def azure_get_machine_type(self, default=None, write=None) -> str:
        """Get Azure Machine Type"""
        inquire = ask()
        size_list = []

        if write:
            self.azure_machine_type = write
            return self.azure_machine_type

        if self.azure_machine_type:
            return self.azure_machine_type

        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        sizes = compute_client.virtual_machine_sizes.list(self.azure_location)
        for group in list(sizes):
            config_block = {}
            config_block['name'] = group.name
            config_block['cpu'] = int(group.number_of_cores)
            config_block['mem'] = int(group.memory_in_mb)
            size_list.append(config_block)
        selection = inquire.ask_machine_type('Azure Machine Type', size_list, default=default)
        self.azure_machine_type = size_list[selection]['name']
        return self.azure_machine_type

    def azure_get_image_name(self, select=True, default=None, write=None) -> Union[dict, list[dict]]:
        """Get Azure Couchbase Image Name"""
        inquire = ask()
        image_list = []

        if write:
            self.azure_image_name = write
            return self.azure_image_name

        if self.azure_image_name:
            return self.azure_image_name

        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        images = compute_client.images.list_by_resource_group(self.azure_resource_group)
        for group in list(images):
            image_block = {}
            image_block['name'] = group.name
            if 'Type' in group.tags:
                image_block['type'] = group.tags['Type']
            if 'Release' in group.tags:
                image_block['release'] = group.tags['Release']
            if 'Version' in group.tags:
                image_block['version'] = image_block['description'] = group.tags['Version']
            if 'type' not in image_block or 'release' not in image_block:
                continue
            image_list.append(image_block)
        if select:
            selection = inquire.ask_list('Azure Image Name', image_list, default=default)
            self.azure_image_name = image_list[selection]
        else:
            self.azure_image_name = image_list

        return self.azure_image_name

    @prereq(requirements=('azure_get_image_name',))
    def get_image(self):
        return self.azure_image_name

    def azure_delete_image(self, name: str):
        inquire = ask()

        if inquire.ask_yn(f"Delete image {name}", default=True):
            credential = AzureCliCredential()
            compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
            request = compute_client.images.begin_delete(self.azure_resource_group, name)
            result = request.result()

    def azure_get_nsg(self, default=None, write=None):
        """Get Azure Network Security Group"""
        inquire = ask()
        nsg_list = []

        if write:
            self.azure_nsg = write
            return self.azure_nsg

        if self.azure_nsg:
            return self.azure_nsg

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        nsgs = network_client.network_security_groups.list(self.azure_resource_group)
        for group in list(nsgs):
            nsg_list.append(group.name)
        selection = inquire.ask_list('Azure Network Security Group', nsg_list, default=default)
        self.azure_nsg = nsg_list[selection]
        return self.azure_nsg

    @prereq(requirements=('azure_get_subnet', 'azure_get_zones'))
    def azure_get_availability_zone_list(self) -> list[dict]:
        """Build Azure Availability Zone Data structure"""
        availability_zone_list = []

        for zone in self.azure_availability_zones:
            config_block = {}
            config_block['name'] = zone
            config_block['subnet'] = self.azure_subnet
            availability_zone_list.append(config_block)
        return availability_zone_list

    @prereq(requirements=('azure_get_vnet',))
    def azure_get_subnet(self, default=None, write=None) -> str:
        """Get Azure Subnet"""
        inquire = ask()
        subnet_list = []

        if write:
            self.azure_subnet = write
            return self.azure_subnet

        if self.azure_subnet:
            return self.azure_subnet

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        subnets = network_client.subnets.list(self.azure_resource_group, self.azure_vnet)
        for group in list(subnets):
            subnet_block = {}
            subnet_block['name'] = group.name
            subnet_list.append(subnet_block)
        selection = inquire.ask_list('Azure Subnet', subnet_list, default=default)
        self.azure_subnet = subnet_list[selection]['name']
        return self.azure_subnet

    def azure_get_vnet(self, default=None, write=None) -> str:
        """Get Azure Virtual Network"""
        inquire = ask()
        vnet_list = []

        if write:
            self.azure_vnet = write
            return self.azure_vnet

        if self.azure_vnet:
            return self.azure_vnet

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, self.azure_subscription_id)
        vnetworks = network_client.virtual_networks.list(self.azure_resource_group)
        for group in list(vnetworks):
            vnet_list.append(group.name)
        selection = inquire.ask_list('Azure Virtual Network', vnet_list, default=default)
        self.azure_vnet = vnet_list[selection]
        return self.azure_vnet

    def azure_get_all_locations(self, default=None, write=None) -> str:
        """Get Azure Location from all Locations"""
        inquire = ask()
        location_list = []
        location_name = []

        if write:
            self.azure_location = write
            return self.azure_location

        if self.azure_location:
            return self.azure_location

        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        locations = subscription_client.subscriptions.list_locations(self.azure_subscription_id)
        for group in list(locations):
            location_list.append(group.name)
            location_name.append(group.display_name)
        selection = inquire.ask_list('Azure Location', location_list, location_name, default=default)
        self.azure_location = location_list[selection]
        return self.azure_location

    def azure_get_location(self, default=None, write=None) -> str:
        """Get Azure Locations by Subscription ID"""
        inquire = ask()
        location_list = []
        location_name = []

        if write:
            self.azure_location = write
            return self.azure_location

        if self.azure_location:
            return self.azure_location

        if 'AZURE_DEFAULT_REGION' in os.environ:
            self.azure_location = os.environ['AZURE_DEFAULT_REGION']
            return os.environ['AZURE_DEFAULT_REGION']

        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, self.azure_subscription_id)
        resource_group = resource_client.resource_groups.list()
        for group in list(resource_group):
            if group.name == self.azure_resource_group:
                location_list.append(group.location)
        selection = inquire.ask_list('Azure Location', location_list, location_name, default=default)
        self.azure_location = location_list[selection]
        return self.azure_location

    @prereq(requirements=('azure_get_machine_type',))
    def azure_get_zones(self) -> list[str]:
        """Get Azure Availability Zone List"""

        if len(self.azure_availability_zones) > 0:
            return self.azure_availability_zones

        print("Fetching Azure zone information, this may take a few minutes...")
        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, self.azure_subscription_id)
        zone_list = compute_client.resource_skus.list()
        for group in list(zone_list):
            if group.resource_type == 'virtualMachines' \
                    and group.name == self.azure_machine_type \
                    and group.locations[0].lower() == self.azure_location.lower():
                for resource_location in group.location_info:
                    for zone_number in resource_location.zones:
                        self.azure_availability_zones.append(zone_number)
                self.azure_availability_zones = sorted(self.azure_availability_zones)
                for zone_number in self.azure_availability_zones:
                    self.logger.info("Added Azure availability zone %s" % zone_number)
        return self.azure_availability_zones

    def azure_get_resource_group(self, default=None, write=None) -> str:
        """Get Azure Resource Group"""
        inquire = ask()
        group_list = []

        if write:
            self.azure_resource_group = write
            return self.azure_resource_group

        if self.azure_resource_group:
            return self.azure_resource_group

        if 'AZURE_RESOURCE_GROUP' in os.environ:
            self.azure_resource_group = os.environ['AZURE_RESOURCE_GROUP']
            return self.azure_resource_group

        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, self.azure_subscription_id)
        groups = resource_client.resource_groups.list()
        for group in list(groups):
            group_list.append(group.name)
        selection = inquire.ask_list('Azure Resource Group', group_list, default=default)
        self.azure_resource_group = group_list[selection]
        return self.azure_resource_group

    def azure_get_subscription_id(self, default=None, write=None):
        """Get Azure subscription ID"""
        inquire = ask()
        subscription_list = []
        subscription_name = []

        if write:
            self.azure_subscription_id = write
            return self.azure_subscription_id

        if self.azure_subscription_id:
            return self.azure_subscription_id

        try:
            credential = AzureCliCredential()
            subscription_client = SubscriptionClient(credential)
            subscriptions = subscription_client.subscriptions.list()
        except Exception as err:
            raise AzureDriverError(f"Azure: unauthorized (use az login): {err}")

        for group in list(subscriptions):
            subscription_list.append(group.subscription_id)
            subscription_name.append(group.display_name)
        selection = inquire.ask_list('Azure Subscription ID', subscription_list, subscription_name, default=default)
        self.azure_subscription_id = subscription_list[selection]
        self.logger.info("Azure Subscription ID = %s" % self.azure_subscription_id)
        return self.azure_subscription_id
