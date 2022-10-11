##
##

import logging
import boto3
import os
import re
from lib.exceptions import AWSDriverError
from typing import Union
from lib.ask import ask
from lib.varfile import varfile
from lib.prereq import prereq


class aws(object):
    TEMPLATE = True
    VARIABLES = [
        ('AWS_AMI_ID', 'ami_id', 'aws_get_ami_id', None),
        ('AWS_INSTANCE_TYPE', 'instance_type', 'aws_get_instance_type', None),
        ('AWS_REGION', 'region_name', 'aws_get_region', None),
        ('AWS_ROOT_IOPS', 'root_volume_iops', 'aws_get_root_iops', None),
        ('AWS_ROOT_SIZE', 'root_volume_size', 'aws_get_root_size', None),
        ('AWS_ROOT_TYPE', 'root_volume_type', 'aws_get_root_type', None),
        ('AWS_SECURITY_GROUP', 'security_group_ids', 'aws_get_sg_id', None),
        ('AWS_SSH_KEY', 'ssh_key', 'aws_get_ssh_key', None),
        ('AWS_SUBNET_ID', 'subnet_id', 'aws_get_subnet_id', None),
        ('AWS_VPC_ID', 'vpc_id', 'aws_get_vpc_id', None),
        ('AWS_MARKET_NAME', 'aws_market_name', 'aws_get_market_ami', None),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()
        self.aws_region = None
        self.aws_availability_zones = []
        self.use_public_ip = True
        self.aws_vpc_id = None
        self.os_name = None
        self.os_ver = None
        self.ssh_key_fingerprint = None
        self.aws_root_iops = None
        self.aws_root_size = None
        self.aws_root_type = None
        self.aws_sg_id = None
        self.aws_subnet_id = None
        self.aws_ssh_key = None
        self.aws_instance_type = None
        self.aws_ami_id = None
        self.aws_ami_name = None
        self.aws_market_ami = None

    def aws_init(self):
        self.aws_get_region()
        try:
            self.aws_get_region_zones()
        except Exception as err:
            raise AWSDriverError(f"can not access AWS API: {err}")

    def aws_get_root_type(self, default=None, write=None) -> str:
        """Get root volume type"""
        inquire = ask()
        aws_type_list = [
            'io2',
            'gp2',
            'gp3',
        ]

        if write:
            self.aws_root_type = write
            return self.aws_root_type

        if self.aws_root_type:
            return self.aws_root_type

        default_selection = self.vf.aws_get_default('root_type')
        self.logger.info("Default root type is %s" % default_selection)
        selection = inquire.ask_list('Root volume type', aws_type_list, default=default_selection)
        self.aws_root_type = aws_type_list[selection]
        return self.aws_root_type

    def aws_get_root_size(self, default=None, write=None) -> str:
        """Get root volume size"""
        inquire = ask()

        if write:
            self.aws_root_size = write
            return self.aws_root_size

        if self.aws_root_size:
            return self.aws_root_size

        default_selection = self.vf.aws_get_default('root_size')
        self.logger.info("Default root size is %s" % default_selection)
        selection = inquire.ask_text('Root volume size', default_selection, default=default)
        self.aws_root_size = selection
        return self.aws_root_size

    def aws_get_root_iops(self, default=None, write=None) -> str:
        """Get IOPS for root volume"""
        inquire = ask()

        if write:
            self.aws_root_iops = write
            return self.aws_root_iops

        if self.aws_root_iops:
            return self.aws_root_iops

        default_selection = self.vf.aws_get_default('root_iops')
        self.logger.info("Default root IOPS is %s" % default_selection)
        selection = inquire.ask_text('Root volume IOPS', default_selection, default=default)
        self.aws_root_iops = selection
        return self.aws_root_iops

    @prereq(requirements=('aws_get_vpc_id',))
    def aws_get_sg_id(self, default=None, write=None) -> list:
        """Get AWS security group ID"""
        inquire = ask()

        if write:
            self.aws_sg_id = [write]
            return self.aws_sg_id

        if self.aws_sg_id:
            return self.aws_sg_id

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
        self.aws_sg_id = [sgs['SecurityGroups'][selection]['GroupId']]
        return self.aws_sg_id

    def aws_get_vpc_id(self, default=None, write=None) -> str:
        """Get AWS VPC ID"""
        inquire = ask()
        vpc_list = []
        vpc_name_list = []

        if write:
            self.aws_vpc_id = write
            return self.aws_vpc_id

        if self.aws_vpc_id:
            return self.aws_vpc_id

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
        return self.aws_vpc_id

    def aws_get_availability_zone_list(self) -> list:
        """Build subnet list by availability zones"""
        availability_zone_list = []

        for zone in self.aws_availability_zones:
            config_block = {}
            config_block['name'] = zone
            aws_subnet_id = self.aws_get_subnet_id(availability_zone=zone)
            if aws_subnet_id is None:
                continue
            config_block['subnet'] = aws_subnet_id
            availability_zone_list.append(config_block)

        if len(availability_zone_list) == 0:
            print("Can not find a suitable subnet.")
            print("If you have Public IP enabled, make sure you have subnets with Public IP enabled.")
            raise AWSDriverError("No suitable subnets")

        return availability_zone_list

    def aws_get_subnet_id(self, availability_zone=None, default=None, write=None) -> Union[str, None]:
        """Get AWS subnet ID"""
        inquire = ask()

        if write:
            self.aws_subnet_id = write
            return self.aws_subnet_id

        # if self.aws_subnet_id:
        #     return self.aws_subnet_id

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

        if len(subnet_list) == 0:
            return None

        selection = inquire.ask_list(question, subnet_list, subnet_name_list, default=default)
        self.aws_subnet_id = subnet_list[selection]
        return self.aws_subnet_id

    def aws_get_ssh_key(self, default=None, write=None) -> str:
        """Get the AWS SSH key pair to use for node access"""
        inquire = ask()
        key_list = []
        key_id_list = []

        if write:
            self.aws_ssh_key = write
            return self.aws_ssh_key

        if self.aws_ssh_key:
            return self.aws_ssh_key

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        key_pairs = ec2_client.describe_key_pairs()
        for i in range(len(key_pairs['KeyPairs'])):
            key_list.append(key_pairs['KeyPairs'][i]['KeyName'])
            key_id_list.append(key_pairs['KeyPairs'][i]['KeyPairId'])

        selection = inquire.ask_list('Select SSH key', key_list, key_id_list, default=default)
        self.aws_ssh_key = key_pairs['KeyPairs'][selection]['KeyName']
        self.ssh_key_fingerprint = key_pairs['KeyPairs'][selection]['KeyFingerprint']
        return self.aws_ssh_key

    def aws_get_instance_type(self, default=None, write=None) -> str:
        """Get the AWS instance type"""
        inquire = ask()
        size_list = []

        if write:
            self.aws_instance_type = write
            return self.aws_instance_type

        if self.aws_instance_type:
            return self.aws_instance_type

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        describe_args = {}
        while True:
            instance_types = ec2_client.describe_instance_types(**describe_args)
            for machine_type in instance_types['InstanceTypes']:
                config_block = {}
                config_block['name'] = machine_type['InstanceType']
                config_block['cpu'] = int(machine_type['VCpuInfo']['DefaultVCpus'])
                config_block['mem'] = int(machine_type['MemoryInfo']['SizeInMiB'])
                try:
                    config_block['description'] = ",".join(machine_type['ProcessorInfo']['SupportedArchitectures']) \
                                                  + ' ' + str(machine_type['ProcessorInfo']['SustainedClockSpeedInGhz']) + 'GHz' \
                                                  + ', Network: ' + machine_type['NetworkInfo']['NetworkPerformance'] \
                                                  + ', Hypervisor: ' + machine_type['Hypervisor'] if 'Hypervisor' in machine_type else 'NA'
                except KeyError:
                    config_block['description'] = ""
                size_list.append(config_block)
            if 'NextToken' not in instance_types:
                break
            describe_args['NextToken'] = instance_types['NextToken']
        selection = inquire.ask_machine_type('AWS Instance Type', size_list, default=default)
        self.aws_instance_type = size_list[selection]['name']
        return self.aws_instance_type

    def aws_get_market_ami(self, select=True, default=None, write=None, arch="x86_64", root_dev="ebs") -> dict:
        """Get an AMI name"""
        inquire = ask()
        image_list = []
        owner_list = [
            {
                "name": "099720109477",
                "description": "Ubuntu Linux"
            },
            {
                "name": "125523088429",
                "description": "CentOS Linux"
            },
            {
                "name": "309956199498",
                "description": "RedHat Linux"
            },
            {
                "name": "013907871322",
                "description": "Suse Linux"
            },
            {
                "name": "379101102735",
                "description": "Debian 9 and earlier"
            },
            {
                "name": "136693071363",
                "description": "Debian 10 and later"
            },
            {
                "name": "131827586825",
                "description": "Oracle Linux"
            },
            {
                "name": "679593333241",
                "description": "Fedora and CoreOS Linux"
            },
            {
                "name": "137112412989",
                "description": "Amazon Linux"
            },
        ]

        if write:
            self.aws_market_ami = write
            return self.aws_market_ami

        if self.aws_market_ami:
            return self.aws_market_ami

        selection = inquire.ask_list("Linux Distribution", owner_list)
        ownerid = owner_list[selection]['name']

        print("Searching images (this can take a few minutes) ...")

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        images = ec2_client.describe_images(Owners=[ownerid], Filters=[
                                            {
                                                'Name': 'architecture',
                                                'Values': [
                                                    arch,
                                                ]
                                            },
                                            {
                                                'Name': 'root-device-type',
                                                'Values': [
                                                    root_dev,
                                                ]
                                            },
                                            ])
        for i in range(len(images['Images'])):
            image_block = {}
            image_block['name'] = images['Images'][i]['ImageId']
            image_block['description'] = images['Images'][i]['Name']
            image_block['date'] = images['Images'][i]['CreationDate']
            image_block['arch'] = images['Images'][i]['Architecture']
            image_list.append(image_block)

        image_list = sorted(image_list, key=lambda d: d['description'])

        if select:
            selection = inquire.ask_list('Select AMI', image_list, default=default)
            self.aws_market_ami = image_list[selection]
        else:
            self.aws_market_ami = image_list

        return self.aws_market_ami

    def aws_get_ami_id(self, select=True, default=None, write=None) -> Union[dict, list[dict]]:
        """Get the Couchbase AMI to use"""
        inquire = ask()
        image_list = []

        if write:
            self.aws_ami_id = write
            return self.aws_ami_id

        if self.aws_ami_id:
            return self.aws_ami_id

        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        images = ec2_client.describe_images(Owners=['self'])
        for i in range(len(images['Images'])):
            image_block = {}
            image_block['name'] = images['Images'][i]['ImageId']
            image_block['description'] = images['Images'][i]['Name']
            image_block['date'] = images['Images'][i]['CreationDate']
            image_block['arch'] = images['Images'][i]['Architecture']
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
                    image_block['description'] = image_block['description'] + f" ({item_version_tag})"
            if 'type' not in image_block or 'release' not in image_block:
                continue
            image_list.append(image_block)
        if select:
            selection = inquire.ask_list('Select AMI', image_list, default=default)
            self.aws_ami_id = image_list[selection]
            self.aws_ami_name = image_list[selection]['name']
        else:
            self.aws_ami_id = image_list

        return self.aws_ami_id

    @prereq(requirements=('aws_get_ami_id',))
    def get_image(self):
        return self.aws_ami_id

    @prereq(requirements=('aws_get_market_ami',))
    def get_market_image(self):
        return self.aws_market_ami

    def aws_remove_ami(self, ami: str):
        inquire = ask()

        if inquire.ask_yn(f"Delete AMI {ami}", default=True):
            ec2_client = boto3.client('ec2', region_name=self.aws_region)
            try:
                ec2_client.deregister_image(ImageId=ami)
            except Exception as err:
                raise AWSDriverError(f"can not remove AMI {ami}: {err}")

    def aws_get_region(self, default=None, write=None) -> str:
        """Get the AWS Region"""
        inquire = ask()

        if write:
            self.aws_region = write
            return self.aws_region

        if 'AWS_REGION' in os.environ:
            self.aws_region = os.environ['AWS_REGION']
        elif 'AWS_DEFAULT_REGION' in os.environ:
            self.aws_region = os.environ['AWS_DEFAULT_REGION']
        elif boto3.DEFAULT_SESSION:
            self.aws_region = boto3.DEFAULT_SESSION.region_name
        elif boto3.Session().region_name:
            self.aws_region = boto3.Session().region_name
        else:
            self.aws_region = inquire.ask_text('AWS Region', default=default)

        return self.aws_region

    def aws_get_region_zones(self) -> list:
        ec2_client = boto3.client('ec2', region_name=self.aws_region)
        zone_list = ec2_client.describe_availability_zones()
        for availability_zone in zone_list['AvailabilityZones']:
            self.logger.info("Found availability zone %s" % availability_zone['ZoneName'])
            self.aws_availability_zones.append(availability_zone['ZoneName'])
        return self.aws_availability_zones

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
