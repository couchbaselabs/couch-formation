##
##

import logging
import boto3
import botocore.exceptions
from botocore.config import Config
import os
import attr
import webbrowser
import time
from datetime import datetime
from Crypto.PublicKey import RSA
from attr.validators import instance_of as io
from typing import Iterable, Union
from itertools import cycle
from lib.exceptions import AWSDriverError, EmptyResultSet
from lib.util.filemgr import FileManager
from lib.util.db_mgr import LocalDB
from lib.config_values import CloudTable
import lib.config as config

logger = logging.getLogger('cf.driver.aws')
logger.addHandler(logging.NullHandler())
logging.getLogger("botocore").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
CLOUD_KEY = "aws"


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
class AWSEbsDiskTypes(object):
    ebs_type_list = [
        {
            "type": "standard",
            "iops": None,
            "max": None
        },
        {
            "type": "io1",
            "iops": 3000,
            "max": 64000
        },
        {
            "type": "io2",
            "iops": 3000,
            "max": 64000
        },
        {
            "type": "gp2",
            "iops": None,
            "max": None
        },
        {
            "type": "sc1",
            "iops": None,
            "max": None
        },
        {
            "type": "st1",
            "iops": None,
            "max": None
        },
        {
            "type": "gp3",
            "iops": 3000,
            "max": 16000
        }
    ]


@attr.s
class AWSImageOwners(object):
    image_owner_list = [
        {
            "owner_id": "099720109477",
            "description": "Ubuntu Linux",
            "user": "ubuntu"
        },
        {
            "owner_id": "125523088429",
            "description": "CentOS Linux",
            "user": "centos"
        },
        {
            "owner_id": "309956199498",
            "description": "RedHat Linux",
            "user": "ec2-user"
        },
        {
            "owner_id": "013907871322",
            "description": "Suse Linux",
            "user": "ec2-user"
        },
        {
            "owner_id": "379101102735",
            "description": "Debian 9 and earlier",
            "user": "admin"
        },
        {
            "owner_id": "136693071363",
            "description": "Debian 10 and later",
            "user": "admin"
        },
        {
            "owner_id": "131827586825",
            "description": "Oracle Linux",
            "user": "ec2-user"
        },
        {
            "owner_id": "125523088429",
            "description": "Fedora CoreOS Linux",
            "user": "core"
        },
        {
            "owner_id": "137112412989",
            "description": "Amazon Linux",
            "user": "ec2-user"
        },
        {
            "owner_id": "647457786197",
            "description": "Arch Linux",
            "user": "arch"
        },
        {
            "owner_id": "792107900819",
            "description": "Rocky Linux",
            "user": "rocky"
        },
    ]


class CloudInit(object):
    VERSION = '4.0.0'

    def __init__(self):
        self.db = LocalDB()
        self.timeouts = Config(
            connect_timeout=1,
            read_timeout=1,
            retries={'max_attempts': 2}
        )

    def auth(self):
        if config.cloud_config.expiration:
            timestamp = config.cloud_config.expiration / 1000
            expires = datetime.fromtimestamp(timestamp)
            if datetime.now() < expires:
                return

        if config.cloud_config.sso_url and config.cloud_config.account:
            self.sso_auth()
        elif config.cloud_config.access_key and config.cloud_config.secret_key:
            if config.cloud_config.expiration:
                timestamp = config.cloud_config.expiration / 1000
                expires = datetime.fromtimestamp(timestamp)
                if datetime.now() > expires:
                    raise AWSDriverError("session token expired")
        else:
            self.default_auth()

    @staticmethod
    def default_auth():
        session = boto3.Session(profile_name='default')
        credentials = session.get_credentials()
        config.cloud_config.access_key = credentials.access_key
        config.cloud_config.secret_key = credentials.secret_key
        config.cloud_config.session_token = credentials.token

    @staticmethod
    def sso_auth():
        token = {}

        session = boto3.Session()
        account_id = config.cloud_config.account
        start_url = config.cloud_config.sso_url
        region = config.cloud_config.region
        sso_oidc = session.client('sso-oidc', region_name=region)
        client_creds = sso_oidc.register_client(
            clientName='couch-formation',
            clientType='public',
        )
        device_authorization = sso_oidc.start_device_authorization(
            clientId=client_creds['clientId'],
            clientSecret=client_creds['clientSecret'],
            startUrl=start_url,
        )
        url = device_authorization['verificationUriComplete']
        device_code = device_authorization['deviceCode']
        expires_in = device_authorization['expiresIn']
        interval = device_authorization['interval']
        webbrowser.open(url, autoraise=True)
        for n in range(1, expires_in // interval + 1):
            time.sleep(interval)
            try:
                token = sso_oidc.create_token(
                    grantType='urn:ietf:params:oauth:grant-type:device_code',
                    deviceCode=device_code,
                    clientId=client_creds['clientId'],
                    clientSecret=client_creds['clientSecret'],
                )
                break
            except sso_oidc.exceptions.AuthorizationPendingException:
                pass

        access_token = token['accessToken']
        sso = session.client('sso', region_name=region)
        account_roles = sso.list_account_roles(
            accessToken=access_token,
            accountId=account_id,
        )
        roles = account_roles['roleList']
        role = roles[0]
        role_creds = sso.get_role_credentials(
            roleName=role['roleName'],
            accountId=account_id,
            accessToken=access_token,
        )

        session_creds = role_creds['roleCredentials']

        config.cloud_config.access_key = session_creds['accessKeyId']
        config.cloud_config.secret_key = session_creds['secretAccessKey']
        config.cloud_config.session_token = session_creds['sessionToken']
        config.cloud_config.expiration = session_creds['expiration']

    def init(self):
        logger.info(f"importing region and zone information")
        regions = config.cloud_base().get_all_regions()
        count = 1
        for region in regions:
            try:
                logger.info(f" ... importing {region}")
                zones = config.cloud_base(region=region).zones()
                row = {
                    "id": count,
                    "name": region,
                    "zones": ','.join(zones),
                    "cloud": CLOUD_KEY
                }
                self.db.update_cloud(CloudTable.REGION, row)
                count += 1
            except (botocore.exceptions.ClientError, botocore.exceptions.ConnectTimeoutError):
                continue


class CloudBase(object):
    VERSION = '4.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = True

    def __init__(self, region: str = None):
        self.db = LocalDB()
        self.aws_region = None
        self.zone_list = []
        self.timeouts = Config(
            connect_timeout=1,
            read_timeout=1,
            retries={'max_attempts': 2}
        )

        if region:
            os.environ['AWS_DEFAULT_REGION'] = region
        elif config.cloud_config.region:
            os.environ['AWS_DEFAULT_REGION'] = config.cloud_config.region

        if config.cloud_config.access_key:
            os.environ['AWS_ACCESS_KEY_ID'] = config.cloud_config.access_key
        if config.cloud_config.secret_key:
            os.environ['AWS_SECRET_ACCESS_KEY'] = config.cloud_config.secret_key
        if config.cloud_config.session_token:
            os.environ['AWS_SESSION_TOKEN'] = config.cloud_config.session_token

        if 'AWS_DEFAULT_REGION' in os.environ:
            self.aws_region = os.environ['AWS_DEFAULT_REGION']
        elif 'AWS_REGION' in os.environ:
            self.aws_region = os.environ['AWS_REGION']
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

    def get_info(self):
        logger.info(f"Region:          {self.aws_region}")
        logger.info(f"Available Zones: {','.join(self.zone_list)}")

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

    def get_all_regions(self) -> list:
        regions = self.ec2_client.describe_regions(AllRegions=False)
        region_list = list(r['RegionName'] for r in regions['Regions'])
        return region_list

    def zones(self) -> list:
        try:
            zone_list = self.ec2_client.describe_availability_zones()
        except Exception as err:
            raise AWSDriverError(f"error getting availability zones: {err}")

        for availability_zone in zone_list['AvailabilityZones']:
            self.zone_list.append(availability_zone['ZoneName'])

        self.zone_list = sorted(set(self.zone_list))

        if len(self.zone_list) == 0:
            raise AWSDriverError("can not get AWS availability zones")

        return self.zone_list

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
        try:
            for item in self.list():
                yield item['cidr']
        except EmptyResultSet:
            return iter(())

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

    def list(self, filter_keys_exist: Union[list[str], None] = None, is_public: bool = False, owner_id: str = None) -> list[dict]:
        image_list = []
        if owner_id:
            owner_filter = [owner_id]
        else:
            owner_filter = []
        if is_public:
            ami_filter = [
                {
                    'Name': 'architecture',
                    'Values': [
                        "x86_64",
                        "arm64"
                    ]
                },
                {
                    'Name': 'root-device-type',
                    'Values': [
                        "ebs",
                    ]
                }
            ]
        else:
            ami_filter = [
                {
                    'Name': 'is-public',
                    'Values': [
                        'false',
                    ]
                }
            ]

        try:
            images = self.ec2_client.describe_images(Filters=ami_filter, Owners=owner_filter)
        except Exception as err:
            raise AWSDriverError(f"error getting AMIs: {err}")

        for image in images['Images']:
            image_block = {'name': image['ImageId'],
                           'description': image['Name'],
                           'date': image['CreationDate'],
                           'arch': image['Architecture']}
            if is_public:
                image_block.update({'owner': image['OwnerId']})
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
        tag_build = AWSTagStruct.build("key-pair")
        tag_build.add(AWSTag("Name", name))

        if tags:
            for key, value in tags.items():
                tag_build.add(AWSTag(key, value))

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

    def details(self, key_name: str) -> dict:
        try:
            result = self.ec2_client.describe_key_pairs(KeyNames=[key_name])
            key_result = result['KeyPairs'][0]
            key_block = {'name': key_result['KeyName'],
                         'id': key_result['KeyPairId'],
                         'fingerprint': key_result['KeyFingerprint']}
            key_block.update(self.process_tags(key_result))
            return key_block
        except Exception as err:
            raise AWSDriverError(f"error deleting key pair: {err}")

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
                         'name': subnet['SubnetId'],
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
