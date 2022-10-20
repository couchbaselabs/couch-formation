##
##

import logging
import boto3
import os
import attr
from attr.validators import instance_of as io, optional
from typing import Protocol, Iterable, List
from lib.exceptions import AWSDriverError, EmptyResultSet
from typing import Union
from lib.ask import ask
from lib.varfile import varfile
from lib.prereq import prereq


@attr.s
class AWSTag(object):
    Key = attr.ib(validator=io(str))
    Value = attr.ib(validator=io(str))

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AWSTagStruct(object):
    ResourceType = attr.ib(validator=io(str))
    Tags = attr.ib(validator=io(Iterable))

    @classmethod
    def build(cls, resource: str, obj: AWSTag):
        return cls(
            resource,
            [obj.as_dict]
        )

    @property
    def as_dict(self):
        return self.__dict__

class CloudDriver(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.aws_region = None
        self.ebs_type_list = ['standard', 'io1', 'io2', 'gp2', 'sc1', 'st1', 'gp3']

        if 'AWS_REGION' in os.environ:
            self.aws_region = os.environ['AWS_REGION']
        elif 'AWS_DEFAULT_REGION' in os.environ:
            self.aws_region = os.environ['AWS_DEFAULT_REGION']
        elif boto3.DEFAULT_SESSION:
            self.aws_region = boto3.DEFAULT_SESSION.region_name
        elif boto3.Session().region_name:
            self.aws_region = boto3.Session().region_name
        else:
            raise AWSDriverError("Can not determine AWS Region. Please export AWS_DEFAULT_REGION and try again.")

        try:
            self.ec2_client = boto3.client('ec2', region_name=self.aws_region)
        except Exception as err:
            raise AWSDriverError(f"can not initialize AWS driver: {err}")

    @staticmethod
    def tag_exists(key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return True
        return False

    @staticmethod
    def get_tag(key, tags):
        for i in range(len(tags)):
            if tags[i]['Key'] == key:
                return tags[i]['Value']
        return None

    def root_types(self) -> list[str]:
        return self.ebs_type_list

    def get_security_group_list(self, vpc_id: str) -> list[dict]:
        sg_list = []

        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                vpc_id,
            ]
        }
        try:
            sgs = self.ec2_client.describe_security_groups(Filters=[vpc_filter])
        except Exception as err:
            raise AWSDriverError(f"error getting security groups: {err}")

        for sg_entry in sgs['SecurityGroups']:
            sg_block = {'name': sg_entry['GroupName'],
                        'description': sg_entry['Description'],
                        'id': sg_entry['GroupId'],
                        'vpc': sg_entry['VpcId']}
            sg_list.append(sg_block)

        if len(sg_list) == 0:
            raise EmptyResultSet(f"no security groups found")
        else:
            return sg_list

    def create_security_group(self, name: str, description: str, vpc_id: str) -> str:
        try:
            result = self.ec2_client.create_security_group(GroupName=name, Description=description, VpcId=vpc_id)
        except Exception as err:
            raise AWSDriverError(f"error creating security group: {err}")

        return result['GroupId']

    def delete_security_group(self, sg_id: str) -> None:
        try:
            self.ec2_client.delete_security_group(GroupId=sg_id)
        except Exception as err:
            raise AWSDriverError(f"error deleting security group: {err}")

    def get_vpc_list(self) -> list[dict]:
        vpc_list = []

        try:
            vpcs = self.ec2_client.describe_vpcs()
        except Exception as err:
            raise AWSDriverError(f"error getting VPC list: {err}")

        for vpc_entry in vpcs['Vpcs']:
            vpc_block = {'cidr': vpc_entry['CidrBlock'],
                         'default': vpc_entry['IsDefault'],
                         'id': vpc_entry['VpcId']}
            vpc_list.append(vpc_block)

        if len(vpc_list) == 0:
            raise EmptyResultSet(f"no VPCs found")
        else:
            return vpc_list

    def create_vpc(self, name: str, cidr: str) -> str:
        vpc_tag = [AWSTagStruct.build("vpc", AWSTag("Name", name)).as_dict]
        try:
            result = self.ec2_client.create_vpc(CidrBlock=cidr, TagSpecifications=vpc_tag)
        except Exception as err:
            raise AWSDriverError(f"error creating VPC: {err}")

        return result['Vpc']['VpcId']

    def delete_vpc(self, vpc_id: str) -> None:
        try:
            self.ec2_client.delete_vpc(VpcId=vpc_id)
        except Exception as err:
            raise AWSDriverError(f"error deleting VPC: {err}")

    def get_zones(self) -> list:
        aws_availability_zones = []

        try:
            zone_list = self.ec2_client.describe_availability_zones()
        except Exception as err:
            raise AWSDriverError(f"error getting availability zones: {err}")

        for availability_zone in zone_list['AvailabilityZones']:
            self.logger.info("Found availability zone %s" % availability_zone['ZoneName'])
            aws_availability_zones.append(availability_zone['ZoneName'])
        return aws_availability_zones

    def get_ami_id(self) -> list[dict]:
        image_list = []
        images = None

        try:
            images = self.ec2_client.describe_images(Owners=['self'])
        except Exception as err:
            raise AWSDriverError(f"error getting AMIs: {err}")

        for i in range(len(images['Images'])):
            image_block = {'name': images['Images'][i]['ImageId'],
                           'description': images['Images'][i]['Name'],
                           'date': images['Images'][i]['CreationDate'],
                           'arch': images['Images'][i]['Architecture']}
            if 'Tags' in images['Images'][i]:
                item_release_tag = self.get_tag('Release', images['Images'][i]['Tags'])
                item_type_tag = self.get_tag('Type', images['Images'][i]['Tags'])
                item_version_tag = self.get_tag('Version', images['Images'][i]['Tags'])
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

        if len(image_list) == 0:
            raise EmptyResultSet(f"no AMIs found")

        return image_list

    def get_ssh_key_list(self) -> list[dict]:
        key_list = []

        try:
            key_pairs = self.ec2_client.describe_key_pairs()
        except Exception as err:
            raise AWSDriverError(f"error getting key pairs: {err}")

        for key in key_pairs['KeyPairs']:
            key_block = {'name': key['KeyName'],
                         'id': key['KeyPairId'],
                         'fingerprint': key['KeyFingerprint'],
                         'pubkey': key['PublicKey']}
            key_list.append(key_block)

        if len(key_list) == 0:
            raise EmptyResultSet(f"no SSH keys found")

        return key_list

    def create_key_pair(self, name: str) -> str:
        result = None
        try:
            result = self.ec2_client.create_key_pair(KeyName=name)
        except Exception as err:
            AWSDriverError(f"error creating keu pair: {err}")

        return result['KeyPairId']

    def delete_key_pair(self, name: str) -> None:
        try:
            self.ec2_client.delete_key_pair(KeyName=name)
        except Exception as err:
            raise AWSDriverError(f"error deleting key pair: {err}")

    def get_subnet_list(self) -> list[dict]:
        pass

    def create_subnet(self, vpc_id: str, zone: str, cidr: str) -> str:
        pass

    def delete_subnet(self, subnet_id: str) -> None:
        pass

    def create_ami(self, name: str, instance: str, description=None, root_dev="/dev/sda", root_type="gp3", root_size=100) -> str:
        root_disk = [
            {
                'DeviceName': root_dev,
                'Ebs': {
                    'VolumeType': root_type,
                    'VolumeSize': root_size,
                },
            },
        ]
        if not description:
            description = "couch-formation-image"

        try:
            result = self.ec2_client.create_image(BlockDeviceMappings=root_disk, Description=description, InstanceId=instance, Name=name)
        except Exception as err:
            raise AWSDriverError(f"error creating AMI: {err}")

        return result['ImageId']

    def delete_ami(self, ami: str) -> None:
        try:
            self.ec2_client.deregister_image(ImageId=ami)
        except Exception as err:
            raise AWSDriverError(f"error deleting AMI: {err}")

    def run_instance(self, name: str, ami: str, ssh_key: str, sg_id: str, subnet: str, root_dev="/dev/sda", root_type="gp3", root_size=100, instance_type="t2.micro"):
        root_disk = [
            {
                'DeviceName': root_dev,
                'Ebs': {
                    'VolumeType': root_type,
                    'VolumeSize': root_size,
                },
            },
        ]
        instance_tag = [AWSTagStruct.build("instance", AWSTag("Name", name)).as_dict]

        try:
            result = self.ec2_client.run_instances(BlockDeviceMappings=root_disk,
                                                   ImageId=ami,
                                                   InstanceType=instance_type,
                                                   KeyName=ssh_key,
                                                   MaxCount=1,
                                                   MinCount=1,
                                                   SecurityGroupIds=[sg_id],
                                                   SubnetId=subnet,
                                                   TagSpecifications=instance_tag)
        except Exception as err:
            raise AWSDriverError(f"error running instance: {err}")

        return result['Instances'][0]['ImageId']
