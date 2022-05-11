##
##


class gcp(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()

    def get_gcp_zones(self, default=None):
        """Collect GCP availability zones"""
        if not self.gcp_region:
            self.get_gcp_region()
        if len(self.gcp_zone_list) > 0:
            return
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
        self.gcp_zone = self.gcp_zone_list[0]
        for gcp_zone_name in self.gcp_zone_list:
            self.logger.info("Added GCP zone %s" % gcp_zone_name)

    def get_gcp_project(self, default=None):
        """Get GCP Project"""
        inquire = ask()
        project_ids = []
        project_names = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
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
            if self.gcp_auth_json_project_id:
                self.logger.info("Setting project ID to %s" % self.gcp_auth_json_project_id)
                self.gcp_project = self.gcp_auth_json_project_id
                return True
            else:
                self.logger.info("Can not get project ID from auth JSON")
                self.gcp_project = inquire.ask_text('GCP Project ID')
                return True
        selection = inquire.ask_list('GCP Project', project_ids, project_names, default=default)
        self.gcp_project = project_ids[selection]

    def get_gcp_image_user(self, default=None):
        """Get GCP base image user for SSH access"""
        if not self.linux_type:
            try:
                self.get_linux_type()
            except Exception:
                raise
        if not self.linux_release:
            try:
                self.get_linux_release()
            except Exception:
                raise
        for i in range(len(self.local_var_json['linux'][self.linux_type])):
            if self.local_var_json['linux'][self.linux_type][i]['version'] == self.linux_release:
                self.gcp_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable user for %s %s linux." % (self.linux_type, self.linux_release))

    def get_gcp_image_family(self, default=None):
        """Get GCP base image family"""
        if not self.gcp_image_family:
            try:
                self.get_gcp_image_name()
            except Exception:
                raise

    def get_gcp_image_name(self, default=None):
        """Get GCP base image name"""
        if not self.linux_type:
            try:
                self.get_linux_type()
            except Exception:
                raise
        if not self.linux_release:
            try:
                self.get_linux_release()
            except Exception:
                raise
        for i in range(len(self.local_var_json['linux'][self.linux_type])):
            if self.local_var_json['linux'][self.linux_type][i]['version'] == self.linux_release:
                self.gcp_image_name = self.local_var_json['linux'][self.linux_type][i]['image']
                self.gcp_image_family = self.local_var_json['linux'][self.linux_type][i]['family']
                self.gcp_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable image for %s %s linux." % (self.linux_type, self.linux_release))

    def gcp_get_account_file(self, default=None):
        """Get GCP auth JSON file path"""
        inquire = ask()
        dir_list = []
        auth_file_list = []
        auth_directory = os.environ['HOME'] + '/.config/gcloud'

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
            except OSError:
                print("Can not access GCP config file %s" % dir_list[i])
                raise

            if file_type == 'service_account':
                auth_file_list.append(dir_list[i])

        selection = inquire.ask_list('Select GCP auth JSON', auth_file_list, default=default)
        self.gcp_account_file = auth_file_list[selection]

        file_handle = open(self.gcp_account_file, 'r')
        auth_data = json.load(file_handle)
        file_handle.close()
        if 'project_id' in auth_data:
            self.gcp_auth_json_project_id = auth_data['project_id']
        if 'client_email' in auth_data:
            self.gcp_service_account_email = auth_data['client_email']

    def gcp_get_machine_type(self, default=None):
        """Get GCP machine type"""
        inquire = ask()
        machine_type_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_zone:
            self.get_gcp_zones()
        if not self.gcp_project:
            self.get_gcp_project()
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

    def gcp_get_cb_image_name(self, default=None):
        """Select Couchbase GCP image"""
        inquire = ask()
        image_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_project:
            self.get_gcp_project()
        credentials = service_account.Credentials.from_service_account_file(self.gcp_account_file)
        gcp_client = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        request = gcp_client.images().list(project=self.gcp_project)
        while request is not None:
            response = request.execute()
            if "items" in response:
                for image in response['items']:
                    image_block = {}
                    image_block['name'] = image['name']
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
                raise Exception("No images exist in this project")
        selection = inquire.ask_list('GCP Couchbase Image', image_list, default=default)
        self.gcp_cb_image = image_list[selection]['name']
        if 'type' in image_list[selection]:
            self.linux_type = image_list[selection]['type']
            self.logger.info("Selecting linux type %s from image metadata" % self.linux_type)
        if 'release' in image_list[selection]:
            self.linux_release = image_list[selection]['release']
            self.logger.info("Selecting linux release %s from image metadata" % self.linux_release)
        if 'version' in image_list[selection]:
            self.cb_version = image_list[selection]['version']
            self.logger.info("Selecting couchbase version %s from image metadata" % self.cb_version)

    def gcp_get_availability_zone_list(self, default=None):
        """Build GCP availability zone data structure"""
        availability_zone_list = []
        if not self.gcp_region:
            try:
                self.get_gcp_region()
            except Exception:
                raise
        if not self.gcp_subnet:
            try:
                self.gcp_get_subnet()
            except Exception:
                raise
        for zone in self.gcp_zone_list:
            config_block = {}
            config_block['name'] = zone
            config_block['subnet'] = self.gcp_subnet
            availability_zone_list.append(config_block)
        return availability_zone_list

    def gcp_get_subnet(self, default=None):
        """Get GCP subnet"""
        inquire = ask()
        subnet_list = []
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_region:
            self.get_gcp_region()
        if not self.gcp_project:
            self.get_gcp_project()
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

    def gcp_get_root_type(self, default=None):
        """Get GCP root disk type"""
        inquire = ask()
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_type' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_type']
        self.logger.info("Default root type is %s" % default_selection)
        selection = inquire.ask_text('Root volume type', recommendation=default_selection, default=default)
        self.gcp_root_type = selection

    def gcp_get_root_size(self, default=None):
        """Get GCP root disk size"""
        inquire = ask()
        default_selection = ''
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_size']
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', recommendation=default_selection, default=default)
        self.gcp_root_size = selection

    def get_gcp_region(self, default=None):
        """Get GCP region"""
        inquire = ask()
        region_list = []
        current_location = self.get_country()
        if not self.gcp_account_file:
            self.gcp_get_account_file()
        if not self.gcp_project:
            self.get_gcp_project()
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
        self.get_gcp_zones()

