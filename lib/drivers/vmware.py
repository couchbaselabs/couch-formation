##
##

import logging
import os
import json
from pyVim.connect import SmartConnect
from pyVmomi import vim
from lib.exceptions import VMwareDriverError
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = False
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = False

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.getLogger("pyvmomi").setLevel(logging.ERROR)
        self.vmware_hostname = None
        self.vmware_username = None
        self.vmware_password = None
        self.vmware_datacenter = None
        self.vmware_dc_folder = None
        self.vmware_network_folder = None
        self.vmware_host_folder = None

        self.read_config()

    def read_config(self):
        config_directory = os.environ['HOME'] + '/.config'
        auth_directory = config_directory + '/imagemgr'
        config_file = auth_directory + '/vmware_auth.json'

        FileManager().create_dir(auth_directory)

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as cfgFile:
                    try:
                        cfg_data = json.load(cfgFile)
                    except ValueError as err:
                        raise VMwareDriverError(f"config file {config_file} format error: {err}")
                    try:
                        self.vmware_hostname = cfg_data['hostname']
                        self.vmware_username = cfg_data['username']
                        self.vmware_datacenter = cfg_data['datacenter']
                        self.vmware_get_password()

                        try:
                            self.vmware_get_datacenter()
                        except Exception as err:
                            raise VMwareDriverError(f"vmware init: error: {err}")

                        return True
                    except KeyError as err:
                        raise VMwareDriverError(f"config file {config_file} syntax error: {err}")
            except OSError as err:
                raise VMwareDriverError(f"can not open config file {config_file}: {err}")
        else:
            self.vmware_get_hostname()
            self.vmware_get_username()
            self.vmware_get_password()

            try:
                self.vmware_get_datacenter()
            except Exception as err:
                raise VMwareDriverError(f"vmware init: error: {err}")

            cfg_data = {
                'hostname': self.vmware_hostname,
                'username': self.vmware_username,
                'datacenter': self.vmware_datacenter
            }

            try:
                with open(config_file, 'w') as cfgFile:
                    json.dump(cfg_data, cfgFile, indent=2)
                    cfgFile.write("\n")
                    cfgFile.close()
            except OSError as err:
                raise VMwareDriverError(f"can not write config file {config_file}: {err}")

            return True

    def vmware_get_hostname(self) -> str:
        self.vmware_hostname = Inquire().ask_text("vSphere Host Name")
        return self.vmware_hostname

    def vmware_get_username(self) -> str:
        self.vmware_username = Inquire().ask_text("vSphere Admin User")
        return self.vmware_username

    def vmware_get_password(self) -> str:
        self.vmware_password = Inquire().ask_pass("vSphere Admin Password")
        return self.vmware_password

    def vmware_get_datacenter(self) -> str:
        try:
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            datacenter = []
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)

            if not self.vmware_datacenter:
                for c in container.view:
                    datacenter.append(c.name)
                selection = Inquire().ask_list('Select datacenter', datacenter)
                self.vmware_datacenter = datacenter[selection]

            for c in container.view:
                if c.name == self.vmware_datacenter:
                    self.vmware_dc_folder = c
                    self.vmware_network_folder = c.networkFolder
                    self.vmware_host_folder = c.hostFolder
            container.Destroy()
            return self.vmware_datacenter
        except Exception as err:
            raise VMwareDriverError(f"can not access vSphere: {err}")


class Network(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Subnet(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class SecurityGroup(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class MachineType(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Instance(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class SSHKey(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)


class Image(CloudBase):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
