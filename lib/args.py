##
##

import argparse
import re
import lib.config as config
import logging
from lib.util.db_mgr import LocalDB
from lib.config import OperatingMode, CloudConfig

logger = logging.getLogger('cf.args')
logger.addHandler(logging.NullHandler())


def name_arg(value):
    p = re.compile(r"^[a-z]([-a-z0-9]*[a-z0-9])?$")
    if p.match(value):
        return value
    else:
        raise argparse.ArgumentTypeError("name must comply with RFC1035")


class Parameters(object):

    def __init__(self):
        parser = argparse.ArgumentParser(add_help=False)
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument('--cloud', action='store', help="Cloud type", default='aws')
        parent_parser.add_argument('--zone', action='store', help="Use One Availability Zone")
        parent_parser.add_argument('--static', action='store_true', help="Assign Static IPs", default=False)
        parent_parser.add_argument('--dns', action='store_true', help="Update DNS", default=True)
        parent_parser.add_argument('--all', action='store_true', help="All qualifier", default=False)
        parent_parser.add_argument('--min', action='store', help="Minimum node count", type=int, default=3)
        parent_parser.add_argument('--name', action='store', help="Environment name", type=name_arg)
        parent_parser.add_argument('-d', '--debug', action='store_true', help="Debug output")
        parent_parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
        parent_parser.add_argument('-y', '--yes', action='store_true', help="Assume yes confirmation")
        image_parser = argparse.ArgumentParser(add_help=False)
        image_parser.add_argument('--image', action='store', help='Image name')
        image_parser.add_argument('--json', action='store_true', help='Output in JSON format', default=False)
        image_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        net_parser = argparse.ArgumentParser(add_help=False)
        net_parser.add_argument('--list', action='store_true', help='List network database')
        net_parser.add_argument('--domain', action='store_true', help='Add domain')
        net_parser.add_argument('--cidr', action='store_true', help='Add network')
        net_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')

        vpc_parser = argparse.ArgumentParser(add_help=False)
        vpc_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')

        log_parser = argparse.ArgumentParser(add_help=False)
        log_parser.add_argument('-c', '--count', action='store', help='Number of lines to show', type=int, default=25)
        log_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')

        db_parser = argparse.ArgumentParser(add_help=False)
        db_parser.add_argument('-f', '--fix', action='store_true', help='Fix issues')

        subparsers = parser.add_subparsers(dest='command')

        subparsers.add_parser('version', help="Show versions", parents=[parent_parser], add_help=False)

        image_mode = subparsers.add_parser('image', help="Manage CB Images", parents=[parent_parser, image_parser], add_help=False)
        image_action = image_mode.add_subparsers(dest='image_command')
        image_action.add_parser('list', help="List images", parents=[parent_parser, image_parser], add_help=False)
        image_action.add_parser('build', help="Build images", parents=[parent_parser, image_parser], add_help=False)
        image_action.add_parser('delete', help="Delete images", parents=[parent_parser, image_parser], add_help=False)

        create_mode = subparsers.add_parser('create', help="Create Nodes", parents=[parent_parser], add_help=False)
        create_action = create_mode.add_subparsers(dest='create_command')
        create_action.add_parser('cluster', help="Create a Couchbase Cluster", parents=[parent_parser], add_help=False)
        create_action.add_parser('app', help="Create App Nodes", parents=[parent_parser], add_help=False)
        create_action.add_parser('sgw', help="Create Sync Gateway Nodes", parents=[parent_parser], add_help=False)
        create_action.add_parser('generic', help="Generic Nodes", parents=[parent_parser], add_help=False)

        deploy_mode = subparsers.add_parser('deploy', help="Deploy Nodes", parents=[parent_parser], add_help=False)
        deploy_action = deploy_mode.add_subparsers(dest='deploy_command')
        deploy_action.add_parser('cluster', help="Deploy a Couchbase Cluster", parents=[parent_parser], add_help=False)
        deploy_action.add_parser('app', help="Deploy App Nodes", parents=[parent_parser], add_help=False)
        deploy_action.add_parser('sgw', help="Deploy Sync Gateway Nodes", parents=[parent_parser], add_help=False)
        deploy_action.add_parser('generic', help="Deploy Generic Nodes", parents=[parent_parser], add_help=False)

        destroy_mode = subparsers.add_parser('destroy', help="Destroy Nodes", parents=[parent_parser], add_help=False)
        destroy_action = destroy_mode.add_subparsers(dest='destroy_command')
        destroy_action.add_parser('cluster', help="Destroy a Couchbase Cluster", parents=[parent_parser], add_help=False)
        destroy_action.add_parser('app', help="Destroy App Nodes", parents=[parent_parser], add_help=False)
        destroy_action.add_parser('sgw', help="Destroy Sync Gateway Nodes", parents=[parent_parser], add_help=False)
        destroy_action.add_parser('generic', help="Destroy Generic Nodes", parents=[parent_parser], add_help=False)

        remove_mode = subparsers.add_parser('remove', help="Remove Environments", parents=[parent_parser], add_help=False)

        list_mode = subparsers.add_parser('list', help="List Information", parents=[parent_parser], add_help=False)
        list_action = list_mode.add_subparsers(dest='list_command')
        list_action.add_parser('images', help="List images", parents=[parent_parser], add_help=False)
        list_action.add_parser('nodes', help="List nodes", parents=[parent_parser], add_help=False)

        show_mode = subparsers.add_parser('show', help="Show Attributes", parents=[parent_parser], add_help=False)
        show_action = show_mode.add_subparsers(dest='show_command')
        show_action_nodes = show_action.add_parser('nodes', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_node_opt = show_action_nodes.add_subparsers(dest='show_node_command')
        show_action_node_opt.add_parser('cluster', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_node_opt.add_parser('app', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_node_opt.add_parser('sgw', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_node_opt.add_parser('generic', help="Show Nodes", parents=[parent_parser], add_help=False)

        net_mode = subparsers.add_parser('net', help="Static Network Configuration", parents=[parent_parser, net_parser], add_help=False)

        vpc_mode = subparsers.add_parser('vpc', help="Create VPC", parents=[parent_parser, vpc_parser], add_help=False)
        vpc_action = vpc_mode.add_subparsers(dest='vpc_command')
        vpc_action.add_parser('create', help="Create VPC", parents=[parent_parser], add_help=False)
        vpc_action.add_parser('destroy', help="Destroy VPC", parents=[parent_parser], add_help=False)
        vpc_action.add_parser('clean', help="Clean VPC", parents=[parent_parser], add_help=False)
        vpc_action.add_parser('show', help="Show VPC", parents=[parent_parser], add_help=False)

        ssh_mode = subparsers.add_parser('ssh', help="Create SSH Keys", parents=[parent_parser], add_help=False)

        log_mode = subparsers.add_parser('logs', help="View logs", parents=[parent_parser, log_parser], add_help=False)
        log_action = log_mode.add_subparsers(dest='log_command')
        log_action.add_parser('image', help="Get image build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action.add_parser('vpc', help="Get vpc build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action.add_parser('cluster', help="Get cluster build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action.add_parser('app', help="Get app build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action.add_parser('sgw', help="Get sgw build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action.add_parser('generic', help="Get sgw build logs", parents=[parent_parser, log_parser], add_help=False)

        db_mode = subparsers.add_parser('db', help="Catalog manager", parents=[parent_parser], add_help=False)
        db_action = db_mode.add_subparsers(dest='db_command')
        db_action.add_parser('check', help="Check the catalog", parents=[parent_parser, db_parser], add_help=False)

        subparsers.add_parser('auth', help="Configure Authorization", parents=[parent_parser], add_help=False)

        self.parser = parser
        self.image_parser = image_mode
        self.create_parser = create_mode
        self.deploy_parser = deploy_mode
        self.destroy_parser = destroy_mode
        self.remove_parser = remove_mode
        self.list_parser = list_mode
        self.net_parser = net_mode
        self.vpc_parser = vpc_mode
        self.ssh_parser = ssh_mode
        self.log_parser = log_mode

        self.parameters, self.remainder = parser.parse_known_args()

    @property
    def args(self):
        return self.parameters

    def update_options(self):
        config.cloud_config = CloudConfig[config.cloud].value()
        db = LocalDB()
        stored = db.get_config()
        if stored:
            config.update_options(stored)
            logger.debug(f"Stored settings: {config.cloud_config.as_dict}")
        config.process_options(self.remainder)
        logger.debug(f"Settings with args: {config.cloud_config.as_dict}")

    def update_config(self):
        if self.parameters.debug:
            config.enable_debug = self.parameters.debug
        if self.parameters.name:
            config.env_name = self.parameters.name
        if self.parameters.cloud:
            config.cloud = self.parameters.cloud
        if self.parameters.zone:
            config.cloud_zone = self.parameters.zone
        if self.parameters.static:
            config.static_ip = self.parameters.static
        if self.parameters.min:
            config.cb_node_min = config.app_node_count = config.sgw_node_count = self.parameters.min
        if self.parameters.dns:
            config.update_dns = self.parameters.dns
        if self.parameters.yes:
            config.assume_yes = self.parameters.yes
        if 'create' in self.parameters:
            if self.parameters.create:
                config.operating_mode = OperatingMode.CREATE.value
        if 'destroy' in self.parameters:
            if self.parameters.destroy:
                config.operating_mode = OperatingMode.DESTROY.value
        if 'build' in self.parameters:
            if self.parameters.build:
                config.operating_mode = OperatingMode.BUILD.value

        if 'list_command' in self.parameters:
            self.parameters.v3 = True
