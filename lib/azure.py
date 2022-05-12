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
import time
from lib.varfile import varfile
from lib.ask import ask
from lib.exceptions import AzureDriverError


class azure(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()

    def azure_get_root_size(self, default=None) -> str:
        """Get Azure root disk size"""
        inquire = ask()

        default_selection = self.vf.azure_get_default('root_size')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', recommendation=default_selection, default=default)
        return selection

    def azure_get_machine_type(self, azure_subscription_id: str, azure_location: str, default=None) -> str:
        """Get Azure Machine Type"""
        inquire = ask()
        size_list = []

        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, azure_subscription_id)
        sizes = compute_client.virtual_machine_sizes.list(azure_location)
        for group in list(sizes):
            config_block = {}
            config_block['name'] = group.name
            config_block['cpu'] = int(group.number_of_cores)
            config_block['mem'] = int(group.memory_in_mb)
            size_list.append(config_block)
        selection = inquire.ask_machine_type('Azure Machine Type', size_list, default=default)
        return size_list[selection]['name']

    def azure_get_image_name(self, azure_subscription_id: str, azure_resource_group: str, select=True, default=None) -> Union[dict, list[dict]]:
        """Get Azure Couchbase Image Name"""
        inquire = ask()
        image_list = []

        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, azure_subscription_id)
        images = compute_client.images.list_by_resource_group(azure_resource_group)
        for group in list(images):
            image_block = {}
            image_block['name'] = group.name
            if 'Type' in group.tags:
                image_block['type'] = group.tags['Type']
            if 'Release' in group.tags:
                image_block['release'] = group.tags['Release']
            if 'Version' in group.tags:
                image_block['version'] = image_block['description'] = group.tags['Version']
            image_list.append(image_block)
        if select:
            selection = inquire.ask_list('Azure Image Name', image_list, default=default)
            return image_list[selection]
        else:
            return image_list

    def azure_delete_image(self, azure_subscription_id: str, azure_resource_group: str, name: str):
        inquire = ask()

        if inquire.ask_yn(f"Delete image {name}", default=True):
            credential = AzureCliCredential()
            compute_client = ComputeManagementClient(credential, azure_subscription_id)
            request = compute_client.images.begin_delete(azure_resource_group, name)
            result = request.result()

    def azure_get_nsg(self, azure_subscription_id: str, azure_resource_group: str, default=None):
        """Get Azure Network Security Group"""
        inquire = ask()
        nsg_list = []

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, azure_subscription_id)
        nsgs = network_client.network_security_groups.list(azure_resource_group)
        for group in list(nsgs):
            nsg_list.append(group.name)
        selection = inquire.ask_list('Azure Network Security Group', nsg_list, default=default)
        return nsg_list[selection]

    def azure_get_availability_zone_list(self, azure_availability_zones: list, azure_subnet: str) -> list[dict]:
        """Build Azure Availability Zone Data structure"""
        availability_zone_list = []

        for zone in azure_availability_zones:
            config_block = {}
            config_block['name'] = zone
            config_block['subnet'] = azure_subnet
            availability_zone_list.append(config_block)
        return availability_zone_list

    def azure_get_subnet(self, azure_subscription_id: str, azure_resource_group: str, azure_vnet: str, default=None) -> str:
        """Get Azure Subnet"""
        inquire = ask()
        subnet_list = []

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, azure_subscription_id)
        subnets = network_client.subnets.list(azure_resource_group, azure_vnet)
        for group in list(subnets):
            subnet_block = {}
            subnet_block['name'] = group.name
            subnet_list.append(subnet_block)
        selection = inquire.ask_list('Azure Subnet', subnet_list, default=default)
        return subnet_list[selection]['name']

    def azure_get_vnet(self, azure_subscription_id: str, azure_resource_group: str, default=None) -> str:
        """Get Azure Virtual Network"""
        inquire = ask()
        vnet_list = []

        credential = AzureCliCredential()
        network_client = NetworkManagementClient(credential, azure_subscription_id)
        vnetworks = network_client.virtual_networks.list(azure_resource_group)
        for group in list(vnetworks):
            vnet_list.append(group.name)
        selection = inquire.ask_list('Azure Virtual Network', vnet_list, default=default)
        return vnet_list[selection]

    def azure_get_all_locations(self, azure_subscription_id: str, default=None) -> str:
        """Get Azure Location from all Locations"""
        inquire = ask()
        location_list = []
        location_name = []

        credential = AzureCliCredential()
        subscription_client = SubscriptionClient(credential)
        locations = subscription_client.subscriptions.list_locations(azure_subscription_id)
        for group in list(locations):
            location_list.append(group.name)
            location_name.append(group.display_name)
        selection = inquire.ask_list('Azure Location', location_list, location_name, default=default)
        return location_list[selection]

    def azure_get_location(self, azure_subscription_id: str, azure_resource_group: str, default=None) -> str:
        """Get Azure Locations by Subscription ID"""
        inquire = ask()
        location_list = []
        location_name = []

        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, azure_subscription_id)
        resource_group = resource_client.resource_groups.list()
        for group in list(resource_group):
            if group.name == azure_resource_group:
                location_list.append(group.location)
        selection = inquire.ask_list('Azure Location', location_list, location_name, default=default)
        return location_list[selection]

    def azure_get_zones(self, azure_subscription_id: str, azure_machine_type: str, azure_location: str) -> list[str]:
        """Get Azure Availability Zone List"""
        azure_availability_zones = []

        print("Fetching Azure zone information, this may take a few minutes...")
        credential = AzureCliCredential()
        compute_client = ComputeManagementClient(credential, azure_subscription_id)
        zone_list = compute_client.resource_skus.list()
        for group in list(zone_list):
            if group.resource_type == 'virtualMachines' \
                    and group.name == azure_machine_type \
                    and group.locations[0].lower() == azure_location.lower():
                for resource_location in group.location_info:
                    for zone_number in resource_location.zones:
                        azure_availability_zones.append(zone_number)
                azure_availability_zones = sorted(azure_availability_zones)
                for zone_number in azure_availability_zones:
                    self.logger.info("Added Azure availability zone %s" % zone_number)
        return azure_availability_zones

    def azure_get_resource_group(self, azure_subscription_id: str, default=None) -> str:
        """Get Azure Resource Group"""
        inquire = ask()
        group_list = []

        if 'AZURE_RESOURCE_GROUP' in os.environ:
            return os.environ['AZURE_RESOURCE_GROUP']

        credential = AzureCliCredential()
        resource_client = ResourceManagementClient(credential, azure_subscription_id)
        groups = resource_client.resource_groups.list()
        for group in list(groups):
            group_list.append(group.name)
        selection = inquire.ask_list('Azure Resource Group', group_list, default=default)
        return group_list[selection]

    def azure_get_subscription_id(self, default=None):
        """Get Azure subscription ID"""
        inquire = ask()
        subscription_list = []
        subscription_name = []

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
        azure_subscription_id = subscription_list[selection]
        self.logger.info("Azure Subscription ID = %s" % azure_subscription_id)
        return azure_subscription_id
