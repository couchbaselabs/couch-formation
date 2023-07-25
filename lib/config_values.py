##
##

from __future__ import annotations
import attr
import argparse
from typing import Optional


@attr.s
class AWSConfig:
    region: Optional[str] = attr.ib(default=None)
    account: Optional[str] = attr.ib(default=None)
    sso_url: Optional[str] = attr.ib(default=None)
    access_key: Optional[str] = attr.ib(default=None)
    secret_key: Optional[str] = attr.ib(default=None)
    session_token: Optional[str] = attr.ib(default=None)
    expiration: Optional[str] = attr.ib(default=None)
    ami: Optional[str] = attr.ib(default=None)
    compute: Optional[str] = attr.ib(default=None)
    key_pair: Optional[str] = attr.ib(default=None)
    vpc: Optional[str] = attr.ib(default=None)
    subnets: Optional[str] = attr.ib(default=None)
    sg: Optional[str] = attr.ib(default=None)
    disk_iops: Optional[str] = attr.ib(default=None)
    disk_size: Optional[str] = attr.ib(default=None)
    disk_type: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        self.region = args.get("region", self.region)
        self.account = args.get("account", self.account)
        self.sso_url = args.get("sso_url", self.sso_url)
        self.access_key = args.get("access_key", self.access_key)
        self.secret_key = args.get("secret_key", self.secret_key)
        self.session_token = args.get("session_token", self.session_token)
        self.expiration = args.get("expiration", self.expiration)
        self.ami = args.get("ami", self.ami)
        self.compute = args.get("compute", self.compute)
        self.key_pair = args.get("key_pair", self.key_pair)
        self.vpc = args.get("vpc", self.vpc)
        self.subnets = args.get("subnets", self.subnets)
        self.sg = args.get("sg", self.sg)
        self.disk_iops = args.get("disk_iops", self.disk_iops)
        self.disk_size = args.get("disk_size", self.disk_size)
        self.disk_type = args.get("disk_type", self.disk_type)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPConfig:
    region: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        self.region = args.get("region", self.region)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureConfig:
    region: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        self.region = args.get("region", self.region)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VMWareConfig:
    hostname: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        self.hostname = args.get("region", self.hostname)

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaConfig:
    cloud: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        self.cloud = args.get("region", self.cloud)

    @property
    def as_dict(self):
        return self.__dict__
