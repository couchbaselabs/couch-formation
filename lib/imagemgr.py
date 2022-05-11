##
##

from lib.exceptions import *
from lib.aws import aws


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
            print(f" {n+1}) {image['name']}")

    def gcp_list(self):
        pass

    def azure_list(self):
        pass

    def vmware_list(self):
        pass
