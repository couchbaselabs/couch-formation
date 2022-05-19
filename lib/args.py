##
##

import argparse

class params(object):

    def __init__(self):
        parser = argparse.ArgumentParser(add_help=False)
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument('--template', action='store', help="Template file")
        parent_parser.add_argument('--globals', action='store', help="Global variables file")
        parent_parser.add_argument('--locals', action='store', help="Local variables file")
        parent_parser.add_argument('--debug', action='store', help="Debug level", type=int, default=3)
        parent_parser.add_argument('--load', action='store', help="Variable file")
        parent_parser.add_argument('--dev', action='store', help="Development Environment", type=int)
        parent_parser.add_argument('--test', action='store', help="Test Environment", type=int)
        parent_parser.add_argument('--prod', action='store', help="Prod Environment", type=int)
        parent_parser.add_argument('--app', action='store', help="Application Environment", type=int)
        parent_parser.add_argument('--cloud', action='store', help="Cloud type", default='aws')
        parent_parser.add_argument('--singlezone', action='store_true', help="Use One Availability Zone", default=False)
        parent_parser.add_argument('--refresh', action='store_true', help="Overwrite configuration files", default=False)
        parent_parser.add_argument('--host', action='store', help="vCenter Host Name")
        parent_parser.add_argument('--user', action='store', help="vCenter Administrative User")
        parent_parser.add_argument('--password', action='store', help="vCenter Admin User Password")
        parent_parser.add_argument('--static', action='store_true', help="Assign Static IPs", default=False)
        parent_parser.add_argument('--dns', action='store_true', help="Update DNS", default=True)
        image_parser = argparse.ArgumentParser(add_help=False)
        image_parser.add_argument('--list', action='store_true', help='List images')
        image_parser.add_argument('--build', action='store_true', help='Build image')
        image_parser.add_argument('--delete', action='store_true', help='Delete image')
        image_parser.add_argument('--type', action='store', help='OS Type', default='linux')
        image_parser.add_argument('--name', action='store', help='OS Name', default='ubuntu')
        image_parser.add_argument('--version', action='store', help='OS Version')
        image_parser.add_argument('--image', action='store', help='Image Name', default=None)
        image_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        net_parser = argparse.ArgumentParser(add_help=False)
        net_parser.add_argument('--list', action='store_true', help='List network database')
        net_parser.add_argument('--domain', action='store_true', help='Add domain')
        net_parser.add_argument('--cidr', action='store_true', help='Add network')
        net_parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show help message')
        subparsers = parser.add_subparsers(dest='command')
        image_mode = subparsers.add_parser('image', help="Manage CB Images", parents=[parent_parser, image_parser], add_help=False)
        create_mode = subparsers.add_parser('create', help="List Nodes", parents=[parent_parser], add_help=False)
        destroy_mode = subparsers.add_parser('destroy', help="Clean Up", parents=[parent_parser], add_help=False)
        list_mode = subparsers.add_parser('list', help="Load Data", parents=[parent_parser], add_help=False)
        net_mode = subparsers.add_parser('net', help="Static Network Configuration", parents=[parent_parser, net_parser], add_help=False)
        self.parser = parser
        self.image_parser = image_mode
        self.create_parser = create_mode
        self.destroy_parser = destroy_mode
        self.list_parser = list_mode
        self.net_parser = net_mode
