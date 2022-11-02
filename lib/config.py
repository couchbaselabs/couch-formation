##
##

import os
import warnings
from enum import Enum
from lib.drivers.network import NetworkDriver


class RunMode(Enum):
    Image = 0
    Node = 1


warnings.filterwarnings("ignore")
cloud = "aws"
debug_level = 3
env_name = None
sync_gateway = False
sgw_node_count = 1
app_node = False
app_node_count = 1
static_ip = False
public_ip = True
update_dns = False
generic_mode = False
cb_node_min = 3
dns_domain = None
single_az = False
test_mode = False
run_mode = RunMode.Node.value
cidr_util = NetworkDriver()
cloud_base = None
cloud_network = None
cloud_subnet = None
cloud_security_group = None
cloud_machine_type = None
cloud_instance = None
ssh_key = None
cloud_image = None

lib_dir = os.path.dirname(os.path.realpath(__file__))
package_dir = os.path.dirname(lib_dir)


def enable_cloud(name: str) -> None:
    driver = None
    global cloud_base, \
        cloud_network, \
        cloud_subnet, \
        cloud_security_group, \
        cloud_machine_type, \
        cloud_instance, \
        ssh_key, \
        cloud_image

    if name == 'aws':
        module = __import__('lib.drivers.aws')
        driver = module.drivers.aws
    elif name == 'gcp':
        module = __import__('lib.drivers.gcp')
        driver = module.drivers.gcp
    elif name == 'azure':
        module = __import__('lib.drivers.azure')
        driver = module.drivers.azure
    elif name == 'vmware':
        module = __import__('lib.drivers.vmware')
        driver = module.drivers.vmware
    elif name == 'capella':
        module = __import__('lib.drivers.capella')
        driver = module.drivers.capella
    cloud_base = getattr(driver, 'CloudBase')
    cloud_network = getattr(driver, 'Network')
    cloud_subnet = getattr(driver, 'Subnet')
    cloud_security_group = getattr(driver, 'SecurityGroup')
    cloud_machine_type = getattr(driver, 'MachineType')
    cloud_instance = getattr(driver, 'Instance')
    ssh_key = getattr(driver, 'SSHKey')
    cloud_image = getattr(driver, 'Image')

    print(f"Loaded Cloud Driver {name.upper()} version {cloud_base.VERSION}")
