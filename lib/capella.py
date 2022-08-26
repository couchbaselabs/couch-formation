##
##

import logging
import jinja2
from lib.ask import ask
from lib.exceptions import nonFatalError, fatalError


class CapellaDriverError(fatalError):
    pass


class capella(object):
    TEMPLATE = False
    CONFIG_FILE = "main.tf"
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

resource "couchbasecapella_project" "project" {
  name = "{{ CAPELLA_PROJECT }}"
}

resource "couchbasecapella_hosted_cluster" "cluster" {
  name        = "{{ CAPELLA_CLUSTER }}"
  project_id  = couchbasecapella_project.project.id
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

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tf_json = {}
        self.tf_config_json = {}
        self.project = None
        self.cluster_name = None
        self.single_az = True
        self.provider = "aws"
        self.region = None
        self.cidr = "10.1.2.0/23"
        self.support_package = "DeveloperPro"
        self.cluster_size = 3
        self.machine_type = None
        self.services = []
        self.root_volume_iops = "0"
        self.root_volume_size = "100"
        self.root_volume_type = "GP3"

    def capella_init(self, environment):
        inquire = ask()
        environment = environment.replace(':', '-')

        self.project = inquire.ask_text("Project name", recommendation=environment)
        self.cluster_name = inquire.ask_text("Cluster name", recommendation=environment)
        self.single_az = inquire.ask_bool("Single AZ", recommendation="false")
        provider_option = inquire.ask_list("Cloud provider", capella.CLOUD_PROVIDER)
        self.provider = capella.CLOUD_PROVIDER[provider_option]
        if self.provider == "aws":
            region_option = inquire.ask_list("Cloud region", capella.AWS_REGIONS)
            self.region = capella.AWS_REGIONS[region_option]
        self.cidr = inquire.ask_text("Cluster CIDR", recommendation="10.1.2.0/23")
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

    def write_tf(self, directory):
        output_file = directory + '/' + capella.CONFIG_FILE

        raw_template = jinja2.Template(capella.MAIN_TEMPLATE)
        format_template = raw_template.render(
            CAPELLA_PROJECT=self.project,
            CAPELLA_CLUSTER=self.cluster_name,
            CAPELLA_SINGLE_AZ=str(self.single_az).lower(),
            CAPELLA_PROVIDER=self.provider,
            CAPELLA_REGION=self.region,
            CAPELLA_CIDR=self.cidr,
            CAPELLA_SUPPORT_PACKAGE=self.support_package,
            CAPELLA_CLUSTER_SIZE=self.cluster_size,
            CAPELLA_COMPUTE_TYPE=self.machine_type,
            CAPELLA_SERVICES=','.join(f'"{s}"' for s in self.services),
            CAPELLA_STORAGE_TYPE=self.root_volume_type,
            CAPELLA_STORAGE_IOPS=self.root_volume_iops,
            CAPELLA_STORAGE_SIZE=self.root_volume_size
        )
        try:
            with open(output_file, 'w') as write_file:
                write_file.write(format_template)
                write_file.write("\n")
                write_file.close()
        except OSError as err:
            raise CapellaDriverError(f"Can not write to new node file: {err}")
