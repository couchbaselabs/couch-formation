##
##

import logging
import jinja2
from lib.exceptions import fatalError


class ComponentException(fatalError):
    pass


class CloudCommon(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def process_template(block: str, parameters: dict) -> str:
        raw_template = jinja2.Template(block)
        formatted_template = raw_template.render(parameters)

        return formatted_template


class Variable(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._name = None
        self._value = None
        self._type = None
        self._description = None

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._value

    @property
    def type(self):
        return self._type

    @property
    def description(self):
        return self._description

    @name.setter
    def name(self, value):
        self._name = value

    @default.setter
    def default(self, value):
        self._value = value

    @type.setter
    def type(self, value):
        self._type = value

    @description.setter
    def description(self, value):
        self._description = value

    def variable(self):
        type_string = "string"
        value = self._value

        if not self._value or not self._name:
            raise ComponentException("attempt to instantiate unset variable")

        if type(self._value) is list:
            type_string = "list(string)"
            value_list = ','.join(f'"{s}"' for s in self._value)
            value = f"[{value_list}]"
        elif type(self._value) == bool:
            type_string = "bool"
            value = str(self._value).lower()

        block = f"""variable "{self.name}" {{
  type    = {type_string}
  default = "{value}"
}}
"""
        return block

    def template(self):
        if not self._value or not self._name or not self._type:
            raise ComponentException("attempt to instantiate unset variable")

        block = f"""variable "{self.name}" {{
  type    = {self._type}
  default = "{{{{{self._value}}}}}"
}}
"""
        return block


class Block(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)


class CloudCommonB(object):
    CB_VERSION = {
        "name": "cb_version",
        "tag": "CB_VERSION",
        "type": "string"
    }
    PKVAR_CB_VERSION = 'cb_version = "{{ CB_VERSION }}"'
    PKVAR_LINUX_TYPE = 'os_linux_type = "{{ LINUX_TYPE }}"'
    PKVAR_LINUX_RELEASE = 'os_linux_release = "{{ LINUX_RELEASE }}"'
    PKVAR_OS_IMAGE_NAME = 'os_image_name = "{{ OS_IMAGE_NAME }}"'
    PKVAR_OS_IMAGE_OWNER = 'os_image_owner = "{{ OS_IMAGE_OWNER }}"'
    PKVAR_OS_IMAGE_USER = 'os_image_user = "{{ OS_IMAGE_USER }}"'
    PKVAR_AWS_REGION = 'region_name = "{{ AWS_REGION }}"'
    PKVAR_HOST_PREP_REPO = 'host_prep_repo = "{{ HOST_PREP_REPO }}"'

    PKVAR_AZURE_RG = 'azure_resource_group = "{{ AZURE_RG }}"'
    PKVAR_IMAGE_PUBLISHER = 'os_image_publisher = "{{ OS_IMAGE_PUBLISHER }}"'
    PKVAR_IMAGE_OFFER = 'os_image_offer = "{{ OS_IMAGE_OFFER }}"'
    PKVAR_IMAGE_SKU = 'os_image_sku = "{{ OS_IMAGE_SKU }}"'
    PKVAR_LOCATION = 'azure_location = "{{ AZURE_LOCATION }}"'

    PKVAR_GCP_ACCOUNT = 'gcp_account_file = "{{ GCP_ACCOUNT_FILE }}"'
    PKVAR_IMAGE_FAMILY = 'os_image_family = "{{ OS_IMAGE_FAMILY }}"'
    PKVAR_GCP_PROJECT = 'gcp_project = "{{ GCP_PROJECT }}"'
    PKVAR_GCP_ZONE = 'gcp_zone = "{{ GCP_ZONE }}"'

    PKVAR_VSPHERE_HOSTNAME = 'vsphere_hostname = "{{ VMWARE_HOSTNAME }}"'
    PKVAR_VSPHERE_USERNAME = 'vsphere_username = "{{ VMWARE_USERNAME }}"'
    PKVAR_VSPHERE_PASSWORD = 'vsphere_password = "{{ VMWARE_PASSWORD }}"'
    PKVAR_VSPHERE_DATACENTER = 'vsphere_datacenter = "{{ VMWARE_DATACENTER }}"'
    PKVAR_VSPHERE_CLUSTER = 'vsphere_cluster = "{{ VMWARE_CLUSTER }}"'
    PKVAR_VSPHERE_DATASTORE = 'vsphere_datastore = "{{ VMWARE_DATASTORE }}"'
    PKVAR_VSPHERE_FOLDER = 'vsphere_folder = "{{ VMWARE_FOLDER }}"'
    PKVAR_VM_GUEST_OS_TYPE = 'vm_guest_os_type = "{{ VMWARE_OS_TYPE }}"'
    PKVAR_VM_CPU_CORES = 'vm_cpu_cores = "{{ VMWARE_CPU_CORES }}"'
    PKVAR_VM_MEM_SIZE = 'vm_mem_size = "{{ VMWARE_MEM_SIZE }}"'
    PKVAR_VM_DISK_SIZE = 'vm_disk_size = "{{ VMWARE_DISK_SIZE }}"'
    PKVAR_VSPHERE_NETWORK = 'vsphere_network = "{{ VMWARE_NETWORK }}"'
    PKVAR_OS_ISO_CHECKSUM = 'os_iso_checksum = "{{ OS_ISO_CHECKSUM }}"'
    PKVAR_OS_SW_URL = 'os_sw_url = "{{ OS_SW_URL }}"'
    PKVAR_BUILD_PASSWORD = 'build_password = "{{ VMWARE_BUILD_PASSWORD }}"'
    PKVAR_BUILD_PASSWORD_ENCRYPTED = 'build_password_encrypted = "{{ VMWARE_BUILD_PWD_ENCRYPTED }}"'
    PKVAR_VM_GUEST_OS_LANGUAGE = 'vm_guest_os_language = "en_US"'
    PKVAR_VM_GUEST_OS_KEYBOARD = 'vm_guest_os_keyboard = "us"'
    PKVAR_OS_TIMEZONE = 'os_timezone = "{{ OS_TIMEZONE }}"'
    PKVAR_SSH_PUBLIC_KEY = 'ssh_public_key = "{{ SSH_PUBLIC_KEY }}"'

    PACKER_HEADER = """packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}
"""
