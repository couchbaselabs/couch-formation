##
##

from datetime import datetime
from lib.exceptions import *
from lib.ask import ask
from lib.aws import aws
from lib.gcp import gcp
from lib.azure import azure
from lib.vmware import vmware


class image_manager(object):

    def __init__(self, parameters):
        self.template_file = 'linux.pkrvars.template'
        self.cloud = parameters.cloud
        self.args = parameters

    def list_images(self):
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

    def delete_images(self):
        if self.cloud == 'aws':
            self.aws_delete(image=self.args.image)
        elif self.cloud == 'gcp':
            self.gcp_delete(image=self.args.image)
        elif self.cloud == 'azure':
            self.azure_delete(image=self.args.image)
        elif self.cloud == 'vmware':
            self.vmware_delete(image=self.args.image)
        else:
            raise ImageMgmtError(f"unknown cloud {self.cloud}")

    def build(self):
        pass

    def _aws_list(self, _driver=None) -> list[dict]:
        if not _driver:
            driver = aws()
            driver.aws_init()
        else:
            driver = _driver

        image_list = driver.aws_get_ami_id(select=False)

        for n, image in enumerate(image_list):
            image_time = datetime.strptime(image['date'], '%Y-%m-%dT%H:%M:%S.000Z')
            image_list[n]['datetime'] = image_time

        sorted_list = sorted(image_list, key=lambda item: item['datetime'])

        return sorted_list

    def aws_list(self):
        inquire = ask()

        image_list = self._aws_list()
        inquire.ask_list('AMI List', image_list, list_only=True)

    def aws_delete(self, image=None):
        inquire = ask()
        driver = aws()
        driver.aws_init()

        if not image:
            image_list = self._aws_list(_driver=driver)
            selection = inquire.ask_list('AMI', image_list)
            driver.aws_remove_ami(image_list[selection]['name'])
        else:
            driver.aws_remove_ami(image)

    def _gcp_list(self, _driver=None) -> list[dict]:
        if not _driver:
            driver = gcp()
            driver.gcp_init()
        else:
            driver = _driver

        image_list = driver.gcp_get_cb_image_name(select=False)

        for n, image in enumerate(image_list):
            image_time = datetime.strptime(image['date'], '%Y-%m-%dT%H:%M:%S.%f%z')
            image_list[n]['datetime'] = image_time

        sorted_list = sorted(image_list, key=lambda item: item['datetime'])

        return sorted_list

    def gcp_list(self):
        inquire = ask()

        image_list = self._gcp_list()
        inquire.ask_list('GCP Image List', image_list, list_only=True)

    def gcp_delete(self, image=None):
        inquire = ask()
        driver = gcp()
        driver.gcp_init()

        if not image:
            image_list = self._gcp_list(_driver=driver)
            selection = inquire.ask_list('GCP Image', image_list)
            driver.gcp_delete_cb_image(image_list[selection]['name'])
        else:
            driver.gcp_delete_cb_image(image)

    def _azure_list(self, _driver=None) -> list[dict]:
        if not _driver:
            driver = azure()
            driver.azure_init()
        else:
            driver = _driver

        image_list = driver.azure_get_image_name(select=False)

        sorted_list = sorted(image_list, key=lambda item: item['name'])

        return sorted_list

    def azure_list(self):
        inquire = ask()

        image_list = self._azure_list()
        inquire.ask_list('Azure Image List', image_list, list_only=True)

    def azure_delete(self, image=None):
        inquire = ask()
        driver = azure()
        driver.azure_init()

        if not image:
            image_list = self._azure_list(_driver=driver)
            selection = inquire.ask_list('Azure Image', image_list)
            driver.azure_delete_image(image_list[selection]['name'])
        else:
            driver.azure_delete_image(image)

    def _vmware_list(self, _driver=None) -> list[dict]:
        if not _driver:
            driver = vmware()
            driver.vmware_init()
        else:
            driver = _driver

        image_list = driver.vmware_get_template(select=False)

        sorted_list = sorted(image_list, key=lambda item: item['datetime'])

        return sorted_list

    def vmware_list(self):
        inquire = ask()

        image_list = self._vmware_list()
        inquire.ask_list('Azure Image List', image_list, list_only=True)

    def vmware_delete(self, image=None):
        inquire = ask()
        driver = vmware()
        driver.vmware_init()

        if not image:
            image_list = self._vmware_list(_driver=driver)
            selection = inquire.ask_list('VM template', image_list)
            driver.vmware_delete_template(image_list[selection]['name'])
        else:
            driver.vmware_delete_template(image)
