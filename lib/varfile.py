##
##

import json
from lib.location import location
from lib.ask import ask
from lib.exceptions import *


class varfile(object):
    VARIABLES = [
        ('LINUX_RELEASE', 'os_linux_release', 'get_linux_release', None),
        ('LINUX_TYPE', 'os_linux_type', 'get_linux_type', None),
        ('OS_IMAGE_OWNER', 'os_image_owner', 'get_image_owner', None),
        ('OS_IMAGE_USER', 'os_image_user', 'get_image_user', None),
        ('OS_IMAGE_NAME', 'os_image_name', 'get_image_name', None),
        ('OS_IMAGE_FAMILY', 'os_image_family', 'get_image_family', None),
        ('OS_IMAGE_PUBLISHER', 'os_image_publisher', 'get_image_publisher', None),
        ('OS_IMAGE_SKU', 'os_image_sku', 'get_image_sku', None),
        ('OS_IMAGE_OFFER', 'os_image_offer', 'get_image_offer', None),
    ]

    def __init__(self):
        self._global_vars: dict
        self._aws_packer_vars: dict
        self._aws_tf_vars: dict
        self._gcp_packer_vars: dict
        self._gcp_tf_vars: dict
        self._azure_packer_vars: dict
        self._azure_tf_vars: dict
        self._vmware_packer_vars: dict
        self._vmware_tf_vars: dict
        self.active_packer_vars = None
        self.active_tf_vars = None
        self.os_type = 'linux'
        self.os_name = None
        self.os_ver = None
        self.cloud = None

        self.lc = location()

        self._global_vars = self.get_var_data(self.lc.package_dir + '/globals.json')

        self._aws_packer_vars = self.get_var_data(self.lc.aws_packer + '/locals.json')
        self._aws_tf_vars = self.get_var_data(self.lc.aws_tf + '/locals.json')

        self._gcp_packer_vars = self.get_var_data(self.lc.gcp_packer + '/locals.json')
        self._gcp_tf_vars = self.get_var_data(self.lc.gcp_tf + '/locals.json')

        self._azure_packer_vars = self.get_var_data(self.lc.azure_packer + '/locals.json')
        self._azure_tf_vars = self.get_var_data(self.lc.azure_tf + '/locals.json')

        self._vmware_packer_vars = self.get_var_data(self.lc.vmware_packer + '/locals.json')
        self._vmware_tf_vars = self.get_var_data(self.lc.vmware_tf + '/locals.json')

    def get_var_data(self, file: str) -> dict:
        try:
            with open(file, 'r') as inputFile:
                var_text = inputFile.read()
                var_json = json.loads(var_text)
            inputFile.close()
            return var_json
        except Exception as err:
            raise VarFileError(f"Can not open var file {file}: {err}")

    def set_os_name(self, name: str):
        self.os_name = name

    def set_os_ver(self, release: str):
        self.os_ver = release

    def set_cloud(self, cloud: str):
        self.cloud = cloud

        if self.cloud == 'aws':
            self.active_packer_vars = self.aws_packer_vars
            self.active_tf_vars = self.aws_tf_vars
        elif self.cloud == 'gcp':
            self.active_packer_vars = self.gcp_packer_vars
            self.active_tf_vars = self.gcp_tf_vars
        elif self.cloud == 'azure':
            self.active_packer_vars = self.azure_packer_vars
            self.active_tf_vars = self.azure_tf_vars
        elif self.cloud == 'vmware':
            self.active_packer_vars = self.vmware_packer_vars
            self.active_tf_vars = self.vmware_tf_vars
        else:
            raise VarFileError(f"unknown cloud {self.cloud}")

    def aws_get_default(self, key: str) -> str:
        try:
            return self.aws_tf_vars['defaults'][key]
        except KeyError:
            raise VarFileError(f"value {key} not in aws defaults")

    def gcp_get_default(self, key: str) -> str:
        try:
            return self.gcp_tf_vars['defaults'][key]
        except KeyError:
            raise VarFileError(f"value {key} not in gcp defaults")

    def azure_get_default(self, key: str) -> str:
        try:
            return self.azure_tf_vars['defaults'][key]
        except KeyError:
            raise VarFileError(f"value {key} not in azure defaults")

    def vmware_get_default(self, key: str) -> str:
        try:
            return self.vmware_tf_vars['defaults'][key]
        except KeyError:
            raise VarFileError(f"value {key} not in vmware defaults")

    def get_all_os(self):
        os_list = []
        try:
            for key in self.active_packer_vars[self.os_type]:
                os_list.append(key)
            return os_list
        except KeyError:
            raise VarFileError(f"can not get {self.cloud} OS list of type {self.os_type}")

    def get_all_version(self) -> list[str]:
        release_list = []
        try:
            for i in range(len(self.active_packer_vars[self.os_type][self.os_name])):
                release_list.append(self.active_packer_vars[self.os_type][self.os_name][i]['version'])
            return release_list
        except KeyError:
            raise VarFileError(f"can not get {self.cloud} OS releases for {self.os_name}")

    def get_linux_release(self, default=None):
        inquire = ask()

        if self.os_ver:
            return self.os_ver

        version_list = self.get_all_version()
        selection = inquire.ask_list('Select Version', version_list, default=default)
        self.os_ver = version_list[selection]
        self.set_os_ver(self.os_ver)

        return self.os_ver

    def get_linux_type(self, default=None):
        inquire = ask()

        if self.os_name:
            return self.os_name

        distro_list = self.get_all_os()
        selection = inquire.ask_list('Select Linux Distribution', distro_list, default=default)
        self.os_name = distro_list[selection]
        self.set_os_name(self.os_name)

        return self.os_name

    def get_image_owner(self):
        return self.get_os_var('owner')

    def get_image_user(self):
        return self.get_os_var('user')

    def get_image_name(self):
        return self.get_os_var('image')

    def get_image_family(self):
        return self.get_os_var('family')

    def get_image_publisher(self):
        return self.get_os_var('publisher')

    def get_image_offer(self):
        return self.get_os_var('offer')

    def get_image_sku(self):
        return self.get_os_var('sku')

    def get_var_file(self):
        return self.get_os_var('vars')

    def get_hcl_file(self):
        return self.get_os_var('hcl')

    def get_os_var(self, key: str) -> str:
        try:
            for i in range(len(self.active_packer_vars[self.os_type][self.os_name])):
                if self.active_packer_vars[self.os_type][self.os_name][i]['version'] == self.os_ver:
                    return self.active_packer_vars[self.os_type][self.os_name][i][key]
        except KeyError:
            raise VarFileError(f"value {key} not in {self.cloud} packer variables for {self.os_name} {self.os_type}")

    def aws_get_os_var(self, key: str) -> str:
        try:
            for i in range(len(self.aws_packer_vars[self.os_type][self.os_name])):
                if self.aws_packer_vars[self.os_type][self.os_name][i]['version'] == self.os_ver:
                    return self.aws_packer_vars[self.os_type][self.os_name][i][key]
        except KeyError:
            raise VarFileError(f"value {key} not in aws packer variables for {self.os_name} {self.os_type}")

    def gcp_get_os_var(self, key: str) -> str:
        try:
            for i in range(len(self.gcp_packer_vars[self.os_type][self.os_name])):
                if self.gcp_packer_vars[self.os_type][self.os_name][i]['version'] == self.os_ver:
                    return self.gcp_packer_vars[self.os_type][self.os_name][i][key]
        except KeyError:
            raise VarFileError(f"value {key} not in gcp packer variables for {self.os_name} {self.os_type}")

    def azure_get_os_var(self, key: str) -> str:
        try:
            for i in range(len(self.azure_packer_vars[self.os_type][self.os_name])):
                if self.azure_packer_vars[self.os_type][self.os_name][i]['version'] == self.os_ver:
                    return self.azure_packer_vars[self.os_type][self.os_name][i][key]
        except KeyError:
            raise VarFileError(f"value {key} not in azure packer variables for {self.os_name} {self.os_type}")

    def vmware_get_os_var(self, key: str) -> str:
        try:
            for i in range(len(self.vmware_packer_vars[self.os_type][self.os_name])):
                if self.vmware_packer_vars[self.os_type][self.os_name][i]['version'] == self.os_ver:
                    return self.vmware_packer_vars[self.os_type][self.os_name][i][key]
        except KeyError:
            raise VarFileError(f"value {key} not in vmware packer variables for {self.os_name} {self.os_type}")

    @property
    def global_vars(self) -> dict:
        return self._global_vars

    @property
    def aws_packer_vars(self) -> dict:
        return self._aws_packer_vars

    @property
    def aws_tf_vars(self) -> dict:
        return self._aws_tf_vars

    @property
    def gcp_packer_vars(self) -> dict:
        return self._gcp_packer_vars

    @property
    def gcp_tf_vars(self) -> dict:
        return self._gcp_tf_vars

    @property
    def azure_packer_vars(self) -> dict:
        return self._azure_packer_vars

    @property
    def azure_tf_vars(self) -> dict:
        return self._azure_tf_vars

    @property
    def vmware_packer_vars(self) -> dict:
        return self._vmware_packer_vars

    @property
    def vmware_tf_vars(self) -> dict:
        return self._vmware_tf_vars
