##
##

import logging
import os
import json
import configparser
from Crypto.PublicKey import RSA
import googleapiclient.discovery
from google.oauth2 import service_account
from google.cloud import compute_v1, network_management_v1
from lib.exceptions import GCPDriverError, EmptyResultSet
from typing import Iterable, Union
from itertools import cycle
import lib.config as config


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = False

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auth_directory = os.environ['HOME'] + '/.config/gcloud'
        self.config_default = self.auth_directory + '/configurations/config_default'
        self.gcp_account = None
        self.gcp_project = None
        self.gcp_region = None
        self.gcp_account_file = None
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
        elif not self.gcp_account_file:
            print("Please set GCP_ACCOUNT_FILE to reference the path to your auth json file")
            raise GCPDriverError("can not locate auth file")

        if 'GCP_DEFAULT_REGION' in os.environ:
            self.gcp_region = os.environ['GCP_DEFAULT_REGION']
        elif not self.gcp_region:
            print("Please set GCP_DEFAULT_REGION to specify a GCP region")
            print("Or set your default region with: gcloud config set compute/region region-name")
            raise GCPDriverError("no default region")

        if 'GCP_PROJECT_ID' in os.environ:
            self.gcp_project = os.environ['GCP_PROJECT_ID']
        elif not self.gcp_project:
            file_handle = open(self.gcp_account_file, 'r')
            auth_data = json.load(file_handle)
            file_handle.close()
            if 'project_id' in auth_data:
                gcp_auth_json_project_id = auth_data['project_id']
                self.gcp_project = gcp_auth_json_project_id
            else:
                print("can not determine GCP project, please set GCP_PROJECT_ID")
                raise GCPDriverError("can not determine project ID")

        try:
            credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
            self.gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        except Exception as err:
            raise GCPDriverError(f"error connecting to GCP: {err}")

        self.zones()
        self.set_zone()

    def read_config(self):
        if os.path.exists(self.config_default):
            config = configparser.ConfigParser()
            try:
                config.read(self.config_default)
            except Exception as err:
                raise GCPDriverError(f"can not read config file {self.config_default}: {err}")

            if 'core' in config:
                self.gcp_account = config['core'].get('account', None)
                self.gcp_project = config['core'].get('project', None)

            if 'compute' in config:
                self.gcp_region = config['compute'].get('region', None)

    def zones(self) -> list:
        request = self.gcp_client.zones().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            for zone in response['items']:
                if not zone['name'].startswith(self.gcp_region):
                    continue
                self.gcp_zone_list.append(zone['name'])
            request = self.gcp_client.zones().list_next(previous_request=request, previous_response=response)

        self.gcp_zone_list = sorted(self.gcp_zone_list)

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
                    network_block = {'cidr': network.get('IPv4Range', None),
                                     'name': network['name'],
                                     'description': network.get('description', None),
                                     'subnets': network['subnetworks'],
                                     'id': network['id']}
                    network_list.append(network_block)
                request = self.gcp_client.networks().list_next(previous_request=request, previous_response=response)
        except Exception as err:
            raise GCPDriverError(f"error listing networks: {err}")

        if len(network_list) == 0:
            raise GCPDriverError(f"no networks found")
        else:
            return network_list

    @property
    def cidr_list(self):
        for item in Subnet().list():
            yield item['cidr']

    def create(self, name: str) -> str:
        network_body = {
            "name": name,
            "autoCreateSubnetworks": False
        }
        try:
            operation = self.gcp_client.networks().insert(project=self.gcp_project, body=network_body)
            response = operation.execute()
            return response['name']
        except Exception as err:
            raise GCPDriverError(f"error creating network: {err}")

    def delete(self, network: str) -> None:
        try:
            operation = self.gcp_client.networks().delete(project=self.gcp_project, network=network)
            operation.execute()
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

    def list(self):
        subnet_list = []

        try:
            request = self.gcp_client.subnetworks().list(project=self.gcp_project, region=self.gcp_region)
            while request is not None:
                response = request.execute()
                for subnet in response['items']:
                    subnet_block = {'cidr': subnet['ipCidrRange'],
                                    'name': subnet['name'],
                                    'description': subnet.get('description', None),
                                    'gateway': subnet['gatewayAddress'],
                                    'network': subnet['network'],
                                    'id': subnet['id']}
                    subnet_list.append(subnet_block)
                request = self.gcp_client.subnetworks().list_next(previous_request=request, previous_response=response)
        except Exception as err:
            raise GCPDriverError(f"error listing subnets: {err}")

        if len(subnet_list) == 0:
            raise GCPDriverError(f"no subnets found")
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
            operation = self.gcp_client.subnetworks().insert(project=self.gcp_project, region=self.gcp_region, body=subnetwork_body)
            response = operation.execute()
            return response['name']
        except Exception as err:
            raise GCPDriverError(f"error creating subnet: {err}")

    def delete(self, subnet: str) -> None:
        try:
            operation = self.gcp_client.subnetworks().delete(project=self.gcp_project, region=self.gcp_region, subnetwork=subnet)
            operation.execute()
        except Exception as err:
            raise GCPDriverError(f"error deleting network: {err}")


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
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = vpc
        network_interface.subnetwork = subnet

        disk = compute_v1.AttachedDisk()
        initialize_params = compute_v1.AttachedDiskInitializeParams()
        initialize_params.source_image = image_name
        initialize_params.disk_size_gb = root_size
        initialize_params.disk_type = root_type
        disk.initialize_params = initialize_params
        disk.auto_delete = True
        disk.boot = True

        metadata = compute_v1.Metadata()
        metadata.items = [
            {
                "key": "ssh-keys",
                "value": public_key
            }
        ]

        instance = compute_v1.Instance()
        instance.network_interfaces = [network_interface]
        instance.name = name
        instance.disks = disk
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"
        instance.metadata = metadata

        request = compute_v1.InsertInstanceRequest()
        request.zone = zone
        request.project = self.gcp_project
        request.instance_resource = instance

        try:
            request = self.gcp_client.instances().insert(request=request)
            response = request.execute()
            return response['name']
        except Exception as err:
            raise GCPDriverError(f"error deleting image: {err}")

    def details(self, instance: str, zone: str) -> dict:
        try:
            request = self.gcp_client.images().get(project=self.gcp_project, zone=zone, instance=instance)
            response = request.execute()
        except Exception as err:
            raise GCPDriverError(f"error getting image details: {err}")

        return response

    def terminate(self, instance: str, zone: str) -> None:
        try:
            request = self.gcp_client.images().delete(project=self.gcp_project, zone=zone, instance=instance)
            request.execute()
        except Exception as err:
            raise GCPDriverError(f"error getting image details: {err}")


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def details(self, key_file: str) -> str:
        if not os.path.isabs(key_file):
            pass
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

    def list(self, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        image_list = []

        request = self.gcp_client.images().list(project=self.gcp_project)

        while request is not None:
            try:
                response = request.execute()
            except Exception as err:
                raise GCPDriverError(f"error getting images: {err}")
            for image in response['items']:
                image_block = {'name': image['name'],
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

    def details(self, image: str) -> dict:
        try:
            request = self.gcp_client.images().get(project=self.gcp_project, image=image)
            image = request.execute()
        except Exception as err:
            raise GCPDriverError(f"error getting image details: {err}")

        image_block = {'name': image['name'],
                       'date': image['creationTimestamp']}
        image_block.update(self.process_labels(image))

        return image_block

    def create(self, name: str, source_image: str, description=None, root_type="pd-ssd", root_size=100) -> str:
        image_body = {
            "name": name,
            "description": description if description else "",
            "sourceImage": f"/global/images/{source_image}",
            "diskSizeGb": root_size,
        }
        try:
            request = self.gcp_client.images().insert(project=self.gcp_project, body=image_body)
            response = request.execute()
        except Exception as err:
            raise GCPDriverError(f"error creating image: {err}")

        return response['name']

    def delete(self, image: str) -> None:
        try:
            request = self.gcp_client.images().delete(project=self.gcp_project, image=image)
            request.execute()
        except Exception as err:
            raise GCPDriverError(f"error deleting image: {err}")
