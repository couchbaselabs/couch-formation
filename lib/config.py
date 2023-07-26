##
##

import os
import warnings
import argparse
import attr
from enum import Enum
from lib.drivers.network import NetworkDriver
from lib.util.envmgr import CatalogRoot
from lib.util.filemgr import FileManager
from lib.config_values import AWSConfig, GCPConfig, AzureConfig, VMWareConfig, CapellaConfig


@attr.s
class CloudProviders(object):
    clouds = [
        "aws",
        "gcp",
        "azure",
        "vmware",
        "capella"
    ]


class CloudConfig(Enum):
    aws = AWSConfig
    gcp = GCPConfig
    azure = AzureConfig
    vmware = VMWareConfig
    capella = CapellaConfig


class OperatingMode(Enum):
    CREATE = 0
    DESTROY = 1
    SHOW = 2
    LOG = 3
    BUILD = 4
    LIST = 5
    DELETE = 6


warnings.filterwarnings("ignore")
config_version = 1
cloud_driver_version = None
cloud_operator_version = None
cloud = "aws"
region = None
debug_level = 3
enable_debug: False
env_name = None
sync_gateway = False
sgw_node_count = 1
app_node = False
app_node_count = 1
static_ip = False
public_ip = True
update_dns = False
domain_name: None
generic_mode = False
cb_node_min = 3
dns_domain = None
single_az = False
cloud_zone = None
cloud_zone_cycle = None
test_mode = False
assume_yes = False
operating_mode = OperatingMode.CREATE.value
catalog_target = CatalogRoot.INVENTORY
cidr_util = NetworkDriver()
cloud_auth = None
cloud_data = None
cloud_base = None
cloud_network = None
cloud_subnet = None
cloud_security_group = None
cloud_machine_type = None
cloud_instance = None
ssh_key = None
cloud_image = None
cloud_operator = None
default_debug_file = 'cf_debug.log'
cloud_config = AWSConfig()

lib_dir = os.path.dirname(os.path.realpath(__file__))
package_dir = os.path.dirname(lib_dir)

if 'CLOUD_MANAGER_DATABASE_LOCATION' in os.environ:
    catalog_root = os.environ['CLOUD_MANAGER_DATABASE_LOCATION']
else:
    catalog_root = f"{package_dir}/db"

if 'CLOUD_MANAGER_CONFIGURATION' in os.environ:
    cfg_dir = os.environ['CLOUD_MANAGER_CONFIGURATION']
else:
    cfg_dir = f"{os.environ.get('HOME')}/.config/couch-formation"

FileManager().create_dir(cfg_dir)


def update_options(settings: dict) -> None:
    cloud_config.from_dict(settings)


def process_options(remainder: list[str]) -> None:
    global cloud_config
    cloud_parser = argparse.ArgumentParser(add_help=False)
    for arg in cloud_config.get_values.keys():
        cloud_parser.add_argument(f"--{arg}", action='store')
    options, unknown = cloud_parser.parse_known_args(remainder)
    cloud_config.from_namespace(options)


def process_params(parameters: argparse.Namespace) -> None:
    global enable_debug, \
        env_name, \
        cloud, \
        cloud_zone, \
        static_ip, \
        cb_node_min, \
        app_node_count, \
        sgw_node_count, \
        update_dns, \
        domain_name, \
        operating_mode, \
        assume_yes, \
        cloud_config
    if parameters.debug:
        enable_debug = parameters.debug
    if parameters.name:
        env_name = parameters.name
    if parameters.cloud:
        cloud = parameters.cloud
    if parameters.zone:
        cloud_zone = parameters.zone
    if parameters.static:
        static_ip = parameters.static
    if parameters.min:
        cb_node_min = app_node_count = sgw_node_count = parameters.min
    if parameters.dns:
        update_dns = parameters.dns
    if parameters.yes:
        assume_yes = parameters.yes
    if 'create' in parameters:
        if parameters.create:
            operating_mode = OperatingMode.CREATE.value
    if 'destroy' in parameters:
        if parameters.destroy:
            operating_mode = OperatingMode.DESTROY.value
    if 'build' in parameters:
        if parameters.build:
            operating_mode = OperatingMode.BUILD.value
    cloud_config = CloudConfig[cloud].value()


def enable_cloud(name: str) -> None:
    driver = None
    operator = None
    global cloud_base, \
        cloud_auth, \
        cloud_network, \
        cloud_subnet, \
        cloud_security_group, \
        cloud_machine_type, \
        cloud_instance, \
        ssh_key, \
        cloud_image, \
        cloud_operator, \
        cloud_driver_version, \
        cloud_operator_version

    if name == 'aws':
        module = __import__('lib.drivers.aws')
        driver = module.drivers.aws
        module = __import__('lib.hcl.aws')
        operator = module.hcl.aws
    elif name == 'gcp':
        module = __import__('lib.drivers.gcp')
        driver = module.drivers.gcp
        module = __import__('lib.hcl.gcp')
        operator = module.hcl.gcp
    elif name == 'azure':
        module = __import__('lib.drivers.azure')
        driver = module.drivers.azure
        module = __import__('lib.hcl.azure')
        operator = module.hcl.azure
    elif name == 'vmware':
        module = __import__('lib.drivers.vmware')
        driver = module.drivers.vmware
        module = __import__('lib.hcl.vmware')
        operator = module.hcl.vmware
    elif name == 'capella':
        module = __import__('lib.drivers.capella')
        driver = module.drivers.capella
        module = __import__('lib.hcl.capella')
        operator = module.hcl.capella
    cloud_auth = getattr(driver, 'CloudInit')
    cloud_base = getattr(driver, 'CloudBase')
    cloud_network = getattr(driver, 'Network')
    cloud_subnet = getattr(driver, 'Subnet')
    cloud_security_group = getattr(driver, 'SecurityGroup')
    cloud_machine_type = getattr(driver, 'MachineType')
    cloud_instance = getattr(driver, 'Instance')
    ssh_key = getattr(driver, 'SSHKey')
    cloud_image = getattr(driver, 'Image')
    cloud_operator = getattr(operator, 'CloudDriver')
    cloud_driver_version = cloud_base.VERSION
    cloud_operator_version = cloud_operator.VERSION
