##
##

import logging
import os
import json
import attr
import configparser
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2 import service_account
from lib.exceptions import GCPDriverError, EmptyResultSet
from typing import Union
from itertools import cycle
import lib.config as config
import time


@attr.s
class GCPDiskTypes(object):
    disk_type_list = [
        {
            "type": 'pd-standard'
        },
        {
            "type": 'pd-balanced'
        },
        {
            "type": 'pd-ssd'
        }
    ]


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = False

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.getLogger("googleapiclient").setLevel(logging.ERROR)
        self.auth_directory = os.environ['HOME'] + '/.config/gcloud'
        self.config_default = self.auth_directory + '/configurations/config_default'
        self.gcp_account = None
        self.gcp_project = None
        self.gcp_region = None
        self.gcp_account_file = None
        self.gcp_account_email = None
        self.gcp_zone_list = []
        self.gcp_zone = None

        self.read_config()

        if 'GCP_ACCOUNT_FILE' in os.environ:
            if os.path.exists(self.auth_directory + '/' + os.environ['GCP_ACCOUNT_FILE']):
                self.gcp_account_file = self.auth_directory + '/' + os.environ['GCP_ACCOUNT_FILE']
            elif os.path.exists(os.environ['GCP_ACCOUNT_FILE']):
                self.gcp_account_file = os.environ['GCP_ACCOUNT_FILE']
            else:
                print(f"environment variable GCP_ACCOUNT_FILE = {os.environ['GCP_ACCOUNT_FILE']}: file not found")
        if not self.gcp_account_file:
            print("Please set GCP_ACCOUNT_FILE to reference the path to your auth json file")
            raise GCPDriverError("can not locate auth file")

        self.read_auth_file()
        if not self.gcp_account_email:
            raise GCPDriverError(f"can not get account email from auth file {self.gcp_account_file}")

        if 'GCP_DEFAULT_REGION' in os.environ:
            self.gcp_region = os.environ['GCP_DEFAULT_REGION']
        if not self.gcp_region:
            print("Please set GCP_DEFAULT_REGION to specify a GCP region")
            print("Or set your default region with: gcloud config set compute/region region-name")
            raise GCPDriverError("no default region")

        if 'GCP_PROJECT_ID' in os.environ:
            self.gcp_project = os.environ['GCP_PROJECT_ID']
        else:
            file_handle = open(self.gcp_account_file, 'r')
            auth_data = json.load(file_handle)
            file_handle.close()
            if 'project_id' in auth_data:
                gcp_auth_json_project_id = auth_data['project_id']
                self.gcp_project = gcp_auth_json_project_id
            elif not self.gcp_project:
                print("can not determine GCP project, please set GCP_PROJECT_ID")
                raise GCPDriverError("can not determine project ID")

        try:
            credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
            self.gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        except Exception as err:
            raise GCPDriverError(f"error connecting to GCP: {err}")

        self.zones()
        self.set_zone()

    def get_info(self):
        self.logger.info(f"Account File:    {self.gcp_account_file}")
        self.logger.info(f"Region:          {self.gcp_region}")
        self.logger.info(f"Project:         {self.gcp_project}")
        self.logger.info(f"Available Zones: {','.join(self.gcp_zone_list)}")

    def read_config(self):
        if os.path.exists(self.config_default):
            config_data = configparser.ConfigParser()
            try:
                config_data.read(self.config_default)
            except Exception as err:
                raise GCPDriverError(f"can not read config file {self.config_default}: {err}")

            if 'core' in config_data:
                self.gcp_account = config_data['core'].get('account', None)
                self.gcp_project = config_data['core'].get('project', None)

            if 'compute' in config_data:
                self.gcp_region = config_data['compute'].get('region', None)

    def read_auth_file(self):
        file_handle = open(self.gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'client_email' in auth_data:
            self.gcp_account_email = auth_data['client_email']

    def zones(self) -> list:
        request = self.gcp_client.zones().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            for zone in response['items']:
                if not zone['name'].startswith(self.gcp_region):
                    continue
                self.gcp_zone_list.append(zone['name'])
            request = self.gcp_client.zones().list_next(previous_request=request, previous_response=response)

        self.gcp_zone_list = sorted(set(self.gcp_zone_list))

        if len(self.gcp_zone_list) == 0:
            raise GCPDriverError("can not get GCP availability zones")

        self.gcp_zone = self.gcp_zone_list[0]
        return self.gcp_zone_list

    def set_zone(self) -> None:
        zone_list = self.zones()
        config.cloud_zone_cycle = cycle(zone_list)

    @property
    def region(self):
        return self.gcp_region

    @property
    def account_file(self):
        return self.gcp_account_file

    @property
    def project(self):
        return self.gcp_project

    @staticmethod
    def process_labels(struct: dict) -> dict:
        block = {}
        if 'labels' in struct:
            for tag in struct['labels']:
                block.update({tag.lower() + '_tag': struct['labels'][tag]})
        block = dict(sorted(block.items()))
        return block

    def wait_for_global_operation(self, operation):
        while True:
            result = self.gcp_client.globalOperations().get(
                project=self.gcp_project,
                operation=operation).execute()

            if result['status'] == 'DONE':
                if 'error' in result:
                    raise GCPDriverError(result['error'])
                return result

            time.sleep(1)

    def wait_for_regional_operation(self, operation):
        while True:
            result = self.gcp_client.regionOperations().get(
                project=self.gcp_project,
                region=self.gcp_region,
                operation=operation).execute()

            if result['status'] == 'DONE':
                if 'error' in result:
                    raise GCPDriverError(result['error'])
                return result

            time.sleep(1)

    def wait_for_zone_operation(self, operation, zone):
        while True:
            result = self.gcp_client.zoneOperations().get(
                project=self.gcp_project,
                zone=zone,
                operation=operation).execute()

            if result['status'] == 'DONE':
                if 'error' in result:
                    raise GCPDriverError(result['error'])
                return result

            time.sleep(1)


class Network(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self) -> list[dict]:
        network_list = []

        try:
            request = self.gcp_client.networks().list(project=self.gcp_project)
            while request is not None:
                response = request.execute()

                for network in response['items']:
                    subnet_list = []
                    for subnet in network['subnetworks']:
                        subnet_name = subnet.rsplit('/', 4)[-1]
                        region_name = subnet.rsplit('/', 4)[-3]
                        if region_name != self.region:
                            continue
                        result = Subnet().details(self.region, subnet_name)
                        subnet_list.append(result)
                    network_block = {'cidr': network.get('IPv4Range', None),
                                     'name': network['name'],
                                     'description': network.get('description', None),
                                     'subnets': subnet_list,
                                     'id': network['id']}
                    network_list.append(network_block)
                request = self.gcp_client.networks().list_next(previous_request=request, previous_response=response)
        except Exception as err:
            raise GCPDriverError(f"error listing networks: {err}")

        if len(network_list) == 0:
            raise EmptyResultSet(f"no networks found")
        else:
            return network_list

    @property
    def cidr_list(self):
        for network in self.list():
            for item in Subnet().list(network['name']):
                yield item['cidr']

    def create(self, name: str) -> str:
        network_body = {
            "name": name,
            "autoCreateSubnetworks": False
        }
        try:
            request = self.gcp_client.networks().insert(project=self.gcp_project, body=network_body)
            operation = request.execute()
            self.wait_for_global_operation(operation['name'])
        except googleapiclient.errors.HttpError as err:
            error_details = err.error_details[0].get('reason')
            if error_details != "alreadyExists":
                raise GCPDriverError(f"can not create network: {err}")
        except Exception as err:
            raise GCPDriverError(f"error creating network: {err}")

        return name

    def delete(self, network: str) -> None:
        try:
            request = self.gcp_client.networks().delete(project=self.gcp_project, network=network)
            operation = request.execute()
            self.wait_for_global_operation(operation['name'])
        except Exception as err:
            raise GCPDriverError(f"error deleting network: {err}")

    def details(self, network: str) -> dict:
        try:
            request = self.gcp_client.networks().get(project=self.gcp_project, network=network)
            result = request.execute()
            return result
        except Exception as err:
            raise GCPDriverError(f"error getting network link: {err}")


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, network: str, region: Union[str, None] = None) -> list[dict]:
        subnet_list = []

        try:
            request = self.gcp_client.subnetworks().list(project=self.gcp_project, region=self.gcp_region)
            while request is not None:
                response = request.execute()
                for subnet in response['items']:
                    network_name = subnet['network'].rsplit('/', 1)[-1]
                    region_name = subnet['region'].rsplit('/', 1)[-1]
                    if region:
                        if region != region_name:
                            continue
                    if network != network_name:
                        continue
                    subnet_block = {'cidr': subnet['ipCidrRange'],
                                    'name': subnet['name'],
                                    'description': subnet.get('description', None),
                                    'gateway': subnet['gatewayAddress'],
                                    'network': network_name,
                                    'region': region_name,
                                    'id': subnet['id']}
                    subnet_list.append(subnet_block)
                request = self.gcp_client.subnetworks().list_next(previous_request=request, previous_response=response)
        except Exception as err:
            raise GCPDriverError(f"error listing subnets: {err}")

        if len(subnet_list) == 0:
            raise EmptyResultSet(f"no subnets found")
        else:
            return subnet_list

    def create(self, name: str, network: str, cidr: str) -> str:
        network_info = Network().details(network)
        subnetwork_body = {
            "name": name,
            "network": network_info['selfLink'],
            "ipCidrRange": cidr,
            "region": self.gcp_region
        }
        try:
            request = self.gcp_client.subnetworks().insert(project=self.gcp_project, region=self.gcp_region, body=subnetwork_body)
            operation = request.execute()
            self.wait_for_regional_operation(operation['name'])
        except googleapiclient.errors.HttpError as err:
            error_details = err.error_details[0].get('reason')
            if error_details != "alreadyExists":
                raise GCPDriverError(f"can not create subnet: {err}")
        except Exception as err:
            raise GCPDriverError(f"error creating subnet: {err}")

        return name

    def delete(self, subnet: str) -> None:
        try:
            request = self.gcp_client.subnetworks().delete(project=self.gcp_project, region=self.gcp_region, subnetwork=subnet)
            operation = request.execute()
            self.wait_for_regional_operation(operation['name'])
        except Exception as err:
            raise GCPDriverError(f"error deleting network: {err}")

    def details(self, region: str, subnet: str) -> dict:
        try:
            request = self.gcp_client.subnetworks().get(project=self.gcp_project, region=region, subnetwork=subnet)
            result = request.execute()
            network_name = result['network'].rsplit('/', 1)[-1]
            region_name = result['region'].rsplit('/', 1)[-1]
            subnet_block = {'cidr': result['ipCidrRange'],
                            'name': result['name'],
                            'description': result.get('description', None),
                            'gateway': result['gatewayAddress'],
                            'network': network_name,
                            'region': region_name,
                            'id': result['id']}
            return subnet_block
        except Exception as err:
            raise GCPDriverError(f"error getting network link: {err}")


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
            request = self.gcp_client.machineTypes().list(project=self.gcp_project, zone=self.gcp_zone)
            while request is not None:
                response = request.execute()
                for machine_type in response['items']:
                    config_block = {'name': machine_type['name'],
                                    'id': machine_type['id'],
                                    'cpu': int(machine_type['guestCpus']),
                                    'memory': int(machine_type['memoryMb']),
                                    'description': machine_type['description']}
                    machine_type_list.append(config_block)
                request = self.gcp_client.machineTypes().list_next(previous_request=request, previous_response=response)
        except Exception as err:
            raise GCPDriverError(f"error listing machine types: {err}")

        return machine_type_list

    def details(self, machine_type: str) -> dict:
        try:
            request = self.gcp_client.machineTypes().get(project=self.gcp_project, zone=self.gcp_zone, machineType=machine_type)
            response = request.execute()
            return {'name': response['name'],
                    'id': response['id'],
                    'cpu': int(response['guestCpus']),
                    'memory': int(response['memoryMb']),
                    'description': response['description']}
        except Exception as err:
            GCPDriverError(f"error getting machine type details: {err}")


class Instance(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, name: str, image_name: str, zone: str, vpc: str, subnet: str, public_key: str, root_type="pd-ssd", root_size=100, machine_type="n2-standard-2"):
        image_detail = Image().market_search(image_name)
        if not image_detail:
            raise GCPDriverError(f"can not find image {image_name}")

        instance_body = {
            "name": name,
            "networkInterfaces": [
                {
                    "network": f"projects/{self.gcp_project}/global/networks/{vpc}",
                    "subnetwork": f"regions/{self.gcp_region}/subnetworks/{subnet}",
                    "accessConfigs": []
                }
            ],
            "metadata": {
                "items": [
                    {
                        "key": "ssh-keys",
                        "value": public_key
                    }
                ]
            },
            "disks": [
                {
                    "boot": True,
                    "initializeParams": {
                        "sourceImage": image_detail['link'],
                        "diskType": f"zones/{zone}/diskTypes/{root_type}",
                        "diskSizeGb": root_size
                    },
                    "autoDelete": True
                }
            ],
            "machineType": f"zones/{zone}/machineTypes/{machine_type}"
        }

        try:
            request = self.gcp_client.instances().insert(project=self.gcp_project, zone=zone, body=instance_body)
            operation = request.execute()
            self.wait_for_zone_operation(operation['name'], zone)
        except googleapiclient.errors.HttpError as err:
            error_details = err.error_details[0].get('reason')
            if error_details != "alreadyExists":
                raise GCPDriverError(f"can not create instance: {err}")
        except Exception as err:
            raise GCPDriverError(f"error creating instance: {err}")

        return name

    def details(self, instance: str, zone: str) -> dict:
        try:
            request = self.gcp_client.instances().get(project=self.gcp_project, zone=zone, instance=instance)
            response = request.execute()
        except Exception as err:
            raise GCPDriverError(f"error getting instance details: {err}")

        return response

    def terminate(self, instance: str, zone: str) -> None:
        try:
            request = self.gcp_client.instances().delete(project=self.gcp_project, zone=zone, instance=instance)
            operation = request.execute()
            self.wait_for_zone_operation(operation['name'], zone)
        except Exception as err:
            raise GCPDriverError(f"error terminating instance: {err}")


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Image(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, filter_keys_exist: Union[list[str], None] = None, project: Union[str, None] = None) -> list[dict]:
        image_list = []
        if not project:
            project = self.gcp_project

        request = self.gcp_client.images().list(project=project)

        while request is not None:
            try:
                response = request.execute()
            except Exception as err:
                raise GCPDriverError(f"error getting images: {err}")
            if response.get('items') is None:
                break
            for image in response['items']:
                image_block = {'name': image['name'],
                               'link': image['selfLink'],
                               'date': image['creationTimestamp']}
                image_block.update(self.process_labels(image))
                if filter_keys_exist:
                    if not all(key in image_block for key in filter_keys_exist):
                        continue
                image_list.append(image_block)
            request = self.gcp_client.images().list_next(previous_request=request, previous_response=response)

        if len(image_list) == 0:
            raise EmptyResultSet(f"no images found")

        return image_list

    def details(self, image: str, project: Union[str, None] = None) -> dict:
        if not project:
            project = self.gcp_project

        try:
            request = self.gcp_client.images().get(project=project, image=image)
            image = request.execute()
        except Exception as err:
            if isinstance(err, googleapiclient.errors.HttpError):
                error_details = err.error_details[0].get('reason')
                if error_details == "notFound":
                    raise EmptyResultSet(f"image {image} not found")
            raise GCPDriverError(f"image detail error: {err}")

        image_block = {'name': image['name'],
                       'link': image['selfLink'],
                       'date': image['creationTimestamp']}
        image_block.update(self.process_labels(image))

        return image_block

    def create(self, name: str, source_image: str, description=None, root_size=100) -> str:
        image_detail = Image().market_search(source_image)
        if not image_detail:
            raise GCPDriverError(f"can not find image {source_image}")
        image_body = {
            "name": name,
            "description": description if description else "",
            "sourceImage": image_detail['link'],
            "diskSizeGb": root_size,
        }
        try:
            request = self.gcp_client.images().insert(project=self.gcp_project, body=image_body)
            operation = request.execute()
            self.wait_for_global_operation(operation['name'])
        except Exception as err:
            raise GCPDriverError(f"error creating image: {err}")

        return name

    def delete(self, image: str) -> None:
        try:
            request = self.gcp_client.images().delete(project=self.gcp_project, image=image)
            operation = request.execute()
            self.wait_for_global_operation(operation['name'])
        except Exception as err:
            raise GCPDriverError(f"error deleting image: {err}")

    def market_search(self, name: str) -> Union[dict, None]:
        project_list = [
            'centos-cloud',
            'cos-cloud',
            'debian-cloud',
            'fedora-cloud',
            'opensuse-cloud',
            'rhel-cloud',
            'rocky-linux-cloud',
            'suse-cloud',
            'ubuntu-os-cloud',
            'ubuntu-os-pro-cloud',
            'fedora-coreos-cloud',
        ]

        for project in project_list:
            try:
                return self.details(name, project=project)
            except EmptyResultSet:
                pass

        return None
