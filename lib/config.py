##
##

import os
from enum import Enum


class RunMode(Enum):
    Image = 0
    Node = 1


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

lib_dir = os.path.dirname(os.path.realpath(__file__))
package_dir = os.path.dirname(lib_dir)
