##
##

import logging
import googleapiclient.discovery
from google.oauth2 import service_account
import json
from typing import Union
from lib.varfile import varfile
from lib.toolbox import toolbox
from lib.ask import ask
from lib.exceptions import *


class gcp(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()

    def get_gcp_zones(self, gcp_account_file: str, gcp_region: str, gcp_project: str) -> list[str]:
        """Collect GCP availability zones"""
        gcp_zone_list = []

        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.zones().list(project=gcp_project)
        while request is not None:
            response = request.execute()
            for zone in response['items']:
                if not zone['name'].startswith(gcp_region):
                    continue
                gcp_zone_list.append(zone['name'])
            request = gcp_client.zones().list_next(previous_request=request, previous_response=response)
        gcp_zone_list = sorted(gcp_zone_list)
        for gcp_zone_name in gcp_zone_list:
            self.logger.info("Added GCP zone %s" % gcp_zone_name)
        return gcp_zone_list

    def get_gcp_project(self, gcp_account_file: str, default=None) -> str:
        """Get GCP Project"""
        inquire = ask()
        project_ids = []
        project_names = []

        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
        request = gcp_client.projects().list()
        while request is not None:
            response = request.execute()
            for project in response.get('projects', []):
                project_ids.append(project['projectId'])
                project_names.append(project['name'])
            request = gcp_client.projects().list_next(previous_request=request, previous_response=response)
        if len(project_ids) == 0:
            self.logger.info("Insufficient permissions to list projects, attempting to get project ID from auth JSON")
            gcp_auth_json_project_id = self.gcp_get_project_id(gcp_account_file)
            self.logger.info("Setting project ID to %s" % gcp_auth_json_project_id)
            return gcp_auth_json_project_id

        selection = inquire.ask_list('GCP Project', project_ids, project_names, default=default)
        return project_ids[selection]

    def gcp_get_account_file(self, default=None) -> str:
        """Get GCP auth JSON file path"""
        candidate_file = None
        inquire = ask()
        dir_list = []
        auth_file_list = []
        auth_directory = os.environ['HOME'] + '/.config/gcloud'

        if 'GCP_ACCOUNT_FILE' in os.environ:
            candidate_file = os.environ['GCP_ACCOUNT_FILE']

        for file_name in os.listdir(auth_directory):
            if file_name.lower().endswith('.json'):
                full_path = auth_directory + '/' + file_name
                dir_list.append(full_path)

        for i in range(len(dir_list)):
            file_handle = open(dir_list[i], 'r')

            try:
                json_data = json.load(file_handle)
                file_type = json_data['type']
                file_handle.close()
            except (ValueError, KeyError):
                continue
            except OSError as err:
                raise GCPDriverError(f"Can not access GCP config file {dir_list[i]}: {err}")

            if candidate_file:
                entry_file_name = os.path.basename(dir_list[i])
                if candidate_file == entry_file_name:
                    return dir_list[i]

            if file_type == 'service_account':
                auth_file_list.append(dir_list[i])

        selection = inquire.ask_list('Select GCP auth JSON', auth_file_list, default=default)
        return auth_file_list[selection]

    def gcp_get_project_id(self, gcp_account_file: str, default=None) -> str:
        inquire = ask()

        if 'GCP_PROJECT_ID' in os.environ:
            return os.environ['GCP_PROJECT_ID']

        file_handle = open(gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'project_id' in auth_data:
            gcp_auth_json_project_id = auth_data['project_id']
            return gcp_auth_json_project_id
        else:
            selection = inquire.ask_text('GCP Project', default=default)
            return selection

    def gcp_get_account_email(self, gcp_account_file: str, default=None) -> str:
        inquire = ask()

        file_handle = open(gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'client_email' in auth_data:
            gcp_service_account_email = auth_data['client_email']
            return gcp_service_account_email
        else:
            selection = inquire.ask_text('GCP Client Email', default=default)
            return selection

    def gcp_get_machine_type(self, gcp_account_file: str, gcp_project: str, gcp_zone: str, default=None) -> str:
        """Get GCP machine type"""
        inquire = ask()
        machine_type_list = []

        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.machineTypes().list(project=gcp_project, zone=gcp_zone)
        while request is not None:
            response = request.execute()
            for machine_type in response['items']:
                config_block = {}
                config_block['name'] = machine_type['name']
                config_block['cpu'] = int(machine_type['guestCpus'])
                config_block['mem'] = int(machine_type['memoryMb'])
                config_block['description'] = machine_type['description']
                machine_type_list.append(config_block)
            request = gcp_client.machineTypes().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_machine_type('GCP Machine Type', machine_type_list, default=default)
        return machine_type_list[selection]['name']

    def gcp_get_cb_image_name(self, gcp_account_file: str, gcp_project: str, select=True, default=None) -> Union[dict, list[dict]]:
        """Select Couchbase GCP image"""
        inquire = ask()
        image_list = []

        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.images().list(project=gcp_project)
        while request is not None:
            response = request.execute()
            if "items" in response:
                for image in response['items']:
                    image_block = {}
                    image_block['name'] = image['name']
                    image_block['date'] = image['creationTimestamp']
                    if 'labels' in image:
                        if 'type' in image['labels']:
                            image_block['type'] = image['labels']['type']
                        if 'release' in image['labels']:
                            image_block['release'] = image['labels']['release']
                        if 'version' in image['labels']:
                            image_block['version'] = image_block['description'] = image['labels']['version'].replace("_", ".")
                    image_list.append(image_block)
                request = gcp_client.images().list_next(previous_request=request, previous_response=response)
            else:
                raise GCPDriverError("No images exist in this project")
        if select:
            selection = inquire.ask_list('GCP Couchbase Image', image_list, default=default)
            return image_list[selection]
        else:
            return image_list

    def gcp_get_availability_zone_list(self, gcp_zone_list: list, gcp_subnet: str) -> list[dict]:
        """Build GCP availability zone data structure"""
        availability_zone_list = []

        for zone in gcp_zone_list:
            config_block = {}
            config_block['name'] = zone
            config_block['subnet'] = gcp_subnet
            availability_zone_list.append(config_block)
        return availability_zone_list

    def gcp_get_subnet(self, gcp_account_file: str, gcp_project: str, gcp_region: str, default=None) -> str:
        """Get GCP subnet"""
        inquire = ask()
        subnet_list = []

        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.subnetworks().list(project=gcp_project, region=gcp_region)
        while request is not None:
            response = request.execute()
            for subnet in response['items']:
                subnet_list.append(subnet['name'])
            request = gcp_client.subnetworks().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_list('GCP Subnet', subnet_list, default=default)
        return subnet_list[selection]

    def gcp_get_root_type(self, default=None) -> str:
        """Get GCP root disk type"""
        inquire = ask()

        default_selection = self.vf.gcp_get_default('root_type')
        self.logger.info("Default root type is %s" % default_selection)
        selection = inquire.ask_text('Root volume type', recommendation=default_selection, default=default)
        return selection

    def gcp_get_root_size(self, default=None) -> str:
        """Get GCP root disk size"""
        inquire = ask()

        default_selection = self.vf.gcp_get_default('root_size')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', recommendation=default_selection, default=default)
        return selection

    def get_gcp_region(self, gcp_account_file: str, gcp_project: str, default=None) -> str:
        """Get GCP region"""
        inquire = ask()
        tb = toolbox()

        if 'GCP_DEFAULT_REGION' in os.environ:
            return os.environ['GCP_DEFAULT_REGION']

        region_list = []
        current_location = tb.get_country()
        credentials = service_account.Credentials.from_service_account_file(gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.regions().list(project=gcp_project)
        while request is not None:
            response = request.execute()
            for region in response['items']:
                if current_location:
                    if current_location.lower() == 'us':
                        if not region['name'].startswith('us'):
                            continue
                    else:
                        if region['name'].startswith('us'):
                            continue
                region_list.append(region['name'])
            request = gcp_client.regions().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_list('GCP Region', region_list, default=default)
        return region_list[selection]
