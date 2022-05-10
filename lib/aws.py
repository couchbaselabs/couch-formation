##
##

import logging
from lib.ask import ask
from lib.varfile import varfile


class aws(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()

    def aws_get_root_type(self, default=None):
        """Get root volume type"""
        inquire = ask()
        default_selection = None
        if 'defaults' in self.local_var_json:
            if 'root_type' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_type']
        self.logger.info("Default root type is %s" % default_selection)
        selection = inquire.ask_text('Root volume type', default_selection, default=default)
        self.aws_root_type = selection


    def aws_get_root_size(self, default=None):
        """Get root volume size"""
        inquire = ask()
        default_selection = None
        if 'defaults' in self.local_var_json:
            if 'root_size' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_size']
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', default_selection, default=default)
        self.aws_root_size = selection


    def aws_get_root_iops(self, default=None):
        """Get IOPS for root volume"""
        inquire = ask()
        default_selection = None
        if 'defaults' in self.local_var_json:
            if 'root_iops' in self.local_var_json['defaults']:
                default_selection = self.local_var_json['defaults']['root_iops']
        self.logger.info("Default root IOPS is %s" % default_selection)
        selection = inquire.ask_text('Root volume IOPS', default_selection, default=default)
        self.aws_root_iops = selection


    def aws_get_sg_id(self, default=None):
        """Get AWS security group ID"""
        inquire = ask()
        if not self.aws_vpc_id:
            try:
                self.aws_get_vpc_id()
            except Exception:
                raise
        sg_list = []
        sg_name_list = []
        if type(default) == list:
            default = default[0]
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                self.aws_vpc_id,
            ]
        }
        sgs = ec2_client.describe_security_groups(Filters=[vpc_filter, ])
        for i in range(len(sgs['SecurityGroups'])):
            sg_list.append(sgs['SecurityGroups'][i]['GroupId'])
            sg_name_list.append(sgs['SecurityGroups'][i]['GroupName'])

        selection = inquire.ask_list('Select security group', sg_list, sg_name_list, default=default)
        self.aws_sg_id = sgs['SecurityGroups'][selection]['GroupId']


    def aws_get_vpc_id(self, default=None):
        """Get AWS VPC ID"""
        inquire = ask()
        vpc_list = []
        vpc_name_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpcs = ec2_client.describe_vpcs()
        for i in range(len(vpcs['Vpcs'])):
            vpc_list.append(vpcs['Vpcs'][i]['VpcId'])
            item_name = ''
            if 'Tags' in vpcs['Vpcs'][i]:
                item_tag = self.aws_get_tag('Name', vpcs['Vpcs'][i]['Tags'])
                if item_tag:
                    item_name = item_tag
            vpc_name_list.append(item_name)

        selection = inquire.ask_list('Select VPC', vpc_list, vpc_name_list, default=default)
        self.aws_vpc_id = vpcs['Vpcs'][selection]['VpcId']


    def aws_get_availability_zone_list(self, default=None):
        """Build subnet list by availability zones"""
        availability_zone_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        for zone in self.aws_availability_zones:
            config_block = {}
            config_block['name'] = zone
            self.aws_get_subnet_id(zone, default=default)
            config_block['subnet'] = self.aws_subnet_id
            availability_zone_list.append(config_block)
        return availability_zone_list


    def aws_get_subnet_id(self, availability_zone=None, default=None):
        """Get AWS subnet ID"""
        inquire = ask()
        if not self.aws_vpc_id:
            try:
                self.aws_get_vpc_id()
            except Exception:
                raise
        subnet_list = []
        subnet_name_list = []
        filter_list = []
        question = "AWS Select Subnet"
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                self.aws_vpc_id,
            ]
        }
        filter_list.append(vpc_filter)
        if availability_zone:
            self.logger.info("AWS: Subnet: Filtering subnets by AZ %s" % availability_zone)
            question = question + " for zone {}".format(availability_zone)
            zone_filter = {
                'Name': 'availability-zone',
                'Values': [
                    availability_zone,
                ]
            }
            filter_list.append(zone_filter)
        self.logger.info("AWS: Subnet: Use public IP is %s" % self.use_public_ip)
        subnets = ec2_client.describe_subnets(Filters=filter_list)
        for i in range(len(subnets['Subnets'])):
            if self.use_public_ip and not subnets['Subnets'][i]['MapPublicIpOnLaunch']:
                continue
            elif not self.use_public_ip and subnets['Subnets'][i]['MapPublicIpOnLaunch']:
                continue
            self.logger.info("AWS: Subnet: Found subnet %s" % subnets['Subnets'][i]['SubnetId'])
            subnet_list.append(subnets['Subnets'][i]['SubnetId'])
            item_name = ''
            if 'Tags' in subnets['Subnets'][i]:
                item_tag = self.aws_get_tag('Name', subnets['Subnets'][i]['Tags'])
                if item_tag:
                    item_name = item_tag
            subnet_name_list.append(item_name)

        selection = inquire.ask_list(question, subnet_list, subnet_name_list, default=default)
        self.aws_subnet_id = subnet_list[selection]

    def aws_get_ssh_key(self, default=None):
        """Get the AWS SSH key pair to use for node access"""
        inquire = ask()
        key_list = []
        key_id_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        key_pairs = ec2_client.describe_key_pairs()
        for i in range(len(key_pairs['KeyPairs'])):
            key_list.append(key_pairs['KeyPairs'][i]['KeyName'])
            key_id_list.append(key_pairs['KeyPairs'][i]['KeyPairId'])

        selection = inquire.ask_list('Select SSH key', key_list, key_id_list, default=default)
        self.aws_ssh_key = key_pairs['KeyPairs'][selection]['KeyName']
        self.ssh_key_fingerprint = key_pairs['KeyPairs'][selection]['KeyFingerprint']

    def aws_get_instance_type(self, default=None):
        """Get the AWS instance type"""
        inquire = ask()
        size_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        describe_args = {}
        while True:
            instance_types = ec2_client.describe_instance_types(**describe_args)
            for machine_type in instance_types['InstanceTypes']:
                config_block = {}
                config_block['name'] = machine_type['InstanceType']
                config_block['cpu'] = int(machine_type['VCpuInfo']['DefaultVCpus'])
                config_block['mem'] = int(machine_type['MemoryInfo']['SizeInMiB'])
                config_block['description'] = ",".join(machine_type['ProcessorInfo']['SupportedArchitectures']) \
                                              + ' ' + str(machine_type['ProcessorInfo']['SustainedClockSpeedInGhz']) + 'GHz' \
                                              + ', Network: ' + machine_type['NetworkInfo']['NetworkPerformance'] \
                                              + ', Hypervisor: ' + machine_type['Hypervisor'] if 'Hypervisor' in machine_type else 'NA'
                size_list.append(config_block)
            if 'NextToken' not in instance_types:
                break
            describe_args['NextToken'] = instance_types['NextToken']
        selection = inquire.ask_machine_type('AWS Instance Type', size_list, default=default)
        self.aws_instance_type = size_list[selection]['name']

    def aws_get_ami_id(self, default=None):
        """Get the Couchbase AMI to use"""
        inquire = ask()
        image_list = []
        image_name_list = []
        if not self.aws_region:
            try:
                self.aws_get_region()
            except Exception:
                raise
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        images = ec2_client.describe_images(Owners=['self'])
        for i in range(len(images['Images'])):
            image_block = {}
            image_block['name'] = images['Images'][i]['ImageId']
            image_block['description'] = images['Images'][i]['Name']
            if 'Tags' in images['Images'][i]:
                item_release_tag = self.aws_get_tag('Release', images['Images'][i]['Tags'])
                item_type_tag = self.aws_get_tag('Type', images['Images'][i]['Tags'])
                item_version_tag = self.aws_get_tag('Version', images['Images'][i]['Tags'])
                if item_type_tag:
                    image_block['type'] = item_type_tag
                if item_release_tag:
                    image_block['release'] = item_release_tag
                if item_version_tag:
                    image_block['version'] = item_version_tag
                    image_block['description'] = image_block['description'] + ' => Version: ' + item_version_tag
            image_list.append(image_block)
        selection = inquire.ask_list('Select AMI', image_list, default=default)
        self.aws_ami_id = image_list[selection]['name']
        if 'type' in image_list[selection]:
            self.linux_type = image_list[selection]['type']
            self.logger.info("Selecting linux type %s from image metadata" % self.linux_type)
        if 'release' in image_list[selection]:
            self.linux_release = image_list[selection]['release']
            self.logger.info("Selecting linux release %s from image metadata" % self.linux_release)
        if 'version' in image_list[selection]:
            self.cb_version = image_list[selection]['version']
            self.logger.info("Selecting couchbase version %s from image metadata" % self.cb_version)

    def aws_get_region(self, default=None):
        """Get the AWS Region"""
        inquire = ask()
        if 'AWS_REGION' in os.environ:
            self.aws_region = os.environ['AWS_REGION']
        elif 'AWS_DEFAULT_REGION' in os.environ:
            self.aws_region = os.environ['AWS_DEFAULT_REGION']
        elif boto3.DEFAULT_SESSION:
            self.aws_region = boto3.DEFAULT_SESSION.region_name
        elif boto3.Session().region_name:
            self.aws_region = boto3.Session().region_name

        if not self.aws_region:
            selection = inquire.ask_text('AWS Region', default=default)
            self.aws_region = selection

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        zone_list = ec2_client.describe_availability_zones()
        for availability_zone in zone_list['AvailabilityZones']:
            self.logger.info("Added availability zone %s" % availability_zone['ZoneName'])
            self.aws_availability_zones.append(availability_zone['ZoneName'])

    def get_aws_image_user(self, default=None):
        """Get the account name to use for SSH to the base AMI"""
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
                self.aws_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate ssh user for %s %s linux." % (self.linux_type, self.linux_release))

    def get_aws_image_owner(self, default=None):
        """Get the AWS base image owner as it is required by Packer"""
        if not self.aws_image_owner:
            try:
                self.get_aws_image_name()
            except Exception:
                raise

    def get_aws_image_name(self, default=None):
        """Get the base AWS AMI to use to build the Couchbase AMI"""
        inquire = ask()
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
                self.aws_image_name = self.local_var_json['linux'][self.linux_type][i]['image']
                self.aws_image_owner = self.local_var_json['linux'][self.linux_type][i]['owner']
                self.aws_image_user = self.local_var_json['linux'][self.linux_type][i]['user']
                return True
        raise Exception("Can not locate suitable image for %s %s linux." % (self.linux_type, self.linux_release))

    def aws_tag_exists(self, key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return True
        return False

    def aws_get_tag(self, key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return tags[i]['Value']
        return None
