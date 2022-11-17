##
##

import logging
import os
import configparser
from typing import Union
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from itertools import cycle
from lib.exceptions import AzureDriverError
import lib.config as config


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = True

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auth_directory = os.environ['HOME'] + '/.azure'
        self.config_default = self.auth_directory + '/clouds.config'
        self.config_main = self.auth_directory + '/config'
        self.cloud_name = 'AzureCloud'
        self.local_context = None
        self.azure_subscription_id = None
        self.credential = None
        self.azure_resource_group = None
        self.azure_location = None
        self.azure_availability_zones = []
        self.azure_zone = None

        self.read_config()

        if 'AZURE_SUBSCRIPTION_ID' in os.environ:
            self.azure_subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        elif not self.azure_subscription_id:
            try:
                self.credential = AzureCliCredential()
                self.subscription_client = SubscriptionClient(self.credential)
                subscriptions = self.subscription_client.subscriptions.list()
            except Exception as err:
                raise AzureDriverError(f"Azure: unauthorized (use az login): {err}")
            self.azure_subscription_id = list(next(subscriptions, None))[0]
        elif not self.azure_subscription_id:
            raise AzureDriverError("can not determine subscription ID, please authenticate with az login")

        if not self.credential:
            self.credential = AzureCliCredential()
        self.resource_client = ResourceManagementClient(self.credential, self.azure_subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, self.azure_subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.azure_subscription_id)

        if 'AZURE_RESOURCE_GROUP' in os.environ:
            self.azure_resource_group = os.environ['AZURE_RESOURCE_GROUP']
        elif self.local_context:
            context_file = self.auth_directory + '/.azure/.local_context_' + self.local_context
            if os.path.exists(context_file):
                config = configparser.ConfigParser()
                try:
                    config.read(context_file)
                except Exception as err:
                    raise AzureDriverError(f"can not read context file {context_file}: {err}")
                if 'all' in config:
                    if 'resource_group_name' in config['all']:
                        self.azure_resource_group = config['all']['resource_group_name']

        if 'AZURE_LOCATION' in os.environ:
            self.azure_location = os.environ['AZURE_LOCATION']
        elif self.azure_resource_group:
            resource_group = self.resource_client.resource_groups.list()
            for group in list(resource_group):
                if group.name == self.azure_resource_group:
                    self.azure_location = group.location
                    break

        if not self.azure_resource_group:
            raise AzureDriverError("can not determine resource group, set AZURE_RESOURCE_GROUP or enable persisted parameters")
        if not self.azure_location:
            raise AzureDriverError("can not determine location, set AZURE_LOCATION")

        self.set_zone()

    def read_config(self):
        if os.path.exists(self.config_main):
            config = configparser.ConfigParser()
            try:
                config.read(self.config_main)
            except Exception as err:
                raise AzureDriverError(f"can not read config file {self.config_main}: {err}")

            if 'cloud' in config:
                if 'name' in config['cloud']:
                    self.cloud_name = config['cloud']['name']

            if 'local_context' in config:
                try:
                    self.local_context = list(config['local_context'].keys())[0]
                except IndexError:
                    pass

        if os.path.exists(self.config_default):
            config = configparser.ConfigParser()
            try:
                config.read(self.config_default)
            except Exception as err:
                raise AzureDriverError(f"can not read config file {self.config_default}: {err}")

            if self.cloud_name in config:
                self.azure_subscription_id = config[self.cloud_name].get('subscription', None)

    def zones(self) -> list:
        zone_list = self.compute_client.resource_skus.list(filter=f"location eq '{self.azure_location}'")
        for group in list(zone_list):
            if group.resource_type == 'virtualMachines':
                for resource_location in group.location_info:
                    for zone_number in resource_location.zones:
                        self.azure_availability_zones.append(zone_number)

        self.azure_availability_zones = sorted(set(self.azure_availability_zones))

        if len(self.azure_availability_zones) == 0:
            raise AzureDriverError("can not get Azure availability zones")

        self.azure_zone = self.azure_availability_zones[0]
        return self.azure_availability_zones

    def set_zone(self) -> None:
        zone_list = self.zones()
        config.cloud_zone_cycle = cycle(zone_list)

    def create_rg(self, name: str, location: str, tags: Union[dict, None]) -> dict:
        if not tags:
            tags = {}
        if not tags.get('type'):
            tags.update({"type": "couch-formation"})
        try:
            if self.resource_client.resource_groups.check_existence(name):
                return self.get_rg(name, location)
            else:
                result = self.resource_client.resource_groups.create_or_update(
                    name,
                    {
                        "location": location,
                        "tags": tags
                    }
                )
                return result.__dict__
        except Exception as err:
            raise AzureDriverError(f"error creating resource group: {err}")

    def get_rg(self, name: str, location: str) -> Union[dict, None]:
        try:
            if self.resource_client.resource_groups.check_existence(name):
                result = self.resource_client.resource_groups.get(name)
                if result.location == location:
                    return result.__dict__
        except Exception as err:
            raise AzureDriverError(f"error getting resource group: {err}")

        return None

    @staticmethod
    def process_tags(struct: dict) -> dict:
        block = {}
        if struct:
            for tag in struct:
                block.update({tag.lower() + '_tag': struct[tag]})
        block = dict(sorted(block.items()))
        return block

    def rg_switch(self):
        image_rg = f"cf-image-{self.azure_location}-rg"
        if self.get_rg(image_rg, self.azure_location):
            resource_group = image_rg
        else:
            resource_group = self.azure_resource_group
        return resource_group

    @property
    def region(self):
        return self.azure_location


class Network(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self) -> list[dict]:
        vnet_list = []

        try:
            vnetworks = self.network_client.virtual_networks.list(self.azure_resource_group)
        except Exception as err:
            raise AzureDriverError(f"error getting vnet: {err}")

        for group in list(vnetworks):
            if group.location != self.azure_location:
                continue
            network_block = {'cidr': group.address_space.address_prefixes,
                             'name': group.name,
                             'subnets': [s.name for s in group.subnets],
                             'id': group.id}
            vnet_list.append(network_block)

        if len(vnet_list) == 0:
            raise AzureDriverError(f"no suitable virtual network in location {self.azure_location}")

        return vnet_list

    @property
    def cidr_list(self):
        for item in self.list():
            for net in item['cidr']:
                yield net

    def create(self, name: str) -> str:
        pass

    def delete(self, network: str) -> None:
        pass

    def details(self, network: str) -> dict:
        pass


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, vnet: str) -> list[dict]:
        subnet_list = []

        try:
            subnets = self.network_client.subnets.list(self.azure_resource_group, vnet)
        except Exception as err:
            raise AzureDriverError(f"error getting subnets: {err}")

        for group in list(subnets):
            subnet_block = {'cidr': group.address_prefix,
                            'name': group.name,
                            'routes': group.route_table.routes,
                            'nsg': group.network_security_group,
                            'id': group.id}
            subnet_list.append(subnet_block)

        if len(subnet_list) == 0:
            raise AzureDriverError(f"no subnets in vnet {vnet}")

        return subnet_list


class SecurityGroup(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class MachineType(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self) -> list:
        machine_type_list = []

        try:
            sizes = self.compute_client.virtual_machine_sizes.list(self.azure_location)
        except Exception as err:
            raise AzureDriverError(f"error listing machine types: {err}")

        for group in list(sizes):
            config_block = {'name': group.name,
                            'cpu': int(group.number_of_cores),
                            'memory': int(group.memory_in_mb),
                            'disk': int(group.resource_disk_size_in_mb)}
            machine_type_list.append(config_block)

        if len(machine_type_list) == 0:
            raise AzureDriverError(f"no machine types in location {self.azure_location}")

        return machine_type_list

    def details(self, machine_type: str) -> Union[dict, None]:
        try:
            sizes = self.compute_client.virtual_machine_sizes.list(self.azure_location)
        except Exception as err:
            raise AzureDriverError(f"error getting machine type {machine_type}: {err}")

        for group in list(sizes):
            if group.name == machine_type:
                return {'name': group.name,
                        'cpu': int(group.number_of_cores),
                        'memory': int(group.memory_in_mb),
                        'disk': int(group.resource_disk_size_in_mb)}
        return None


class Instance(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Image(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, filter_keys_exist: Union[list[str], None] = None, resource_group: Union[str, None] = None) -> list[dict]:
        image_list = []
        if not resource_group:
            resource_group = self.rg_switch()

        images = self.compute_client.images.list_by_resource_group(resource_group)

        for image in list(images):
            image_block = {'name': image.name,
                           'id': image.id,
                           'location': image.location}
            image_block.update(self.process_tags(image.tags))
            if filter_keys_exist:
                if not all(key in image_block for key in filter_keys_exist):
                    continue
            image_list.append(image_block)

        if len(image_list) == 0:
            raise AzureDriverError(f"no images found")

        return image_list

    def details(self, name: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.rg_switch()
        request = self.compute_client.images.get(resource_group, name)
        image = request.result()
        image_block = {'name': image.name,
                       'id': image.id,
                       'location': image.location}
        image_block.update(self.process_tags(image.tags))
        return image_block

    def create(self, name: str, source_image: str, description=None, root_type="StandardSSD_LRS", root_size=100) -> str:
        pass

    def delete(self, name: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.rg_switch()
        request = self.compute_client.images.begin_delete(resource_group, name)
        result = request.result()

    def market_search(self, name: str) -> Union[dict, None]:
        pass
