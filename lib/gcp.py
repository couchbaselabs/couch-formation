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
from lib.prereq import prereq


class gcp(object):
    VARIABLES = [
        ('GCP_ACCOUNT_FILE', 'gcp_account_file', 'gcp_get_account_file', None),
        ('GCP_CB_IMAGE', 'gcp_cb_image', 'gcp_get_cb_image_name', None),
        ('GCP_MACHINE_TYPE', 'gcp_machine_type', 'gcp_get_machine_type', None),
        ('GCP_PROJECT', 'gcp_project', 'gcp_get_project_id', None),
        ('GCP_REGION', 'gcp_region', 'get_gcp_region', None),
        ('GCP_ROOT_SIZE', 'gcp_disk_size', 'gcp_get_root_size', None),
        ('GCP_ROOT_TYPE', 'gcp_disk_type', 'gcp_get_root_type', None),
        ('GCP_SA_EMAIL', 'gcp_service_account_email', 'gcp_get_account_email', None),
        ('GCP_SUBNET', 'gcp_subnet', 'gcp_get_subnet', None),
        ('GCP_ZONE', 'gcp_zone', 'get_gcp_zones', None),
        ('GCP_MARKET_IMAGE', 'gcp_market_image', 'gcp_get_market_image_name', None),
        ('GCP_IMAGE_PROJECT', 'gcp_image_project', 'gcp_get_image_project', None),
    ]
    PREREQUISITES = {
        'gcp_get_availability_zone_list': [
            'gcp_get_subnet'
        ]
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()
        self.gcp_account_file = None
        self.gcp_project = None
        self.gcp_zone_list = []
        self.gcp_region = None
        self.gcp_zone = None
        self.gcp_service_account_email = None
        self.gcp_machine_type = None
        self.gcp_cb_image = None
        self.gcp_subnet = None
        self.gcp_root_size = None
        self.gcp_root_type = None
        self.gcp_cb_image = None
        self.gcp_market_image = None
        self.gcp_image_project = None

    def gcp_init(self):
        try:
            self.gcp_get_account_file()
            self.gcp_get_project_id()
        except Exception as err:
            raise GCPDriverError(f"can not access GCP API: {err}")

    def gcp_prep(self, select=True):
        try:
            self.get_gcp_region()
            self.get_gcp_zones(select=select)
        except Exception as err:
            raise GCPDriverError(f"GCP prep error: {err}")

    def get_gcp_zones(self, select=True, default=None, write=None) -> str:
        """Collect GCP availability zones"""
        inquire = ask()

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.zones().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            for zone in response['items']:
                if not zone['name'].startswith(self.gcp_region):
                    continue
                self.gcp_zone_list.append(zone['name'])
            request = gcp_client.zones().list_next(previous_request=request, previous_response=response)
        self.gcp_zone_list = sorted(self.gcp_zone_list)
        for gcp_zone_name in self.gcp_zone_list:
            self.logger.info("Added GCP zone %s" % gcp_zone_name)

        if write:
            self.gcp_zone = write
            return self.gcp_zone

        if self.gcp_zone:
            return self.gcp_zone

        if select:
            selection = inquire.ask_list('GCP Zone', self.gcp_zone_list, default=default)
            self.gcp_zone = self.gcp_zone_list[selection]
        else:
            self.gcp_zone = self.gcp_zone_list[0]

        return self.gcp_zone

    def get_gcp_project(self, default=None, write=None) -> str:
        """Get GCP Project"""
        inquire = ask()
        project_ids = []
        project_names = []

        if write:
            self.gcp_project = write
            return self.gcp_project

        if self.gcp_project:
            return self.gcp_project

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
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
            gcp_auth_json_project_id = self.gcp_get_project_id()
            self.logger.info("Setting project ID to %s" % gcp_auth_json_project_id)
            return self.gcp_project

        selection = inquire.ask_list('GCP Project', project_ids, project_names, default=default)
        self.gcp_project = project_ids[selection]
        return self.gcp_project

    def gcp_get_account_file(self, default=None, write=None) -> str:
        """Get GCP auth JSON file path"""
        candidate_file = None
        inquire = ask()
        dir_list = []
        auth_file_list = []
        auth_directory = os.environ['HOME'] + '/.config/gcloud'

        if write:
            self.gcp_account_file = write
            return self.gcp_account_file

        if self.gcp_account_file:
            return self.gcp_account_file

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
                    self.gcp_account_file = dir_list[i]
                    return self.gcp_account_file

            if file_type == 'service_account':
                auth_file_list.append(dir_list[i])

        selection = inquire.ask_list('Select GCP auth JSON', auth_file_list, default=default)
        self.gcp_account_file = auth_file_list[selection]
        return self.gcp_account_file

    def gcp_get_project_id(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.gcp_project = write
            return self.gcp_project

        if self.gcp_project:
            return self.gcp_project

        if 'GCP_PROJECT_ID' in os.environ:
            self.gcp_project = os.environ['GCP_PROJECT_ID']
            return self.gcp_project

        file_handle = open(self.gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'project_id' in auth_data:
            gcp_auth_json_project_id = auth_data['project_id']
            self.gcp_project = gcp_auth_json_project_id
        else:
            selection = inquire.ask_text('GCP Project', default=default)
            self.gcp_project = selection

        return self.gcp_project

    def gcp_get_account_email(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.gcp_service_account_email = write
            return self.gcp_service_account_email

        if self.gcp_service_account_email:
            return self.gcp_service_account_email

        file_handle = open(self.gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'client_email' in auth_data:
            self.gcp_service_account_email = auth_data['client_email']
        else:
            self.gcp_service_account_email = inquire.ask_text('GCP Client Email', default=default)

        return self.gcp_service_account_email

    def gcp_get_machine_type(self, default=None, write=None) -> str:
        """Get GCP machine type"""
        inquire = ask()
        machine_type_list = []

        if write:
            self.gcp_machine_type = write
            return self.gcp_machine_type

        if self.gcp_machine_type:
            return self.gcp_machine_type

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.machineTypes().list(project=self.gcp_project, zone=self.gcp_zone)
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
        self.gcp_machine_type = machine_type_list[selection]['name']
        return self.gcp_machine_type

    def gcp_get_market_image_name(self, select=True, default=None, write=None) -> dict:
        """Select GCP image"""
        inquire = ask()
        image_list = []
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

        if write:
            self.gcp_market_image = write
            return self.gcp_market_image

        if self.gcp_market_image:
            return self.gcp_market_image

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

        for project in project_list:
            request = gcp_client.images().list(project=project)
            while request is not None:
                response = request.execute()
                if "items" in response:
                    for image in response['items']:
                        if 'deprecated' in image:
                            if (image['deprecated']['state'] == "DEPRECATED") or (image['deprecated']['state'] == "OBSOLETE"):
                                continue
                        image_block = {}
                        image_block['name'] = image['name']
                        image_block['date'] = image['creationTimestamp']
                        image_block['project'] = project
                        image_list.append(image_block)
                    request = gcp_client.images().list_next(previous_request=request, previous_response=response)
                else:
                    raise GCPDriverError("No images exist")

        if select:
            selection = inquire.ask_list('GCP Image', image_list, default=default)
            self.gcp_market_image = image_list[selection]
            self.gcp_image_project = image_list[selection]['project']
        else:
            self.gcp_market_image = image_list

        return self.gcp_market_image

    @prereq(requirements=('gcp_get_market_image_name',))
    def gcp_get_image_project(self, default=None, write=None) -> str:
        if write:
            self.gcp_image_project = write
            return self.gcp_image_project

        return self.gcp_image_project

    def gcp_get_cb_image_name(self, select=True, default=None, write=None) -> Union[dict, list[dict]]:
        """Select Couchbase GCP image"""
        inquire = ask()
        image_list = []

        if write:
            self.gcp_cb_image = write
            return self.gcp_cb_image

        if self.gcp_cb_image:
            return self.gcp_cb_image

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.images().list(project=self.gcp_project)
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
                    if 'type' not in image_block or 'release' not in image_block:
                        continue
                    image_list.append(image_block)
                request = gcp_client.images().list_next(previous_request=request, previous_response=response)
            else:
                raise GCPDriverError("No images exist in this project")
        if select:
            selection = inquire.ask_list('GCP Couchbase Image', image_list, default=default)
            self.gcp_cb_image = image_list[selection]
        else:
            self.gcp_cb_image = image_list

        return self.gcp_cb_image

    @prereq(requirements=('gcp_get_cb_image_name',))
    def get_image(self):
        return self.gcp_cb_image

    @prereq(requirements=('gcp_get_market_image_name',))
    def get_market_image(self):
        return self.gcp_market_image

    def gcp_delete_cb_image(self, name: str):
        inquire = ask()

        if inquire.ask_yn(f"Delete image {name}", default=True):
            credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
            gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
            request = gcp_client.images().delete(project=self.gcp_project, image=name)
            response = request.execute()
            if 'error' in response:
                raise GCPDriverError(f"can not delete {name}: {response['error']['errors'][0]['message']}")

    @prereq(requirements=('gcp_get_subnet',))
    def gcp_get_availability_zone_list(self) -> list[dict]:
        """Build GCP availability zone data structure"""
        availability_zone_list = []

        for zone in self.gcp_zone_list:
            config_block = {}
            config_block['name'] = zone
            config_block['subnet'] = self.gcp_subnet
            availability_zone_list.append(config_block)
        return availability_zone_list

    def gcp_get_subnet(self, default=None, write=None) -> str:
        """Get GCP subnet"""
        inquire = ask()
        subnet_list = []

        if write:
            self.gcp_subnet = write
            return self.gcp_subnet

        if self.gcp_subnet:
            return self.gcp_subnet

        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.subnetworks().list(project=self.gcp_project, region=self.gcp_region)
        while request is not None:
            response = request.execute()
            for subnet in response['items']:
                subnet_list.append(subnet['name'])
            request = gcp_client.subnetworks().list_next(previous_request=request, previous_response=response)
        selection = inquire.ask_list('GCP Subnet', subnet_list, default=default)
        self.gcp_subnet = subnet_list[selection]
        return self.gcp_subnet

    def gcp_get_root_type(self, default=None, write=None) -> str:
        """Get GCP root disk type"""
        inquire = ask()
        gcp_type_list = [
            'pd-standard',
            'pd-balanced',
            'pd-ssd',
            'pd-extreme',
        ]

        if write:
            self.gcp_root_type = write
            return self.gcp_root_type

        if self.gcp_root_type:
            return self.gcp_root_type

        default_selection = self.vf.gcp_get_default('root_type')
        self.logger.info("Default root type is %s" % default_selection)
        selection = inquire.ask_list('Root volume type', gcp_type_list, default=default_selection)
        self.gcp_root_type = gcp_type_list[selection]
        return self.gcp_root_type

    def gcp_get_root_size(self, default=None, write=None) -> str:
        """Get GCP root disk size"""
        inquire = ask()

        if write:
            self.gcp_root_size = write
            return self.gcp_root_size

        if self.gcp_root_size:
            return self.gcp_root_size

        default_selection = self.vf.gcp_get_default('root_size')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', recommendation=default_selection, default=default)
        self.gcp_root_size = selection
        return self.gcp_root_size

    def get_gcp_region(self, default=None, write=None) -> str:
        """Get GCP region"""
        inquire = ask()
        tb = toolbox()

        if write:
            self.gcp_region = write
            return self.gcp_region

        if self.gcp_region:
            return self.gcp_region

        if 'GCP_DEFAULT_REGION' in os.environ:
            self.gcp_region = os.environ['GCP_DEFAULT_REGION']
            return os.environ['GCP_DEFAULT_REGION']

        region_list = []
        current_location = tb.get_country()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.regions().list(project=self.gcp_project)
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
        self.gcp_region = region_list[selection]
        return self.gcp_region
