##
##

import argparse

class params(object):

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
        image_parser = argparse.ArgumentParser(add_help=False)
        image_parser.add_argument('--list', action='store_true', help='List images')
        image_parser.add_argument('--build', action='store_true', help='Build image')
        image_parser.add_argument('--delete', action='store_true', help='Delete image')
        image_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        net_parser = argparse.ArgumentParser(add_help=False)
        net_parser.add_argument('--list', action='store_true', help='List network database')
        net_parser.add_argument('--domain', action='store_true', help='Add domain')
        net_parser.add_argument('--cidr', action='store_true', help='Add network')
        net_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        subparsers = parser.add_subparsers(dest='command')
        image_mode = subparsers.add_parser('image', help="Manage CB Images", parents=[parent_parser, image_parser], add_help=False)
        create_mode = subparsers.add_parser('create', help="Create Nodes", parents=[parent_parser], add_help=False)
        deploy_mode = subparsers.add_parser('deploy', help="Deploy Nodes", parents=[parent_parser], add_help=False)
        destroy_mode = subparsers.add_parser('destroy', help="Destroy Nodes", parents=[parent_parser], add_help=False)
        remove_mode = subparsers.add_parser('remove', help="Remove Environments", parents=[parent_parser], add_help=False)
        list_mode = subparsers.add_parser('list', help="List Nodes", parents=[parent_parser], add_help=False)
        net_mode = subparsers.add_parser('net', help="Static Network Configuration", parents=[parent_parser, net_parser], add_help=False)
        self.parser = parser
        self.image_parser = image_mode
        self.create_parser = create_mode
        self.deploy_parser = deploy_mode
        self.destroy_parser = destroy_mode
        self.remove_parser = remove_mode
        self.list_parser = list_mode
        self.net_parser = net_mode
