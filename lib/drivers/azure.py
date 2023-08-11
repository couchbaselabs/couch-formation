##
##

import logging
import os
import configparser
import attr
from typing import Union
from Crypto.PublicKey import RSA
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.core.exceptions import ResourceNotFoundError
from lib.util.filemgr import FileManager
from itertools import cycle
from lib.exceptions import AzureDriverError, EmptyResultSet
import lib.config as config
from lib.util.db_mgr import LocalDB

logger = logging.getLogger('cf.driver.azure')
logger.addHandler(logging.NullHandler())
logging.getLogger("azure").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
CLOUD_KEY = "azure"


@attr.s
class AzureDiskTypes(object):
    disk_type_list = [
        {
            "type": 'Premium_LRS'
        },
        {
            "type": 'UltraSSD_LRS'
        }
    ]


@attr.s
class AzureDiskTiers(object):
    disk_tier_list = [
        {
            "disk_size": "64",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "128",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "256",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "512",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "1024",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "2048",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "4096",
            "disk_tier": "P50",
            "disk_iops": "16000"
        },
        {
            "disk_size": "8192",
            "disk_tier": "P80",
            "disk_iops": "16000"
        },
        {
            "disk_size": "16384",
            "disk_tier": "P80",
            "disk_iops": "16000"
        }
    ]


@attr.s
class AzureImagePublishers(object):
    publishers = [
        {
            "name": "Canonical",
            "description": "Ubuntu Linux"
        },
        {
            "name": "OpenLogic",
            "description": "CentOS Linux"
        },
        {
            "name": "RedHat",
            "description": "RedHat Linux"
        },
        {
            "name": "SUSE",
            "description": "Suse Linux"
        },
        {
            "name": "credativ",
            "description": "Debian 9 and earlier"
        },
        {
            "name": "Debian",
            "description": "Debian 10 and later"
        },
        {
            "name": "Oracle-Linux",
            "description": "Oracle Linux"
        },
        {
            "name": "CoreOS",
            "description": "CoreOS"
        },
    ]


class CloudInit(object):
    VERSION = '4.0.0'

    def __init__(self):
        self.db = LocalDB()

    def auth(self):
        pass

    def init(self):
        pass


class CloudBase(object):
    VERSION = '3.0.1'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = True

    def __init__(self, region: str = None, null_init: bool = True, cloud: str = CLOUD_KEY):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.getLogger("azure").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)
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
        self.cloud = cloud

        self.read_config()

        if not self.credential:
            self.credential = AzureCliCredential()
        self.subscription_client = SubscriptionClient(self.credential)

        if 'AZURE_SUBSCRIPTION_ID' in os.environ:
            self.azure_subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        elif not self.azure_subscription_id:
            try:
                subscriptions = self.subscription_client.subscriptions.list()
            except Exception as err:
                raise AzureDriverError(f"Azure: unauthorized (use az login): {err}")
            self.azure_subscription_id = list(next(subscriptions, None))[0]
        elif not self.azure_subscription_id:
            raise AzureDriverError("can not determine subscription ID, please authenticate with az login")

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

        if region:
            self.azure_location = region
        elif 'AZURE_LOCATION' in os.environ:
            self.azure_location = os.environ['AZURE_LOCATION']
        elif self.azure_resource_group:
            resource_group = self.resource_client.resource_groups.list()
            for group in list(resource_group):
                if group.name == self.azure_resource_group:
                    self.azure_location = group.location
                    break

        if not self.azure_resource_group and not null_init:
            raise AzureDriverError("can not determine resource group, set AZURE_RESOURCE_GROUP or enable persisted parameters")
        if not self.azure_location and not null_init:
            raise AzureDriverError("can not determine location, set AZURE_LOCATION")

        if self.azure_location:
            self.set_zone()

    def get_info(self):
        self.logger.info(f"Subscription ID: {self.azure_subscription_id}")
        self.logger.info(f"Region:          {self.region}")
        self.logger.info(f"Resource Group:  {self.azure_resource_group}")
        self.logger.info(f"Available Zones: {','.join(self.azure_availability_zones)}")

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

    def create_rg(self, name: str, location: str, tags: Union[dict, None] = None) -> dict:
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

    def list_rg(self, location: Union[str, None] = None, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        rg_list = []

        try:
            resource_groups = self.resource_client.resource_groups.list()
        except Exception as err:
            raise AzureDriverError(f"error getting resource groups: {err}")

        for group in list(resource_groups):
            if location:
                if group.location != location:
                    continue
            rg_block = {'location': group.location,
                        'name': group.name,
                        'id': group.id}
            rg_block.update(self.process_tags(group.tags))
            if filter_keys_exist:
                if not all(key in rg_block for key in filter_keys_exist):
                    continue
            rg_list.append(rg_block)

        if len(rg_list) == 0:
            raise EmptyResultSet(f"no resource groups found")

        return rg_list

    def delete_rg(self, name: str):
        try:
            if self.resource_client.resource_groups.check_existence(name):
                request = self.resource_client.resource_groups.begin_delete(name)
                request.wait()
        except Exception as err:
            raise AzureDriverError(f"error deleting resource group: {err}")

    def list_locations(self) -> list[dict]:
        location_list = []
        locations = self.subscription_client.subscriptions.list_locations(self.azure_subscription_id)
        for group in list(locations):
            location_block = {
                'name': group.name,
                'display_name': group.display_name
            }
            location_list.append(location_block)
        return location_list

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

    def list(self, resource_group: Union[str, None] = None, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        if not resource_group:
            if not self.azure_resource_group:
                return []
            resource_group = self.azure_resource_group
        vnet_list = []

        try:
            vnetworks = self.network_client.virtual_networks.list(resource_group)
        except Exception as err:
            raise AzureDriverError(f"error getting vnet: {err}")

        for group in list(vnetworks):
            if group.location != self.azure_location:
                continue
            network_block = {'cidr': group.address_space.address_prefixes,
                             'name': group.name,
                             'subnets': [s.name for s in group.subnets],
                             'id': group.id}
            network_block.update(self.process_tags(group.tags))
            if filter_keys_exist:
                if not all(key in network_block for key in filter_keys_exist):
                    continue
            vnet_list.append(network_block)

        if len(vnet_list) == 0:
            raise EmptyResultSet(f"no suitable virtual network in location {self.azure_location}")

        return vnet_list

    @property
    def cidr_list(self):
        try:
            for item in self.list():
                for net in item['cidr']:
                    yield net
        except EmptyResultSet:
            return iter(())

    def create(self, name: str, cidr: str, resource_group: Union[str, None] = None) -> str:
        if not resource_group:
            resource_group = self.azure_resource_group

        try:
            net_info = self.details(name, resource_group)
            return net_info['name']
        except ResourceNotFoundError:
            pass

        try:
            request = self.network_client.virtual_networks.begin_create_or_update(
                resource_group,
                name,
                {
                    'location': self.azure_location,
                    'address_space': {
                        'address_prefixes': [cidr]
                    }
                }
            )
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error creating network: {err}")
        return name

    def delete(self, network: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.virtual_networks.begin_delete(resource_group, network)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error getting vnet: {err}")

    def details(self, network: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            info = self.network_client.virtual_networks.get(resource_group, network)
        except ResourceNotFoundError:
            raise
        except Exception as err:
            raise AzureDriverError(f"error getting vnet: {err}")

        network_block = {'cidr': info.address_space.address_prefixes,
                         'name': info.name,
                         'subnets': [s.name for s in info.subnets],
                         'id': info.id}
        network_block.update(self.process_tags(info.tags))

        return network_block

    def create_pub_ip(self, name: str, resource_group: Union[str, None] = None) -> dict:
        public_ip = {
            'location': self.azure_location,
            'public_ip_allocation_method': 'Static',
            'sku': {
                'name': 'Standard'
            }
        }

        try:
            request = self.network_client.public_ip_addresses.begin_create_or_update(resource_group, name, public_ip)
            result = request.result()
        except Exception as err:
            raise AzureDriverError(f"can not create public IP: {err}")

        return result.__dict__

    def create_nic(self, name: str, network: str, subnet: str, zone: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.azure_resource_group

        try:
            subnet_info = Subnet().details(network, subnet, resource_group)
        except Exception as err:
            raise AzureDriverError(f"can not get subnet {subnet} info: {err}")

        pub_ip = self.create_pub_ip(f"{name}-pub-ip", resource_group)

        parameters = {
            'location': self.azure_location,
            'ip_configurations': [
                {
                    'name': f"{name}-int",
                    'subnet': {
                        'id': subnet_info['id'],
                    },
                    'private_ip_allocation_method': 'Dynamic',
                    'zones': [zone],
                    'public_ip_address': {
                        'id': pub_ip['id']
                    }
                }
            ]
        }

        try:
            request = self.network_client.network_interfaces.begin_create_or_update(resource_group, name, parameters)
            result = request.result()
        except Exception as err:
            raise AzureDriverError(f"error creating nic: {err}")

        return result.__dict__

    def delete_pub_ip(self, name: str, resource_group: Union[str, None] = None):
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.public_ip_addresses.begin_delete(resource_group, name)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error deleting public IP: {err}")

    def delete_nic(self, name: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.network_interfaces.begin_delete(resource_group, name)
            request.wait()
            self.delete_pub_ip(f"{name}-pub-ip", resource_group)
        except Exception as err:
            raise AzureDriverError(f"error deleting nic: {err}")


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, vnet: str, resource_group: Union[str, None] = None) -> list[dict]:
        if not resource_group:
            resource_group = self.azure_resource_group
        subnet_list = []

        try:
            subnets = self.network_client.subnets.list(resource_group, vnet)
        except Exception as err:
            raise AzureDriverError(f"error getting subnets: {err}")

        for group in list(subnets):
            subnet_block = {'cidr': group.address_prefix,
                            'name': group.name,
                            'routes': group.route_table.routes if group.route_table else None,
                            'nsg': group.network_security_group.id.rsplit('/', 1)[-1] if group.network_security_group else None,
                            'id': group.id}
            subnet_list.append(subnet_block)

        if len(subnet_list) == 0:
            raise EmptyResultSet(f"no subnets in vnet {vnet}")

        return subnet_list

    def create(self, name: str, network: str, cidr: str, nsg: str, resource_group: Union[str, None] = None) -> str:
        if not resource_group:
            resource_group = self.azure_resource_group

        nsg_data = SecurityGroup().details(nsg, resource_group)
        if not nsg_data.get('id'):
            raise AzureDriverError(f"can not lookup nsg {nsg}")

        request = self.network_client.subnets.begin_create_or_update(
            resource_group,
            network,
            name,
            {
                'address_prefix': cidr,
                'network_security_group': {
                    'id': nsg_data['id']
                }
            }
        )
        subnet_info = request.result()

        return subnet_info.name

    def delete(self, network: str, subnet: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.subnets.begin_delete(resource_group, network, subnet)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error deleting subnet: {err}")

    def details(self, network: str, subnet: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            info = self.network_client.subnets.get(resource_group, network, subnet)
        except Exception as err:
            raise AzureDriverError(f"error getting subnet: {err}")

        subnet_block = {'cidr': info.address_prefix,
                        'name': info.name,
                        'routes': info.route_table.routes if info.route_table else None,
                        'nsg': info.network_security_group.id.rsplit('/', 1)[-1] if info.network_security_group else None,
                        'id': info.id}

        return subnet_block


class SecurityGroup(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, resource_group: Union[str, None] = None, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        if not resource_group:
            resource_group = self.azure_resource_group
        nsg_list = []

        try:
            result = self.network_client.network_security_groups.list(resource_group)
        except Exception as err:
            raise AzureDriverError(f"error getting vnet: {err}")

        for group in list(result):
            if group.location != self.azure_location:
                continue
            nsg_block = {'location': group.location,
                         'name': group.name,
                         'rules': [r.__dict__ for r in group.security_rules] if group.security_rules else [],
                         'subnets': [s.__dict__ for s in group.subnets] if group.subnets else [],
                         'id': group.id}
            nsg_block.update(self.process_tags(group.tags))
            if filter_keys_exist:
                if not all(key in nsg_block for key in filter_keys_exist):
                    continue
            nsg_list.append(nsg_block)

        if len(nsg_list) == 0:
            raise EmptyResultSet(f"no suitable network security group in group {resource_group}")

        return nsg_list

    def create(self, name: str, resource_group: Union[str, None] = None) -> str:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.network_security_groups.begin_create_or_update(
                resource_group,
                name,
                {
                    'location': self.azure_location
                }
            )
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error creating network security group: {err}")
        return name

    def add_rule(self,
                 name: str,
                 nsg: str,
                 ports: list,
                 priority: int,
                 source: Union[list, None] = None,
                 resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        if source:
            default_source = None
        else:
            default_source = "*"
        try:
            request = self.network_client.security_rules.create_or_update(
                resource_group,
                nsg,
                name,
                {
                    "description": "Cloud Formation Managed",
                    "access": "Allow",
                    "destination_address_prefix": "*",
                    "destination_port_ranges": ports,
                    "direction": "Inbound",
                    "priority": priority,
                    "protocol": "Tcp",
                    "source_address_prefix": default_source,
                    "source_address_prefixes": source,
                    "source_port_range": "*",
                }
            )
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error creating network security group rule: {err}")

    def delete(self, name: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.network_client.network_security_groups.begin_delete(resource_group, name)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error getting network security group: {err}")

    def details(self, name: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            info = self.network_client.network_security_groups.get(resource_group, name)
        except Exception as err:
            raise AzureDriverError(f"error getting network security group: {err}")

        nsg_block = {'location': info.location,
                     'name': info.name,
                     'rules': [r.__dict__ for r in info.security_rules] if info.security_rules else [],
                     'subnets': [s.__dict__ for s in info.subnets] if info.subnets else [],
                     'id': info.id}
        nsg_block.update(self.process_tags(info.tags))

        return nsg_block


class MachineType(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self) -> list:
        machine_type_list = []

        try:
            resource_list = self.compute_client.resource_skus.list()
        except Exception as err:
            raise AzureDriverError(f"error listing machine types: {err}")

        for group in list(resource_list):
            vm_cpu = 0
            vm_mem = 0
            if self.azure_location not in group.locations:
                continue
            if group.restrictions:
                if len(list(group.restrictions)) != 0:
                    continue
            if not group.capabilities:
                continue
            for capability in group.capabilities:
                if capability.name == 'vCPUs':
                    vm_cpu = int(capability.value)
                if capability.name == 'MemoryGB':
                    try:
                        vm_mem = int(capability.value) * 1024
                    except ValueError:
                        vm_mem = float(capability.value) * 1024
            if vm_cpu == 0 or vm_mem == 0:
                continue
            config_block = {'name': group.name,
                            'cpu': vm_cpu,
                            'memory': vm_mem}
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

    def run(self,
            name: str,
            image_reference: Union[tuple, str],
            zone: str,
            network: str,
            subnet: str,
            username: str,
            public_key: str,
            root_type="StandardSSD_LRS",
            root_size=100,
            machine_type="Standard_D4_v3",
            resource_group: Union[str, None] = None) -> str:
        if not resource_group:
            resource_group = self.azure_resource_group

        try:
            instance_info = self.details(name, resource_group)
            return instance_info['name']
        except ResourceNotFoundError:
            pass

        if type(image_reference) is str:
            image_block = {
                'id': image_reference
            }
        else:
            image_block = {
                'publisher': image_reference[0],
                'offer': image_reference[1],
                'sku': image_reference[2],
                'version': 'latest'
            }

        try:
            nic_info = Network().create_nic(f"{name}-nic", network, subnet, zone, resource_group)
        except Exception as err:
            raise AzureDriverError(f"can not create nic: {err}")

        parameters = {
            'location': self.azure_location,
            'os_profile': {
                'computer_name': name,
                'admin_username': username,
                'linux_configuration': {
                    'ssh': {
                        'public_keys': [
                            {
                                'path': f"/home/{username}/.ssh/authorized_keys",
                                'key_data': public_key
                            }
                        ]
                    }
                }
            },
            'hardware_profile': {
                'vm_size': machine_type
            },
            'storage_profile': {
                'image_reference': image_block,
                'os_disk': {
                    'name': f"{name}-boot-disk",
                    'disk_size_gb': root_size,
                    'create_option': 'FromImage',
                    'managed_disk': {
                        'storage_account_type': root_type
                    }
                }
            },
            'network_profile': {
                'network_interfaces': [{
                    'id': nic_info['id'],
                }]
            },
        }

        try:
            request = self.compute_client.virtual_machines.begin_create_or_update(resource_group, name, parameters)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error listing machine types: {err}")

        return name

    def details(self, instance: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            machine = self.compute_client.virtual_machines.get(resource_group, instance)
        except ResourceNotFoundError:
            raise
        except Exception as err:
            raise AzureDriverError(f"error getting instance {instance}: {err}")

        instance_info = {'name': machine.name,
                         'id': machine.id,
                         'zones': machine.zones,
                         'storage': machine.storage_profile.__dict__,
                         'os': machine.os_profile.__dict__,
                         'disk': machine.network_profile.__dict__}

        return instance_info

    def terminate(self, instance: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.azure_resource_group
        try:
            request = self.compute_client.virtual_machines.begin_delete(resource_group, instance)
            request.wait()
            request = self.compute_client.disks.begin_delete(resource_group, f"{instance}-boot-disk")
            request.wait()
            Network().delete_nic(f"{instance}-nic", resource_group)
        except Exception as err:
            raise AzureDriverError(f"error deleting instance: {err}")


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def public_key(key_file: str) -> str:
        if not os.path.isabs(key_file):
            key_file = FileManager.ssh_key_absolute_path(key_file)
        fh = open(key_file, 'r')
        key_pem = fh.read()
        fh.close()
        rsa_key = RSA.importKey(key_pem)
        modulus = rsa_key.n
        pubExpE = rsa_key.e
        priExpD = rsa_key.d
        primeP = rsa_key.p
        primeQ = rsa_key.q
        private_key = RSA.construct((modulus, pubExpE, priExpD, primeP, primeQ))
        public_key = private_key.public_key().exportKey('OpenSSH')
        ssh_public_key = public_key.decode('utf-8')
        return ssh_public_key


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
                           'resource_group': resource_group,
                           'location': image.location}
            image_block.update(self.process_tags(image.tags))
            if filter_keys_exist:
                if not all(key in image_block for key in filter_keys_exist):
                    continue
            image_list.append(image_block)

        if len(image_list) == 0:
            raise EmptyResultSet(f"no images found")

        return image_list

    def public(self, location: str, publisher: str):
        offer_list = []
        pruned_offer_list = []

        offers = self.compute_client.virtual_machine_images.list_offers(location, publisher)
        for group in list(offers):
            offer_block = {'name': group.name,
                           'skus': [],
                           'count': 0}
            offer_list.append(offer_block)

        for n, offer in enumerate(offer_list):
            offer_name = offer['name']
            skus = self.compute_client.virtual_machine_images.list_skus(location, publisher, offer_name)
            for group in list(skus):
                sku_name = group.name
                versions = self.compute_client.virtual_machine_images.list(location, publisher, offer_name, sku_name)
                if len(list(versions)) > 0:
                    offer_list[n]['skus'].append(sku_name)
                    offer_list[n]['count'] = len(offer_list[n]['skus'])

        for offer in offer_list:
            if offer['count'] != 0:
                pruned_offer_list.append(offer)

        if len(pruned_offer_list) == 0:
            raise EmptyResultSet(f"no images found")

        return pruned_offer_list

    def details(self, name: str, resource_group: Union[str, None] = None) -> dict:
        if not resource_group:
            resource_group = self.rg_switch()
        request = self.compute_client.images.get(resource_group, name)
        image = request.result()
        image_block = {'name': image.name,
                       'id': image.id,
                       'resource_group': resource_group,
                       'location': image.location}
        image_block.update(self.process_tags(image.tags))
        return image_block

    def create(self, name: str, source_instance: str, root_type="StandardSSD_LRS", root_size=100, resource_group: Union[str, None] = None) -> str:
        if not resource_group:
            resource_group = self.rg_switch()

        try:
            vm_info = Instance().details(source_instance, resource_group)
            vm_id = vm_info['id']
        except Exception as err:
            raise AzureDriverError(f"can not get instance {name} info: {err}")

        parameters = {
            'location': self.azure_location,
            'source_virtual_machine': {
                'id': vm_id
            },
        }

        try:
            request = self.compute_client.virtual_machines.begin_power_off(resource_group, source_instance)
            request.wait()
            self.compute_client.virtual_machines.generalize(resource_group, source_instance)
            request = self.compute_client.images.begin_create_or_update(resource_group, name, parameters)
            request.wait()
        except Exception as err:
            raise AzureDriverError(f"error creating image: {err}")

        return name

    def delete(self, name: str, resource_group: Union[str, None] = None) -> None:
        if not resource_group:
            resource_group = self.rg_switch()
        try:
            request = self.compute_client.images.begin_delete(resource_group, name)
            result = request.result()
        except Exception as err:
            raise AzureDriverError(f"can not delete image: {err}")

    def market_search(self, name: str) -> Union[dict, None]:
        pass
