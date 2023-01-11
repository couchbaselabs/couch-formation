##
##

import argparse
import re
import lib.config as config
from lib.config import OperatingMode


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
        parent_parser.add_argument('--debug', action='store_true', help="Debug output", default=False)
        parent_parser.add_argument('--dev', action='store', help="Development Environment", type=int)
        parent_parser.add_argument('--test', action='store', help="Test Environment", type=int)
        parent_parser.add_argument('--prod', action='store', help="Prod Environment", type=int)
        parent_parser.add_argument('--app', action='store', help="Application Environment", type=int)
        parent_parser.add_argument('--sgw', action='store', help="Sync Gateway Environment", type=int)
        parent_parser.add_argument('--cloud', action='store', help="Cloud type", default='aws')
        parent_parser.add_argument('--zone', action='store_true', help="Use One Availability Zone", default=False)
        parent_parser.add_argument('--static', action='store_true', help="Assign Static IPs", default=False)
        parent_parser.add_argument('--dns', action='store_true', help="Update DNS", default=True)
        parent_parser.add_argument('--all', action='store_true', help="List all environments", default=False)
        parent_parser.add_argument('--standalone', action='store_true', help="Build standalone machine", default=False)
        parent_parser.add_argument('--min', action='store', help="Minimum node count", type=int, default=3)
        parent_parser.add_argument('--name', action='store', help="Environment name", type=name_arg)
        parent_parser.add_argument('--v3', action='store_true', help="Use new framework")
        parent_parser.add_argument('--noop', action='store', help=argparse.SUPPRESS)
        image_parser = argparse.ArgumentParser(add_help=False)
        image_parser.add_argument('--list', action='store_true', help='List images')
        image_parser.add_argument('--build', action='store_true', help='Build image')
        image_parser.add_argument('--delete', action='store_true', help='Delete image')
        image_parser.add_argument('--image', action='store', help='Image name')
        image_parser.add_argument('--json', action='store_true', help='Output in JSON format', default=False)
        image_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        net_parser = argparse.ArgumentParser(add_help=False)
        net_parser.add_argument('--list', action='store_true', help='List network database')
        net_parser.add_argument('--domain', action='store_true', help='Add domain')
        net_parser.add_argument('--cidr', action='store_true', help='Add network')
        net_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        vpc_parser = argparse.ArgumentParser(add_help=False)
        vpc_parser.add_argument('--create', action='store_true', help='Create a VPC')
        vpc_parser.add_argument('--destroy', action='store_true', help='Destroy a VPC')
        vpc_parser.add_argument('--show', action='store_true', help='Show VPC')
        vpc_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        log_parser = argparse.ArgumentParser(add_help=False)
        # log_parser.add_argument('--image', action='store_true', help='Show image build logs')
        # log_parser.add_argument('--vpc', action='store_true', help='Show image build logs')
        # log_parser.add_argument('--cluster', action='store_true', help='Show image build logs')
        # log_parser.add_argument('--applog', action='store_true', help='Show image build logs')
        # log_parser.add_argument('--sgwlog', action='store_true', help='Show image build logs')
        log_parser.add_argument('-c', '--count', action='store', help='Number of lines to show', type=int, default=25)
        log_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        subparsers = parser.add_subparsers(dest='command')
        image_mode = subparsers.add_parser('image', help="Manage CB Images", parents=[parent_parser, image_parser], add_help=False)

        create_mode = subparsers.add_parser('create', help="Create Nodes", parents=[parent_parser], add_help=False)
        create_action = create_mode.add_subparsers(dest='create_command')
        create_action_cluster = create_action.add_parser('cluster', help="Create a Couchbase Cluster", parents=[parent_parser], add_help=False)
        create_action_app = create_action.add_parser('app', help="Create App Nodes", parents=[parent_parser], add_help=False)
        create_action_sgw = create_action.add_parser('sgw', help="Create Sync Gateway Nodes", parents=[parent_parser], add_help=False)
        create_action_generic = create_action.add_parser('generic', help="Generic Nodes", parents=[parent_parser], add_help=False)

        deploy_mode = subparsers.add_parser('deploy', help="Deploy Nodes", parents=[parent_parser], add_help=False)

        destroy_mode = subparsers.add_parser('destroy', help="Destroy Nodes", parents=[parent_parser], add_help=False)
        destroy_action = destroy_mode.add_subparsers(dest='destroy_command')
        destroy_action_cluster = destroy_action.add_parser('cluster', help="Destroy a Couchbase Cluster", parents=[parent_parser], add_help=False)
        destroy_action_app = destroy_action.add_parser('app', help="Destroy App Nodes", parents=[parent_parser], add_help=False)
        destroy_action_sgw = destroy_action.add_parser('sgw', help="Destroy Sync Gateway Nodes", parents=[parent_parser], add_help=False)
        destroy_action_generic = destroy_action.add_parser('generic', help="Destroy Generic Nodes", parents=[parent_parser], add_help=False)

        remove_mode = subparsers.add_parser('remove', help="Remove Environments", parents=[parent_parser], add_help=False)

        list_mode = subparsers.add_parser('list', help="List Information", parents=[parent_parser], add_help=False)
        list_action = list_mode.add_subparsers(dest='list_command')
        list_action_image = list_action.add_parser('images', help="List images", parents=[parent_parser], add_help=False)
        list_action_nodes = list_action.add_parser('nodes', help="List nodes", parents=[parent_parser], add_help=False)

        show_mode = subparsers.add_parser('show', help="Show Attributes", parents=[parent_parser], add_help=False)
        show_action = show_mode.add_subparsers(dest='show_command')
        show_action_nodes = show_action.add_parser('nodes', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_node_opt = show_action_nodes.add_subparsers(dest='show_node_command')
        show_action_cluster = show_action_node_opt.add_parser('cluster', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_cluster = show_action_node_opt.add_parser('app', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_cluster = show_action_node_opt.add_parser('sgw', help="Show Nodes", parents=[parent_parser], add_help=False)
        show_action_cluster = show_action_node_opt.add_parser('generic', help="Show Nodes", parents=[parent_parser], add_help=False)

        net_mode = subparsers.add_parser('net', help="Static Network Configuration", parents=[parent_parser, net_parser], add_help=False)
        vpc_mode = subparsers.add_parser('vpc', help="Create VPC", parents=[parent_parser, vpc_parser], add_help=False)
        ssh_mode = subparsers.add_parser('ssh', help="Create SSH Keys", parents=[parent_parser], add_help=False)

        log_mode = subparsers.add_parser('logs', help="View logs", parents=[parent_parser, log_parser], add_help=False)
        log_action = log_mode.add_subparsers(dest='log_command')
        log_action_image = log_action.add_parser('image', help="Get image build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action_vpc = log_action.add_parser('vpc', help="Get vpc build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action_cluster = log_action.add_parser('cluster', help="Get cluster build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action_app = log_action.add_parser('app', help="Get app build logs", parents=[parent_parser, log_parser], add_help=False)
        log_action_sgw = log_action.add_parser('sgw', help="Get sgw build logs", parents=[parent_parser, log_parser], add_help=False)

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

        self.parameters = parser.parse_args()

    @property
    def args(self):
        return self.parameters

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
