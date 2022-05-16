##
##

import json
from lib.location import location
from lib.exceptions import *


class varfile(object):

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
        self.os_type = 'linux'
        self.os_name = None
        self.os_ver = None

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

    def aws_get_all_os(self):
        os_list = []
        try:
            for key in self.aws_packer_vars[self.os_type]:
                os_list.append(key)
            return os_list
        except KeyError:
            raise VarFileError(f"can not get aws OS list of type {self.os_type}")

    def gcp_get_all_os(self):
        try:
            return self.gcp_packer_vars[self.os_type].keys()
        except KeyError:
            raise VarFileError(f"can not get gcp OS list of type {self.os_type}")

    def azure_get_all_os(self):
        try:
            return self.azure_packer_vars[self.os_type].keys()
        except KeyError:
            raise VarFileError(f"can not get azure OS list of type {self.os_type}")

    def vmware_get_all_os(self):
        try:
            return self.vmware_packer_vars[self.os_type].keys()
        except KeyError:
            raise VarFileError(f"can not get vmware OS list of type {self.os_type}")

    def aws_get_os_releases(self) -> list[str]:
        release_list = []
        try:
            for i in range(len(self.aws_packer_vars[self.os_type][self.os_name])):
                release_list.append(self.aws_packer_vars[self.os_type][self.os_name][i]['version'])
            return release_list
        except KeyError:
            raise VarFileError(f"can not get aws OS releases for {self.os_name}")

    def gcp_get_os_releases(self) -> list[str]:
        release_list = []
        try:
            for i in range(len(self.gcp_packer_vars[self.os_type][self.os_name])):
                release_list.append(self.gcp_packer_vars[self.os_type][self.os_name][i]['version'])
            return release_list
        except KeyError:
            raise VarFileError(f"can not get aws OS releases for {self.os_name}")

    def azure_get_os_releases(self) -> list[str]:
        release_list = []
        try:
            for i in range(len(self.azure_packer_vars[self.os_type][self.os_name])):
                release_list.append(self.azure_packer_vars[self.os_type][self.os_name][i]['version'])
            return release_list
        except KeyError:
            raise VarFileError(f"can not get aws OS releases for {self.os_name}")

    def vmware_get_os_releases(self) -> list[str]:
        release_list = []
        try:
            for i in range(len(self.vmware_packer_vars[self.os_type][self.os_name])):
                release_list.append(self.vmware_packer_vars[self.os_type][self.os_name][i]['version'])
            return release_list
        except KeyError:
            raise VarFileError(f"can not get aws OS releases for {self.os_name}")

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
