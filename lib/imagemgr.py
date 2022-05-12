##
##

from datetime import datetime
from lib.exceptions import *
from lib.aws import aws
from lib.gcp import gcp
from lib.azure import azure
from lib.vmware import vmware


class image_manager(object):

    def __init__(self, parameters):
        self.template_file = 'linux.pkrvars.template'
        self.cloud = parameters.cloud

    def list(self):
        if self.cloud == 'aws':
            self.aws_list()
        elif self.cloud == 'gcp':
            self.gcp_list()
        elif self.cloud == 'azure':
            self.azure_list()
        elif self.cloud == 'vmware':
            self.vmware_list()
        else:
            raise ImageMgmtError(f"unknown cloud {self.cloud}")

    def build(self):
        pass

    def aws_list(self):
        driver = aws()

        region = driver.aws_get_region()
        image_list = driver.aws_get_ami_id(region, select=False)

        for n, image in enumerate(image_list):
            image_time = datetime.strptime(image['date'], '%Y-%m-%dT%H:%M:%S.000Z')
            image_list[n]['datetime'] = image_time

        sorted_list = sorted(image_list, key=lambda item: item['datetime'])

        for n, image in enumerate(sorted_list):
            print(f" {n+1:02d}) {image['arch'].ljust(6)} {image['name']} {image['description'].ljust(60)} {image['datetime'].strftime('%D %r')}")

    def gcp_list(self):
        driver = gcp()

        account_file = driver.gcp_get_account_file()
        gcp_project = driver.gcp_get_project_id(account_file)
        image_list = driver.gcp_get_cb_image_name(account_file, gcp_project, select=False)

        for n, image in enumerate(image_list):
            image_time = datetime.strptime(image['date'], '%Y-%m-%dT%H:%M:%S.%f%z')
            image_list[n]['datetime'] = image_time

        sorted_list = sorted(image_list, key=lambda item: item['datetime'])

        for n, image in enumerate(sorted_list):
            print(f" {n+1:02d}) {image['name'].ljust(64)} {image['datetime'].strftime('%D %r')}")

    def azure_list(self):
        driver = azure()

        subscription_id = driver.azure_get_subscription_id()
        resource_group = driver.azure_get_resource_group(subscription_id)
        image_list = driver.azure_get_image_name(subscription_id, resource_group, select=False)

        sorted_list = sorted(image_list, key=lambda item: item['name'])

        for n, image in enumerate(sorted_list):
            print(f" {n+1:02d}) {image['name']}")

    def vmware_list(self):
        driver = vmware()

        driver.vmware_init()
        image_list = driver.vmware_get_template(select=False)

        sorted_list = sorted(image_list, key=lambda item: item['name'])

        for n, image in enumerate(sorted_list):
            print(f" {n + 1:02d}) {image['name']}")
