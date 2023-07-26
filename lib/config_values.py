##
##

from __future__ import annotations
import attr
import argparse
from typing import Optional


@attr.s
class CloudAsset:
    cloud: Optional[str] = attr.ib(default=None)
    environment: Optional[str] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    project: Optional[str] = attr.ib(default=None)
    resource_group: Optional[str] = attr.ib(default=None)
    image: Optional[str] = attr.ib(default=None)
    image_group: Optional[str] = attr.ib(default=None)
    compute: Optional[str] = attr.ib(default=None)
    key_name: Optional[str] = attr.ib(default=None)
    network: Optional[str] = attr.ib(default=None)
    subnets: Optional[str] = attr.ib(default=None)
    security_group: Optional[str] = attr.ib(default=None)
    disk_iops: Optional[str] = attr.ib(default=None)
    disk_size: Optional[str] = attr.ib(default=None)
    disk_type: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("project"):
            self.project = args.get("project")
        if args.get("resource_group"):
            self.resource_group = args.get("resource_group")
        if args.get("image"):
            self.image = args.get("image")
        if args.get("image_group"):
            self.image_group = args.get("image_group")
        if args.get("compute"):
            self.compute = args.get("compute")
        if args.get("key_name"):
            self.key_name = args.get("key_name")
        if args.get("network"):
            self.network = args.get("network")
        if args.get("subnets"):
            self.subnets = args.get("subnets")
        if args.get("security_group"):
            self.security_group = args.get("security_group")
        if args.get("disk_iops"):
            self.disk_iops = args.get("disk_iops")
        if args.get("disk_size"):
            self.disk_size = args.get("disk_size")
        if args.get("disk_type"):
            self.disk_type = args.get("disk_type")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("project"):
            self.project = args.get("project")
        if args.get("resource_group"):
            self.resource_group = args.get("resource_group")
        if args.get("image"):
            self.image = args.get("image")
        if args.get("image_group"):
            self.image_group = args.get("image_group")
        if args.get("compute"):
            self.compute = args.get("compute")
        if args.get("key_name"):
            self.key_name = args.get("key_name")
        if args.get("network"):
            self.network = args.get("network")
        if args.get("subnets"):
            self.subnets = args.get("subnets")
        if args.get("security_group"):
            self.security_group = args.get("security_group")
        if args.get("disk_iops"):
            self.disk_iops = args.get("disk_iops")
        if args.get("disk_size"):
            self.disk_size = args.get("disk_size")
        if args.get("disk_type"):
            self.disk_type = args.get("disk_type")


@attr.s
class Network:
    cloud: Optional[str] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    cidr: Optional[str] = attr.ib(default=None)
    subnets: Optional[str] = attr.ib(default=None)
    id: Optional[str] = attr.ib(default=None)
    name: Optional[str] = attr.ib(default=None)
    default: Optional[bool] = attr.ib(default=False)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("cidr"):
            self.cidr = args.get("cidr")
        if args.get("subnets"):
            self.subnets = args.get("subnets")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("default"):
            self.default = args.get("default")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("cidr"):
            self.cidr = args.get("cidr")
        if args.get("subnets"):
            self.subnets = args.get("subnets")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("default"):
            self.default = args.get("default")


@attr.s
class Subnet:
    cloud: Optional[str] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    cidr: Optional[str] = attr.ib(default=None)
    gateway: Optional[str] = attr.ib(default=None)
    routes: Optional[str] = attr.ib(default=None)
    name: Optional[str] = attr.ib(default=None)
    id: Optional[str] = attr.ib(default=None)
    network: Optional[str] = attr.ib(default=None)
    zone: Optional[str] = attr.ib(default=None)
    security_group: Optional[str] = attr.ib(default=None)
    default: Optional[bool] = attr.ib(default=False)
    public: Optional[bool] = attr.ib(default=True)
    environment: Optional[str] = attr.ib(default=None)
    tag: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("cidr"):
            self.cidr = args.get("cidr")
        if args.get("gateway"):
            self.gateway = args.get("gateway")
        if args.get("routes"):
            self.routes = args.get("routes")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("network"):
            self.network = args.get("network")
        if args.get("zone"):
            self.zone = args.get("zone")
        if args.get("security_group"):
            self.security_group = args.get("security_group")
        if args.get("default"):
            self.default = args.get("default")
        if args.get("public"):
            self.public = args.get("public")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("tag"):
            self.tag = args.get("tag")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("cidr"):
            self.cidr = args.get("cidr")
        if args.get("gateway"):
            self.gateway = args.get("gateway")
        if args.get("routes"):
            self.routes = args.get("routes")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("network"):
            self.network = args.get("network")
        if args.get("zone"):
            self.zone = args.get("zone")
        if args.get("security_group"):
            self.security_group = args.get("security_group")
        if args.get("default"):
            self.default = args.get("default")
        if args.get("public"):
            self.public = args.get("public")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("tag"):
            self.tag = args.get("tag")


@attr.s
class Node:
    cloud: Optional[str] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    id: Optional[int] = attr.ib(default=None)
    name: Optional[str] = attr.ib(default=None)
    type: Optional[str] = attr.ib(default=None)
    config_flags: Optional[str] = attr.ib(default=None)
    environment: Optional[str] = attr.ib(default=None)
    services: Optional[str] = attr.ib(default=None)
    subnet: Optional[str] = attr.ib(default=None)
    zone: Optional[str] = attr.ib(default=None)
    cpu: Optional[int] = attr.ib(default=None)
    ram: Optional[int] = attr.ib(default=None)
    swap: Optional[bool] = attr.ib(default=True)
    compute: Optional[str] = attr.ib(default=None)
    disk_iops: Optional[str] = attr.ib(default=None)
    disk_size: Optional[str] = attr.ib(default=None)
    disk_type: Optional[str] = attr.ib(default=None)
    ip_address: Optional[str] = attr.ib(default=None)
    netmask: Optional[str] = attr.ib(default=None)
    gateway: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("type"):
            self.type = args.get("type")
        if args.get("config_flags"):
            self.config_flags = args.get("config_flags")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("services"):
            self.services = args.get("services")
        if args.get("subnet"):
            self.subnet = args.get("subnet")
        if args.get("zone"):
            self.zone = args.get("zone")
        if args.get("cpu"):
            self.cpu = args.get("cpu")
        if args.get("ram"):
            self.ram = args.get("ram")
        if args.get("swap"):
            self.swap = args.get("swap")
        if args.get("compute"):
            self.compute = args.get("compute")
        if args.get("disk_iops"):
            self.disk_iops = args.get("disk_iops")
        if args.get("disk_size"):
            self.disk_size = args.get("disk_size")
        if args.get("disk_type"):
            self.disk_type = args.get("disk_type")
        if args.get("ip_address"):
            self.ip_address = args.get("ip_address")
        if args.get("netmask"):
            self.netmask = args.get("netmask")
        if args.get("gateway"):
            self.gateway = args.get("gateway")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("cloud"):
            self.cloud = args.get("cloud")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("id"):
            self.id = args.get("id")
        if args.get("name"):
            self.name = args.get("name")
        if args.get("type"):
            self.type = args.get("type")
        if args.get("config_flags"):
            self.config_flags = args.get("config_flags")
        if args.get("environment"):
            self.environment = args.get("environment")
        if args.get("services"):
            self.services = args.get("services")
        if args.get("subnet"):
            self.subnet = args.get("subnet")
        if args.get("zone"):
            self.zone = args.get("zone")
        if args.get("cpu"):
            self.cpu = args.get("cpu")
        if args.get("ram"):
            self.ram = args.get("ram")
        if args.get("swap"):
            self.swap = args.get("swap")
        if args.get("compute"):
            self.compute = args.get("compute")
        if args.get("disk_iops"):
            self.disk_iops = args.get("disk_iops")
        if args.get("disk_size"):
            self.disk_size = args.get("disk_size")
        if args.get("disk_type"):
            self.disk_type = args.get("disk_type")
        if args.get("ip_address"):
            self.ip_address = args.get("ip_address")
        if args.get("netmask"):
            self.netmask = args.get("netmask")
        if args.get("gateway"):
            self.gateway = args.get("gateway")


@attr.s
class AWSConfig:
    id: Optional[int] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    account: Optional[str] = attr.ib(default=None)
    sso_url: Optional[str] = attr.ib(default=None)
    access_key: Optional[str] = attr.ib(default=None)
    secret_key: Optional[str] = attr.ib(default=None)
    session_token: Optional[str] = attr.ib(default=None)
    expiration: Optional[int] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("id"):
            self.id = args.get("id")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("account"):
            self.account = args.get("account")
        if args.get("sso_url"):
            self.sso_url = args.get("sso_url")
        if args.get("access_key"):
            self.access_key = args.get("access_key")
        if args.get("secret_key"):
            self.secret_key = args.get("secret_key")
        if args.get("session_token"):
            self.session_token = args.get("session_token")
        if args.get("expiration"):
            self.expiration = args.get("expiration")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("region"):
            self.region = args.get("region")
        if args.get("account"):
            self.account = args.get("account")
        if args.get("sso_url"):
            self.sso_url = args.get("sso_url")
        if args.get("access_key"):
            self.access_key = args.get("access_key")
        if args.get("secret_key"):
            self.secret_key = args.get("secret_key")
        if args.get("session_token"):
            self.session_token = args.get("session_token")
        if args.get("expiration"):
            self.expiration = args.get("expiration")

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class GCPConfig:
    id: Optional[int] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    account_file: Optional[str] = attr.ib(default=None)
    project_id: Optional[str] = attr.ib(default=None)
    account_email: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("id"):
            self.id = args.get("id")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("account_file"):
            self.account_file = args.get("account_file")
        if args.get("project_id"):
            self.project_id = args.get("project_id")
        if args.get("account_email"):
            self.account_email = args.get("account_email")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("region"):
            self.region = args.get("region")
        if args.get("account_file"):
            self.account_file = args.get("account_file")
        if args.get("project_id"):
            self.project_id = args.get("project_id")
        if args.get("account_email"):
            self.account_email = args.get("account_email")

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class AzureConfig:
    id: Optional[int] = attr.ib(default=None)
    region: Optional[str] = attr.ib(default=None)
    subscription_id: Optional[str] = attr.ib(default=None)
    resource_group: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("id"):
            self.id = args.get("id")
        if args.get("region"):
            self.region = args.get("region")
        if args.get("subscription_id"):
            self.subscription_id = args.get("subscription_id")
        if args.get("resource_group"):
            self.resource_group = args.get("resource_group")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("region"):
            self.region = args.get("region")
        if args.get("subscription_id"):
            self.subscription_id = args.get("subscription_id")
        if args.get("resource_group"):
            self.resource_group = args.get("resource_group")

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class VMWareConfig:
    id: Optional[int] = attr.ib(default=None)
    hostname: Optional[str] = attr.ib(default=None)
    username: Optional[str] = attr.ib(default=None)
    password: Optional[str] = attr.ib(default=None)
    datacenter: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("id"):
            self.id = args.get("id")
        if args.get("hostname"):
            self.hostname = args.get("hostname")
        if args.get("username"):
            self.username = args.get("username")
        if args.get("password"):
            self.password = args.get("password")
        if args.get("datacenter"):
            self.datacenter = args.get("datacenter")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("hostname"):
            self.hostname = args.get("hostname")
        if args.get("username"):
            self.username = args.get("username")
        if args.get("password"):
            self.password = args.get("password")
        if args.get("datacenter"):
            self.datacenter = args.get("datacenter")

    @property
    def as_dict(self):
        return self.__dict__


@attr.s
class CapellaConfig:
    id: Optional[int] = attr.ib(default=None)
    access_key: Optional[str] = attr.ib(default=None)
    secret_key: Optional[str] = attr.ib(default=None)

    @property
    def get_values(self):
        return self.__annotations__

    def from_dict(self, args: dict):
        if args.get("id"):
            self.id = args.get("id", self.id)
        if args.get("access_key"):
            self.access_key = args.get("access_key")
        if args.get("secret_key"):
            self.secret_key = args.get("secret_key")

    def from_namespace(self, namespace: argparse.Namespace):
        args = vars(namespace)

        if args.get("access_key"):
            self.access_key = args.get("access_key")
        if args.get("secret_key"):
            self.secret_key = args.get("secret_key")

    @property
    def as_dict(self):
        return self.__dict__
