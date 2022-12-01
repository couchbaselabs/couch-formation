##
##

import logging
import boto3
import os
import attr
from Crypto.PublicKey import RSA
from attr.validators import instance_of as io
from typing import Iterable, Union
from itertools import cycle
from lib.exceptions import AWSDriverError, EmptyResultSet
from lib.util.filemgr import FileManager
import lib.config as config


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
    def build(cls, resource: str):
        return cls(
            resource,
            []
        )

    def add(self, obj: AWSTag):
        self.Tags.append(obj.as_dict)
        return self

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class EbsVolume(object):
    VolumeType = attr.ib(validator=io(str))
    VolumeSize = attr.ib(validator=io(int))

    @classmethod
    def build(cls, vol_type: str, vol_size: int):
        return cls(
            vol_type,
            vol_size
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AWSEbsDisk(object):
    DeviceName = attr.ib(validator=io(str))
    Ebs = attr.ib(validator=io(dict))

    @classmethod
    def build(cls, device: str, obj: EbsVolume):
        return cls(
            device,
            obj.as_dict
        )

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AWSebsDiskTypes(object):
    ebs_type_list = ['standard', 'io1', 'io2', 'gp2', 'sc1', 'st1', 'gp3']


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = True

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.aws_region = None

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

        self.set_zone()

    @property
    def client(self):
        return self.ec2_client

    @property
    def region(self):
        return self.aws_region

    @staticmethod
    def process_tags(struct: dict) -> dict:
        block = {}
        if 'Tags' in struct:
            for tag in struct['Tags']:
                block.update({tag['Key'].lower() + '_tag': tag['Value']})
        block = dict(sorted(block.items()))
        return block

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

    def zones(self) -> list:
        aws_availability_zones = []

        try:
            zone_list = self.ec2_client.describe_availability_zones()
        except Exception as err:
            raise AWSDriverError(f"error getting availability zones: {err}")

        for availability_zone in zone_list['AvailabilityZones']:
            self.logger.info("Found availability zone %s" % availability_zone['ZoneName'])
            aws_availability_zones.append(availability_zone['ZoneName'])
        return aws_availability_zones

    def set_zone(self) -> None:
        zone_list = self.zones()
        config.cloud_zone_cycle = cycle(zone_list)


class SecurityGroup(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, vpc_id: str, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        sg_list = []
        sgs = []
        extra_args = {}
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                vpc_id,
            ]
        }

        try:
            while True:
                result = self.ec2_client.describe_security_groups(**extra_args, Filters=[vpc_filter])
                sgs.extend(result['SecurityGroups'])
                if 'NextToken' not in result:
                    break
                extra_args['NextToken'] = result['NextToken']
        except Exception as err:
            raise AWSDriverError(f"error getting security groups: {err}")

        for sg_entry in sgs:
            sg_block = {'name': sg_entry['GroupName'],
                        'description': sg_entry['Description'],
                        'id': sg_entry['GroupId'],
                        'vpc': sg_entry['VpcId']}
            sg_block.update(self.process_tags(sg_entry))
            if filter_keys_exist:
                if not all(key in sg_block for key in filter_keys_exist):
                    continue
            sg_list.append(sg_block)

        if len(sg_list) == 0:
            raise EmptyResultSet(f"no security groups found")
        else:
            return sg_list

    def create(self, name: str, description: str, vpc_id: str) -> str:
        sg_tag = [AWSTagStruct.build("security-group").add(AWSTag("Name", name)).as_dict]
        try:
            result = self.ec2_client.create_security_group(GroupName=name, Description=description, VpcId=vpc_id, TagSpecifications=sg_tag)
        except Exception as err:
            raise AWSDriverError(f"error creating security group: {err}")

        return result['GroupId']

    def delete(self, sg_id: str) -> None:
        try:
            self.ec2_client.delete_security_group(GroupId=sg_id)
        except Exception as err:
            raise AWSDriverError(f"error deleting security group: {err}")


class Network(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        vpc_list = []
        vpcs = []
        extra_args = {}

        try:
            while True:
                result = self.ec2_client.describe_vpcs(**extra_args)
                vpcs.extend(result['Vpcs'])
                if 'NextToken' not in result:
                    break
                extra_args['NextToken'] = result['NextToken']
        except Exception as err:
            raise AWSDriverError(f"error getting VPC list: {err}")

        for vpc_entry in vpcs:
            vpc_block = {'cidr': vpc_entry['CidrBlock'],
                         'default': vpc_entry['IsDefault'],
                         'id': vpc_entry['VpcId']}
            vpc_block.update(self.process_tags(vpc_entry))
            if filter_keys_exist:
                if not all(key in vpc_block for key in filter_keys_exist):
                    continue
            vpc_list.append(vpc_block)

        if len(vpc_list) == 0:
            raise EmptyResultSet(f"no VPCs found")
        else:
            return vpc_list

    @property
    def cidr_list(self):
        for item in self.list():
            yield item['cidr']

    def create(self, name: str, cidr: str) -> str:
        vpc_tag = [AWSTagStruct.build("vpc").add(AWSTag("Name", name)).as_dict]
        try:
            result = self.ec2_client.create_vpc(CidrBlock=cidr, TagSpecifications=vpc_tag)
        except Exception as err:
            raise AWSDriverError(f"error creating VPC: {err}")

        return result['Vpc']['VpcId']

    def delete(self, vpc_id: str) -> None:
        try:
            self.ec2_client.delete_vpc(VpcId=vpc_id)
        except Exception as err:
            raise AWSDriverError(f"error deleting VPC: {err}")

    def details(self, vpc_id: str) -> Union[dict, None]:
        try:
            result = self.ec2_client.describe_vpcs(VpcId=[vpc_id])
            vpc_entry = result['Vpcs'][0]
            vpc_block = {'cidr': vpc_entry['CidrBlock'],
                         'default': vpc_entry['IsDefault'],
                         'id': vpc_entry['VpcId']}
            vpc_block.update(self.process_tags(vpc_entry))
            return vpc_block
        except (KeyError, IndexError):
            return None
        except Exception as err:
            raise AWSDriverError(f"error getting VPC details: {err}")


class Image(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        image_list = []
        ami_filter = {
            'Name': 'is-public',
            'Values': [
                'false',
            ]
        }

        try:
            images = self.ec2_client.describe_images(Filters=[ami_filter])
        except Exception as err:
            raise AWSDriverError(f"error getting AMIs: {err}")

        for image in images['Images']:
            image_block = {'name': image['ImageId'],
                           'description': image['Name'],
                           'date': image['CreationDate'],
                           'arch': image['Architecture']}
            image_block.update(self.process_tags(image))
            if filter_keys_exist:
                if not all(key in image_block for key in filter_keys_exist):
                    continue
            image_list.append(image_block)

        if len(image_list) == 0:
            raise EmptyResultSet(f"no AMIs found")

        return image_list

    def details(self, ami_id: str) -> dict:
        ami_filter = {
            'Name': 'image-id',
            'Values': [
                ami_id,
            ]
        }
        try:
            result = self.ec2_client.describe_images(Filters=[ami_filter])
        except Exception as err:
            raise AWSDriverError(f"error getting AMI details: {err}")

        return result['Images'][0]

    def create(self, name: str, instance: str, description=None, root_type="gp3", root_size=100) -> str:
        try:
            instance_details = Instance().details(instance)
        except Exception as err:
            raise AWSDriverError(f"error getting instance {instance} details: {err}")
        if 'BlockDeviceMappings' not in instance_details:
            raise AWSDriverError(f"can not get details for instance {instance}")

        root_dev = instance_details['BlockDeviceMappings'][0]['DeviceName']
        root_disk = [AWSEbsDisk.build(root_dev, EbsVolume(root_type, root_size)).as_dict]
        ami_tag = [AWSTagStruct.build("image").add(AWSTag("Name", name)).as_dict]

        if not description:
            description = "couch-formation-image"

        try:
            result = self.ec2_client.create_image(BlockDeviceMappings=root_disk,
                                                  Description=description,
                                                  InstanceId=instance,
                                                  Name=name,
                                                  TagSpecifications=ami_tag)
        except Exception as err:
            raise AWSDriverError(f"error creating AMI: {err}")

        ami_id = result['ImageId']
        waiter = self.ec2_client.get_waiter('image_available')
        waiter.wait(ImageIds=[ami_id])

        return ami_id

    def delete(self, ami: str) -> None:
        try:
            self.ec2_client.deregister_image(ImageId=ami)
        except Exception as err:
            raise AWSDriverError(f"error deleting AMI: {err}")


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        key_list = []

        try:
            key_pairs = self.ec2_client.describe_key_pairs()
        except Exception as err:
            raise AWSDriverError(f"error getting key pairs: {err}")

        for key in key_pairs['KeyPairs']:
            key_block = {'name': key['KeyName'],
                         'id': key['KeyPairId'],
                         'fingerprint': key['KeyFingerprint'],
                         'pubkey': key.get('PublicKey')}
            key_block.update(self.process_tags(key))
            if filter_keys_exist:
                if not all(key in key_block for key in filter_keys_exist):
                    continue
            key_list.append(key_block)

        if len(key_list) == 0:
            raise EmptyResultSet(f"no SSH keys found")

        return key_list

    def create(self, name: str, file_name: str, tags: Union[dict, None] = None) -> dict:
        ssh_key = self.public_key(file_name)
        key_block = {}
        key_tag = []

        if tags:
            tag_build = AWSTagStruct.build("key-pair")
            for k, v in tags.items():
                tag_build.add(AWSTag(k, v))
            key_tag = [tag_build.as_dict]

        try:
            result = self.ec2_client.import_key_pair(KeyName=name,
                                                     PublicKeyMaterial=ssh_key.encode('utf-8'),
                                                     TagSpecifications=key_tag)
            key_block = {'name': result['KeyName'],
                         'id': result['KeyPairId'],
                         'fingerprint': result['KeyFingerprint']}
            key_block.update(self.process_tags(result))
        except Exception as err:
            AWSDriverError(f"error importing key pair: {err}")

        return key_block

    def create_native(self, name: str) -> dict:
        key_block = {}
        try:
            result = self.ec2_client.create_key_pair(KeyName=name)
            key_block = {'name': result['KeyName'],
                         'id': result['KeyPairId'],
                         'fingerprint': result['KeyFingerprint'],
                         'key': result['KeyMaterial']}
            key_block.update(self.process_tags(result))
        except Exception as err:
            AWSDriverError(f"error creating key pair: {err}")

        return key_block

    def delete(self, name: str) -> None:
        try:
            self.ec2_client.delete_key_pair(KeyName=name)
        except Exception as err:
            raise AWSDriverError(f"error deleting key pair: {err}")

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


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self, vpc_id: str, zone: Union[str, None] = None, filter_keys_exist: Union[list[str], None] = None) -> list[dict]:
        subnet_list = []
        subnets = []
        extra_args = {}
        subnet_filter = [
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ]
            }
        ]

        if zone:
            subnet_filter.append(
                {
                    'Name': 'availability-zone',
                    'Values': [
                        zone,
                    ]
                }
            )

        try:
            while True:
                result = self.ec2_client.describe_subnets(**extra_args, Filters=subnet_filter)
                subnets.extend(result['Subnets'])
                if 'NextToken' not in result:
                    break
                extra_args['NextToken'] = result['NextToken']
        except Exception as err:
            raise AWSDriverError(f"error getting subnets: {err}")

        for subnet in subnets:
            net_block = {'cidr': subnet['CidrBlock'],
                         'id': subnet['SubnetId'],
                         'vpc': subnet['VpcId'],
                         'zone': subnet['AvailabilityZone'],
                         'default': subnet['DefaultForAz'],
                         'public': subnet['MapPublicIpOnLaunch']}
            net_block.update(self.process_tags(subnet))
            if filter_keys_exist:
                if not all(key in net_block for key in filter_keys_exist):
                    continue
            subnet_list.append(net_block)

        if len(subnet_list) == 0:
            raise EmptyResultSet(f"no subnets found")

        return subnet_list

    def create(self, name: str, vpc_id: str, zone: str, cidr: str) -> str:
        result = None
        subnet_tag = [AWSTagStruct.build("subnet").add(AWSTag("Name", name)).as_dict]
        try:
            result = self.ec2_client.create_subnet(VpcId=vpc_id, AvailabilityZone=zone, CidrBlock=cidr, TagSpecifications=subnet_tag)
        except Exception as err:
            AWSDriverError(f"error creating subnet: {err}")

        return result['Subnet']['SubnetId']

    def delete(self, subnet_id: str) -> None:
        try:
            self.ec2_client.delete_subnet(SubnetId=subnet_id)
        except Exception as err:
            raise AWSDriverError(f"error deleting subnet: {err}")


class Instance(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, name: str, ami: str, ssh_key: str, sg_id: str, subnet: str, root_type="gp3", root_size=100, instance_type="t2.micro"):
        try:
            ami_details = Image().details(ami)
        except Exception as err:
            raise AWSDriverError(f"error getting AMI {ami} details: {err}")
        if 'BlockDeviceMappings' not in ami_details:
            raise AWSDriverError(f"can not get details for AMI {ami}")

        root_dev = ami_details['BlockDeviceMappings'][0]['DeviceName']
        root_disk = [AWSEbsDisk.build(root_dev, EbsVolume(root_type, root_size)).as_dict]
        instance_tag = [AWSTagStruct.build("instance").add(AWSTag("Name", name)).as_dict]

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

        instance_id = result['Instances'][0]['InstanceId']
        waiter = self.ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        return instance_id

    def details(self, instance_id: str) -> dict:
        try:
            result = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        except Exception as err:
            raise AWSDriverError(f"error getting instance details: {err}")

        return result['Reservations'][0]['Instances'][0]

    def terminate(self, instance_id: str) -> None:
        try:
            self.ec2_client.terminate_instances(InstanceIds=[instance_id])
        except Exception as err:
            raise AWSDriverError(f"error terminating instance: {err}")

        waiter = self.ec2_client.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])


class MachineType(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def list(self) -> list:
        type_list = []
        types = []
        extra_args = {}
        try:
            while True:
                result = self.ec2_client.describe_instance_types(**extra_args)
                types.extend(result['InstanceTypes'])
                if 'NextToken' not in result:
                    break
                extra_args['NextToken'] = result['NextToken']
        except Exception as err:
            raise AWSDriverError(f"error getting instance types: {err}")

        for machine in types:
            key_block = {'name': machine['InstanceType'],
                         'cpu': int(machine['VCpuInfo']['DefaultVCpus']),
                         'memory': int(machine['MemoryInfo']['SizeInMiB']),
                         'arch': machine.get('ProcessorInfo', {}).get('SupportedArchitectures'),
                         'clock': machine.get('ProcessorInfo', {}).get('SustainedClockSpeedInGhz'),
                         'network': machine.get('NetworkInfo', {}).get('NetworkPerformance'),
                         'hypervisor': machine.get('Hypervisor')}
            type_list.append(key_block)

        if len(type_list) == 0:
            raise EmptyResultSet(f"no instance types found")

        return type_list

    def details(self, instance_type: str) -> dict:
        try:
            result = self.ec2_client.describe_instance_types(InstanceTypes=[instance_type])
        except Exception as err:
            raise AWSDriverError(f"error getting instance type details: {err}")

        if len(result['InstanceTypes']) == 0:
            raise EmptyResultSet(f"can not find instance type {instance_type}")

        machine = result['InstanceTypes'][0]

        return {'name': machine['InstanceType'],
                'cpu': int(machine['VCpuInfo']['DefaultVCpus']),
                'memory': int(machine['MemoryInfo']['SizeInMiB']),
                'arch': machine.get('ProcessorInfo', {}).get('SupportedArchitectures'),
                'clock': machine.get('ProcessorInfo', {}).get('SustainedClockSpeedInGhz'),
                'network': machine.get('NetworkInfo', {}).get('NetworkPerformance'),
                'hypervisor': machine.get('Hypervisor')}
