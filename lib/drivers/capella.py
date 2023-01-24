##
##

import logging
import os
from lib.util.sessionmgr import CapellaSession
from lib.exceptions import CapellaDriverError, CapellaNotImplemented, EmptyResultSet


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = True
    SAAS_CLOUD = True
    NETWORK_SUPER_NET = False
    SUPPORT_PACKAGE = [
        "Basic",
        "DeveloperPro",
        "Enterprise"
    ]
    CLOUD_PROVIDER = [
        "aws",
        "gcp"
    ]
    AWS_MACHINE_TYPES = [
        {
            "name": "m5.xlarge",
            "description": "4 vCPU / 16GB RAM"
        },
        {
            "name": "r5.xlarge",
            "description": "4 vCPU / 32GB RAM"
        },
        {
            "name": "c5.2xlarge",
            "description": "8 vCPU / 16GB RAM"
        },
        {
            "name": "m5.2xlarge",
            "description": "8 vCPU / 32GB RAM"
        },
        {
            "name": "r5.2xlarge",
            "description": "8 vCPU / 64GB RAM"
        },
        {
            "name": "c5.4xlarge",
            "description": "16 vCPU / 32GB RAM"
        },
        {
            "name": "m5.4xlarge",
            "description": "16 vCPU / 64GB RAM"
        },
        {
            "name": "r5.4xlarge",
            "description": "16 vCPU / 128GB RAM"
        },
        {
            "name": "m5.8xlarge",
            "description": "32 vCPU / 128GB RAM"
        },
        {
            "name": "r5.8xlarge",
            "description": "32 vCPU / 256GB RAM"
        },
        {
            "name": "c5.9xlarge",
            "description": "36 vCPU / 72GB RAM"
        },
        {
            "name": "c5.12xlarge",
            "description": "48 vCPU / 96GB RAM"
        },
        {
            "name": "m5.12xlarge",
            "description": "48 vCPU / 192GB RAM"
        },
        {
            "name": "r5.12xlarge",
            "description": "48 vCPU / 384GB RAM"
        },
        {
            "name": "m5.16xlarge",
            "description": "64 vCPU / 256GB RAM"
        },
        {
            "name": "c5.18xlarge",
            "description": "72vCPU / 144GB RAM"
        }
    ]
    GCP_MACHINE_TYPES = [
        {
            "name": "n2-standard-2",
            "description": "2 vCPU / 8GB RAM"
        },
        {
            "name": "n2-standard-4",
            "description": "4 vCPU / 16GB RAM"
        },
        {
            "name": "n2-standard-8",
            "description": "8 vCPU / 32GB RAM"
        },
        {
            "name": "n2-standard-16",
            "description": "16 vCPU / 64GB RAM"
        },
        {
            "name": "n2-standard-32",
            "description": "32 vCPU / 128GB RAM"
        },
        {
            "name": "n2-standard-48",
            "description": "48 vCPU / 192GB RAM"
        },
        {
            "name": "n2-standard-64",
            "description": "64 vCPU / 256GB RAM"
        },
        {
            "name": "n2-standard-80",
            "description": "80 vCPU / 320GB RAM"
        },
        {
            "name": "n2-highmem-2",
            "description": "2 vCPU / 16GB RAM"
        },
        {
            "name": "n2-highmem-4",
            "description": "4 vCPU / 32GB RAM"
        },
        {
            "name": "n2-highmem-8",
            "description": "8 vCPU / 64GB RAM"
        },
        {
            "name": "n2-highmem-16",
            "description": "16 vCPU / 128GB RAM"
        },
        {
            "name": "n2-highmem-32",
            "description": "32 vCPU / 256GB RAM"
        },
        {
            "name": "n2-highmem-48",
            "description": "48 vCPU / 384GB RAM"
        },
        {
            "name": "n2-highmem-64",
            "description": "64 vCPU / 512GB RAM"
        },
        {
            "name": "n2-highmem-80",
            "description": "80 vCPU / 640GB RAM"
        },
        {
            "name": "n2-highcpu-2",
            "description": "2 vCPU / 2GB RAM"
        },
        {
            "name": "n2-highcpu-4",
            "description": "4 vCPU / 4GB RAM"
        },
        {
            "name": "n2-highcpu-8",
            "description": "8 vCPU / 8GB RAM"
        },
        {
            "name": "n2-highcpu-16",
            "description": "16 vCPU / 16GB RAM"
        },
        {
            "name": "n2-highcpu-32",
            "description": "32 vCPU / 32GB RAM"
        },
        {
            "name": "n2-highcpu-48",
            "description": "48 vCPU / 48GB RAM"
        },
        {
            "name": "n2-highcpu-64",
            "description": "64 vCPU / 64GB RAM"
        },
        {
            "name": "n2-highcpu-80",
            "description": "80 vCPU / 80GB RAM"
        },
        {
            "name": "n2-custom-2-4096",
            "description": "2 vCPU / 4GB RAM"
        },
        {
            "name": "n2-custom-4-8192",
            "description": "4 vCPU / 8GB RAM"
        },
        {
            "name": "n2-custom-8-16384",
            "description": "8 vCPU / 16GB RAM"
        },
        {
            "name": "n2-custom-16-32768",
            "description": "16 vCPU / 32GB RAM"
        },
        {
            "name": "n2-custom-32-65536",
            "description": "32 vCPU / 64GB RAM"
        },
        {
            "name": "n2-custom-36-73728",
            "description": "36 vCPU / 72GB RAM"
        },
        {
            "name": "n2-custom-48-98304",
            "description": "48 vCPU / 96GB RAM"
        },
        {
            "name": "n2-custom-72-147456",
            "description": "72 vCPU / 144GB RAM"
        }
    ]
    AWS_REGIONS = [
        "us-east-1",
        "us-east-2",
        "us-west-2",
        "eu-west-1",
        "eu-central-1",
        "eu-west-2",
        "eu-west-3",
        "eu-north-1",
        "ap-southeast-1",
        "ap-northeast-1",
        "ap-southeast-2",
        "ap-northeast-2",
        "ap-south-1",
        "ca-central-1"
    ]
    GCP_REGIONS = [
        "us-east1",
        "us-east4",
        "us-west1",
        "us-west3",
        "us-west4",
        "us-central1",
        "northamerica-northeast1",
        "northamerica-northeast2",
        "asia-east1",
        "asia-east2",
        "asia-northeast1",
        "asia-northeast2",
        "asia-northeast3",
        "asia-south1",
        "asia-south2",
        "asia-southeast1",
        "asia-southeast2",
        "australia-southeast1",
        "australia-southeast2",
        "europe-west1",
        "europe-west2",
        "europe-west3",
        "europe-west4",
        "europe-west6",
        "europe-west8",
        "europe-central2",
        "europe-north1",
        "southamerica-east1",
        "southamerica-west1"
    ]
    AWS_DISK_TYPES = [
        {
            "type": "GP3",
            "iops": 3000,
            "max": 16000
        },
        {
            "type": "IO2",
            "iops": 3000,
            "max": 64000
        }
    ]
    GCP_DISK_TYPES = [
        {
            "type": "PD-SSD",
            "iops": None,
            "max": None
        }
    ]
    SERVICES = ["data", "index", "query", "fts", "analytics", "eventing"]

    def __init__(self, cloud: str = "aws"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.projects = []
        # self.cluster_name = None
        # self.single_az = True
        # self.provider = "aws"
        # self.region = None
        # self.cidr = "10.1.0.0/16"
        # self.support_package = "DeveloperPro"
        # self.cluster_size = 3
        # self.machine_type = None
        # self.services = []
        self.clusters = []
        # self.root_volume_iops = "0"
        # self.root_volume_size = "100"
        # self.root_volume_type = "GP3"
        self.cloud = cloud

        if 'CBC_ACCESS_KEY' not in os.environ:
            raise CapellaDriverError("Please set CBC_ACCESS_KEY for Capella API access")

        if 'CBC_SECRET_KEY' not in os.environ:
            raise CapellaDriverError("Please set CBC_SECRET_KEY for Capella API access")

    def get_info(self):
        self.logger.info(f"Access Key:    {os.environ['CBC_ACCESS_KEY']}")
        self.logger.info(f"Secret Key:    {os.environ['CBC_SECRET_KEY']}")

    @property
    def regions(self):
        if self.cloud == "aws":
            return CloudBase.AWS_REGIONS
        elif self.cloud == "gcp":
            return CloudBase.GCP_REGIONS

    def capella_init(self):
        self.capella_get_clusters()

    def capella_get_projects(self) -> list[dict]:
        projects = []
        capella = CapellaSession()

        result = capella.api_get("/v2/projects")

        try:
            for item in result:
                element = {
                    "name": item["name"],
                    "id": item["id"]
                }
                projects.append(element)
        except Exception as err:
            raise CapellaDriverError(f"Error getting Capella projects: {err}")

        if len(projects) == 0:
            raise EmptyResultSet("Can not find any Capella projects.")

        self.projects = projects
        return self.projects

    def capella_get_clusters(self) -> list[dict]:
        capella = CapellaSession()
        self.clusters = capella.api_get("/v3/clusters")
        return self.clusters


class Network(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def list() -> list[dict]:
        cidr_list = []
        capella = CapellaSession()
        try:
            for item in CloudBase().capella_get_clusters():
                try:
                    cluster = capella.api_get(f"/v3/clusters/{item['id']}")
                    network_block = {
                        'cidr': cluster[0]["place"]["CIDR"]
                    }
                    cidr_list.append(network_block)
                except CapellaNotImplemented:
                    continue
            return cidr_list
        except KeyError:
            raise CapellaDriverError("Can not get CIDR from cluster record.")

    @property
    def cidr_list(self):
        for item in self.list():
            yield item['cidr']


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class SecurityGroup(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class MachineType(CloudBase):

    def __init__(self, cloud: str = "aws"):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cloud = cloud

    def list(self) -> list[dict]:
        if self.cloud == "aws":
            return CloudBase.AWS_MACHINE_TYPES
        elif self.cloud == "gcp":
            return CloudBase.GCP_MACHINE_TYPES

    def disk_types(self):
        if self.cloud == "aws":
            return CloudBase.AWS_DISK_TYPES
        elif self.cloud == "gcp":
            return CloudBase.GCP_DISK_TYPES


class Instance(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Image(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
