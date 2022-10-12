##
##

import logging
import boto3
import os
import re
from lib.exceptions import AWSDriverError, EmptyResultSet
from typing import Union
from lib.ask import ask
from lib.varfile import varfile
from lib.prereq import prereq


class AWSValues(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)


class AWS(object):

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

        self.ec2_client = boto3.client('ec2', region_name=self.aws_region)

    def root_types(self) -> list[str]:
        return self.ebs_type_list

    def get_security_group_list(self, vpc_id: str) -> list[dict]:
        vpc_filter = {
            'Name': 'vpc-id',
            'Values': [
                vpc_id,
            ]
        }
        sgs = self.ec2_client.describe_security_groups(Filters=[vpc_filter])

        if len(sgs['SecurityGroups']) == 0:
            raise EmptyResultSet(f"no security groups found")
        else:
            return sgs['SecurityGroups']

    def create_security_group(self, name: str, description: str, vpc_id: str) -> str:
        result = self.ec2_client.create_security_group(GroupName=name, Description=description, VpcId=vpc_id)
        return result['GroupId']

    def delete_security_group(self, sg_id: str) -> None:
        self.ec2_client.delete_security_group(GroupId=sg_id)

    def get_vpc_list(self) -> list[dict]:
        vpcs = self.ec2_client.describe_vpcs()

        if len(vpcs['Vpcs']) == 0:
            raise EmptyResultSet(f"no VPCs found")
        else:
            return vpcs['Vpcs']

    def create_vpc(self, cidr: str) -> str:
        result = self.ec2_client.create_vpc(CidrBlock=cidr)
        return result['Vpc']['VpcId']

    def delete_vpc(self, vpc_id: str) -> None:
        self.ec2_client.delete_vpc(VpcId=vpc_id)
