##
##

from lib.exceptions import *

class location(object):

    def __init__(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        self._package_dir = os.path.dirname(current_dir)
        self.cloud = None
        self._packer_dir = None
        self._tf_dir = None

    def set_cloud(self, cloud: str):
        self.cloud = cloud

        if self.cloud == 'aws':
            self._packer_dir = self.aws_packer
            self._tf_dir = self.aws_tf
        elif self.cloud == 'gcp':
            self._packer_dir = self.gcp_packer
            self._tf_dir = self.gcp_tf
        elif self.cloud == 'azure':
            self._packer_dir = self.azure_packer
            self._tf_dir = self.azure_tf
        elif self.cloud == 'vmware':
            self._packer_dir = self.vmware_packer
            self._tf_dir = self.vmware_tf
        else:
            raise VarFileError(f"unknown cloud {self.cloud}")

    def get_home(self, _location: str) -> str:
        home_dir = self._package_dir + '/' + _location
        if not os.path.exists(home_dir):
            raise DirectoryStructureError(f"Expecting {_location} root at {home_dir}")
        return home_dir

    def get_packer(self, _location: str) -> str:
        packer_dir = self._package_dir + '/' + _location + '/packer'
        if not os.path.exists(packer_dir):
            raise DirectoryStructureError(f"Expecting {_location} packer dir at {packer_dir}")
        return packer_dir

    def get_tf(self, _location: str) -> str:
        tf_dir = self._package_dir + '/' + _location + '/terraform'
        if not os.path.exists(tf_dir):
            raise DirectoryStructureError(f"Expecting {_location} terraform dir at {tf_dir}")
        return tf_dir

    @property
    def packer_dir(self):
        return self._packer_dir

    @property
    def tf_dir(self):
        return self._tf_dir

    @property
    def package_dir(self):
        return self._package_dir

    @property
    def aws_home(self):
        return self.get_home('aws')

    @property
    def aws_packer(self):
        return self.get_packer('aws')

    @property
    def aws_tf(self):
        return self.get_tf('aws')

    @property
    def gcp_home(self):
        return self.get_home('gcp')

    @property
    def gcp_packer(self):
        return self.get_packer('gcp')

    @property
    def gcp_tf(self):
        return self.get_tf('gcp')

    @property
    def azure_home(self):
        return self.get_home('azure')

    @property
    def azure_packer(self):
        return self.get_packer('azure')

    @property
    def azure_tf(self):
        return self.get_tf('azure')

    @property
    def vmware_home(self):
        return self.get_home('vmware')

    @property
    def vmware_packer(self):
        return self.get_packer('vmware')

    @property
    def vmware_tf(self):
        return self.get_tf('vmware')
