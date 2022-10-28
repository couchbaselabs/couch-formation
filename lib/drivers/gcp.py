##
##

import logging
import os
import json
import configparser
import googleapiclient.discovery
from google.oauth2 import service_account
from lib.exceptions import GCPDriverError


class GCPBase(object):

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


class GCPNetwork(GCPBase):

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


class GCPSubnet(GCPBase):

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


class GCPMachineType(GCPBase):

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
