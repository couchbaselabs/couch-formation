##
##

import logging
import jinja2
import os
import ipaddress
from lib.ask import ask
from lib.exceptions import fatalError
from lib.capsessionmgr import capella_session
from lib.capexceptions import CapellaNotImplemented


class CapellaDriverError(fatalError):
    pass


class capella(object):
    TEMPLATE = False
    CONFIG_FILE = "main.tf"
    OUTPUT_FILE = "outputs.tf"
    VARIABLES = []
    SUPPORT_PACKAGE = [
        "Basic",
        "DeveloperPro",
        "Enterprise"
    ]
    CLOUD_PROVIDER = [
        "aws"
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
    SERVICES = ["data", "index", "query", "fts", "analytics", "eventing"]
    MAIN_TEMPLATE = """
terraform {
  required_providers {
    couchbasecapella = {
      source = "couchbasecloud/couchbasecapella"
      version = "0.1.1"
    }
  }
}

provider "couchbasecapella" {}

resource "couchbasecapella_hosted_cluster" "capella_cluster" {
  name        = "{{ CAPELLA_CLUSTER }}"
  project_id  = "{{ CAPELLA_PROJECT }}"
  place {
    single_az = {{ CAPELLA_SINGLE_AZ }}
    hosted {
      provider = "{{ CAPELLA_PROVIDER }}"
      region   = "{{ CAPELLA_REGION }}"
      cidr     = "{{ CAPELLA_CIDR }}"
    }
  }
  support_package {
    timezone = "GMT"
    support_package_type     = "{{ CAPELLA_SUPPORT_PACKAGE }}"
  }
  servers {
    size     = "{{ CAPELLA_CLUSTER_SIZE }}"
    compute  = "{{ CAPELLA_COMPUTE_TYPE }}"
    services = [{{ CAPELLA_SERVICES }}]
    storage {
      storage_type = "{{ CAPELLA_STORAGE_TYPE }}"
      iops = "{{ CAPELLA_STORAGE_IOPS }}"
      storage_size = "{{ CAPELLA_STORAGE_SIZE }}"
    }
  }
}
"""
    OUTPUT_TEMPLATE = """
output "cluster-id" {
  value = couchbasecapella_hosted_cluster.capella_cluster.id
}
"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tf_json = {}
        self.tf_config_json = {}
        self.project = None
        self.cluster_name = None
        self.single_az = True
        self.provider = "aws"
        self.region = None
        self.cidr = "10.1.0.0/16"
        self.support_package = "DeveloperPro"
        self.cluster_size = 3
        self.machine_type = None
        self.services = []
        self.clusters = []
        self.root_volume_iops = "0"
        self.root_volume_size = "100"
        self.root_volume_type = "GP3"

        if 'CBC_ACCESS_KEY' not in os.environ:
            raise CapellaDriverError("Please set CBC_ACCESS_KEY for Capella API access")

        if 'CBC_SECRET_KEY' not in os.environ:
            raise CapellaDriverError("Please set CBC_SECRET_KEY for Capella API access")

    def capella_init(self, environment):
        inquire = ask()
        environment = environment.replace(':', '-')
        self.capella_get_clusters()

        self.project = self.capella_get_project()
        self.cluster_name = inquire.ask_text("Cluster name", recommendation=environment)
        self.single_az = inquire.ask_bool("Single AZ", recommendation="false")
        provider_option = inquire.ask_list("Cloud provider", capella.CLOUD_PROVIDER)
        self.provider = capella.CLOUD_PROVIDER[provider_option]
        if self.provider == "aws":
            region_option = inquire.ask_list("Cloud region", capella.AWS_REGIONS)
            self.region = capella.AWS_REGIONS[region_option]
        self.cidr = self.capella_get_cidr()
        support_package_option = inquire.ask_list("Support package", capella.SUPPORT_PACKAGE)
        self.support_package = capella.SUPPORT_PACKAGE[support_package_option]
        self.cluster_size = int(inquire.ask_text("Cluster size", recommendation="3"))
        if self.provider == "aws":
            machine_type_option = inquire.ask_list("Machine type", capella.AWS_MACHINE_TYPES)
            self.machine_type = capella.AWS_MACHINE_TYPES[machine_type_option]['name']
        self.services = inquire.ask_multi("Services", capella.SERVICES, ["data", "index", "query"])
        self.root_volume_size = inquire.ask_text("Storage size", recommendation="100")
        if self.provider == "aws":
            self.root_volume_iops = inquire.ask_text("Storage IOPS", recommendation="3000")
            self.root_volume_type = inquire.ask_text("Storage type", recommendation="GP3")

    def capella_get_project(self, default=None, write=None):
        inquire = ask()
        options = []
        capella = capella_session()

        result = capella.api_get("/v2/projects")

        try:
            for item in result:
                element = {}
                element["name"] = item["name"]
                element["description"] = item["id"]
                options.append(element)
        except Exception as err:
            raise CapellaDriverError(f"Error getting Capella projects: {err}")

        if len(options) == 0:
            raise CapellaDriverError("Can not fine any Capella projects.")

        selection = inquire.ask_search("Capella project", options)

        self.project = selection["description"]
        return self.project

    def capella_get_clusters(self):
        capella = capella_session()
        self.clusters = capella.api_get("/v3/clusters")

    def capella_get_cidrs(self):
        cidr_list = []
        capella = capella_session()
        try:
            for item in self.clusters:
                try:
                    cluster = capella.api_get(f"/v3/clusters/{item['id']}")
                    cidr_list.append(cluster[0]["place"]["CIDR"])
                except CapellaNotImplemented:
                    continue
            return cidr_list
        except KeyError:
            raise CapellaDriverError("Can not get CIDR from cluster record.")

    def find_cidr(self, subnet: str, cidr_list: list[str]) -> bool:
        sub_network = ipaddress.ip_network(subnet)
        for cidr in cidr_list:
            cmp_network = ipaddress.ip_network(cidr)
            if sub_network.overlaps(cmp_network):
                return True
        return False

    def capella_get_cidr(self, default=None, write=None):
        cluster_cidr = None
        inquire = ask()
        cidr_in_use = self.capella_get_cidrs()
        selection = inquire.ask_text("Cluster CIDR pool", recommendation=self.cidr)
        for subnet in list(ipaddress.ip_network(selection).subnets(new_prefix=23)):
            if self.find_cidr(subnet.exploded, cidr_in_use):
                continue
            else:
                cluster_cidr = subnet.exploded
                break
        if cluster_cidr is None:
            raise CapellaDriverError(f"can not compute available cluster cidr from pool {selection}")
        return cluster_cidr

    def write_tf(self, directory):
        output_file = directory + '/' + capella.CONFIG_FILE
        substitutions = {
            "CAPELLA_PROJECT": self.project,
            "CAPELLA_CLUSTER": self.cluster_name,
            "CAPELLA_SINGLE_AZ": str(self.single_az).lower(),
            "CAPELLA_PROVIDER": self.provider,
            "CAPELLA_REGION": self.region,
            "CAPELLA_CIDR": self.cidr,
            "CAPELLA_SUPPORT_PACKAGE": self.support_package,
            "CAPELLA_CLUSTER_SIZE": self.cluster_size,
            "CAPELLA_COMPUTE_TYPE": self.machine_type,
            "CAPELLA_SERVICES": ','.join(f'"{s}"' for s in self.services),
            "CAPELLA_STORAGE_TYPE": self.root_volume_type,
            "CAPELLA_STORAGE_IOPS": self.root_volume_iops,
            "CAPELLA_STORAGE_SIZE": self.root_volume_size
        }

        raw_template = jinja2.Template(capella.MAIN_TEMPLATE)
        format_template = raw_template.render(substitutions)
        try:
            with open(output_file, 'w') as write_file:
                write_file.write(format_template)
                write_file.write("\n")
                write_file.close()
        except OSError as err:
            raise CapellaDriverError(f"Can not write to new main file: {err}")

        raw_template = jinja2.Template(capella.OUTPUT_TEMPLATE)
        format_template = raw_template.render(substitutions)
        output_file = directory + '/' + capella.OUTPUT_FILE
        try:
            with open(output_file, 'w') as write_file:
                write_file.write(format_template)
                write_file.write("\n")
                write_file.close()
        except OSError as err:
            raise CapellaDriverError(f"Can not write to new output file: {err}")
