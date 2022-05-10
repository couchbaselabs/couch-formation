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

    def aws_get_default(self, key: str) -> str:
        try:
            return self.aws_tf_vars['defaults'][key]
        except KeyError:
            raise VarFileError(f"value {key} not in aws defaults")

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
