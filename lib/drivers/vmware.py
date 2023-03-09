##
##

import logging
import os
import json
import base64
import random
import string
import secrets
from typing import Union
from pyVim.connect import SmartConnect
from pyVmomi import vim
from passlib.hash import sha512_crypt
from lib.exceptions import VMwareDriverError
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire


class CloudBase(object):
    VERSION = '3.0.0'
    PUBLIC_CLOUD = False
    SAAS_CLOUD = False
    NETWORK_SUPER_NET = False
    VMWARE_DISK_SIZE = 100000
    VMWARE_DISK_TYPE = "pvscsi"
    VMWARE_MACHINE_TYPES = [
        {
            "name": "standard-2-8",
            "cpu": 2,
            "memory": 8192
        },
        {
            "name": "standard-4-16",
            "cpu": 4,
            "memory": 16384
        },
        {
            "name": "standard-8-32",
            "cpu": 8,
            "memory": 32768
        },
        {
            "name": "standard-16-64",
            "cpu": 16,
            "memory": 65536
        },
        {
            "name": "standard-32-128",
            "cpu": 32,
            "memory": 131072
        },
        {
            "name": "standard-48-192",
            "cpu": 48,
            "memory": 196608
        },
        {
            "name": "standard-64-256",
            "cpu": 64,
            "memory": 262144
        },
        {
            "name": "standard-80-320",
            "cpu": 80,
            "memory": 327680
        },
        {
            "name": "high-mem-2-16",
            "cpu": 2,
            "memory": 16384
        },
        {
            "name": "high-mem-4-32",
            "cpu": 4,
            "memory": 32768
        },
        {
            "name": "high-mem-8-64",
            "cpu": 8,
            "memory": 65536
        },
        {
            "name": "high-mem-16-128",
            "cpu": 16,
            "memory": 131072
        },
        {
            "name": "high-mem-32-256",
            "cpu": 32,
            "memory": 262144
        },
        {
            "name": "high-mem-48-384",
            "cpu": 48,
            "memory": 393216
        },
        {
            "name": "high-mem-64-512",
            "cpu": 64,
            "memory": 524288
        },
        {
            "name": "high-mem-80-640",
            "cpu": 80,
            "memory": 655360
        },
        {
            "name": "high-cpu-2-2",
            "cpu": 2,
            "memory": 2048
        },
        {
            "name": "high-cpu-4-4",
            "cpu": 4,
            "memory": 4096
        },
        {
            "name": "high-cpu-8-8",
            "cpu": 8,
            "memory": 8192
        },
        {
            "name": "high-cpu-16-16",
            "cpu": 16,
            "memory": 16384
        },
        {
            "name": "high-cpu-32-32",
            "cpu": 32,
            "memory": 32768
        },
        {
            "name": "high-cpu-48-48",
            "cpu": 48,
            "memory": 49152
        },
        {
            "name": "high-cpu-64-64",
            "cpu": 64,
            "memory": 65536
        },
        {
            "name": "high-cpu-80-80",
            "cpu": 80,
            "memory": 81920
        }
    ]

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
        self.vmware_network = None
        self.vmware_dvs = None
        self.vmware_cluster = None
        self.vmware_template_folder = None
        self.vmware_cluster_folder = None
        self.vmware_create_folder = False
        self.vmware_datastore = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_templates = []
        self.vmware_hosts = []

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
                        self.vmware_password = base64.b64decode(cfg_data['password'].encode('utf-8')).decode('utf-8')

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
                'datacenter': self.vmware_datacenter,
                'password': base64.b64encode(self.vmware_password.encode('utf-8')).decode('utf-8')
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
                selection = Inquire().ask_list_basic('Select datacenter', datacenter)
                self.vmware_datacenter = selection

            for c in container.view:
                if c.name == self.vmware_datacenter:
                    self.vmware_dc_folder = c
                    self.vmware_network_folder = c.networkFolder
                    self.vmware_host_folder = c.hostFolder
            container.Destroy()
            return self.vmware_datacenter
        except Exception as err:
            raise VMwareDriverError(f"can not access vSphere: {err}")

    def vmware_get_dvs_network(self) -> str:
        pg_list = []

        try:
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(self.vmware_network_folder, [vim.dvs.DistributedVirtualPortgroup], True)
            for managed_object_ref in container.view:
                pg_list.append(managed_object_ref.name)
            container.Destroy()
            pg_list = sorted(set(pg_list))
            selection = Inquire().ask_list_basic('Select port group', pg_list)
            self.vmware_network = selection
            return self.vmware_network
        except Exception as err:
            raise VMwareDriverError(f"can not get port group: {err}")

    def vmware_get_dvs_switch(self) -> str:
        dvs_list = []

        try:
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(self.vmware_network_folder,
                                                                [vim.dvs.VmwareDistributedVirtualSwitch],
                                                                True)
            for managed_object_ref in container.view:
                dvs_list.append(managed_object_ref.name)
            container.Destroy()
            selection = Inquire().ask_list_basic('Select distributed switch', dvs_list)
            self.vmware_dvs = selection
            return self.vmware_dvs
        except Exception as err:
            raise VMwareDriverError(f"can not get distributed switch: {err}")

    def vmware_get_cluster(self) -> str:
        try:
            clusters = []
            for c in self.vmware_host_folder.childEntity:
                if isinstance(c, vim.ClusterComputeResource):
                    clusters.append(c.name)
            selection = Inquire().ask_list_basic('Select cluster', clusters)
            self.vmware_cluster = selection
            return self.vmware_cluster
        except Exception as err:
            raise VMwareDriverError(f"can not get cluster: {err}")

    def vmware_get_hosts(self, cluster: str) -> list[dict]:
        try:
            hosts = []
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.ComputeResource], True)
            for managed_object_ref in container.view:
                if managed_object_ref.name == cluster:
                    for host in managed_object_ref.host:
                        host_struct = {'name': host.name, 'hostname': host.config.network.dnsConfig.hostName}
                        hosts.append(host_struct)
            container.Destroy()
            self.vmware_hosts = hosts
            return self.vmware_hosts
        except Exception as err:
            raise VMwareDriverError(f"can not get hosts: {err}")

    def _create_folder(self, folder_name: str):
        for folder in self.vmware_dc_folder.vmFolder.childEntity:
            if folder.name == folder_name:
                self.logger.info(f"Folder {folder_name} already exists.")
                return

        self.logger.info(f"Folder {folder_name} does not exist.")
        self.logger.info(f"Creating folder {folder_name}")
        try:
            self.vmware_dc_folder.vmFolder.CreateFolder(folder_name)
        except Exception as err:
            raise VMwareDriverError(f"can not create folder {folder_name}: {err}")

    def vmware_get_cluster_folder(self) -> str:
        selection = Inquire().ask_text('Cluster Folder', default="couchbase")
        self.vmware_cluster_folder = selection

        if self.vmware_create_folder:
            self._create_folder(self.vmware_cluster_folder)

        return self.vmware_cluster_folder

    def vmware_get_template_folder(self) -> str:
        selection = Inquire().ask_text('Template Folder', default="couchbase-templates")
        self.vmware_template_folder = selection

        if self.vmware_create_folder:
            self._create_folder(self.vmware_template_folder)

        return self.vmware_template_folder

    def vmware_get_datastore(self) -> str:
        try:
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            datastore_list = []
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
            esxi_hosts = container.view
            for esxi_host in esxi_hosts:
                storage_system = esxi_host.configManager.storageSystem
                host_file_sys_vol_mount_info = storage_system.fileSystemVolumeInfo.mountInfo
                for host_mount_info in host_file_sys_vol_mount_info:
                    if host_mount_info.volume.type == 'VFFS' or host_mount_info.volume.type == 'OTHER':
                        continue
                    datastore_struct = {'name': host_mount_info.volume.name,
                                        'type': host_mount_info.volume.type}
                    datastore_list.append(datastore_struct)
            selection = Inquire().ask_list_dict('Select datastore', datastore_list)
            container.Destroy()
            self.vmware_datastore = selection['name']
            return self.vmware_datastore
        except Exception as err:
            raise VMwareDriverError(f"can not get datastore: {err}")

    def vmware_get_build_password(self) -> str:
        self.vmware_build_password = secrets.token_urlsafe(12)
        return self.vmware_build_password

    def vmware_get_build_pwd_encrypted(self, build_password: str) -> str:
        self.vmware_build_pwd_encrypted = sha512_crypt.using(
            salt=''.join([random.choice(string.ascii_letters + string.digits) for _ in range(16)]), rounds=5000)\
            .hash(build_password)
        return self.vmware_build_pwd_encrypted

    @staticmethod
    def check_image_name_format(name):
        try:
            name_fields = name.split('-')
            if name_fields[2].startswith("couchbase"):
                return True
        except IndexError:
            pass
        return False

    def vmware_get_templates(self) -> Union[dict, list[dict]]:
        templates = []
        try:
            si = SmartConnect(host=self.vmware_hostname,
                              user=self.vmware_username,
                              pwd=self.vmware_password,
                              port=443,
                              disableSslCertValidation=True)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            for managed_object_ref in container.view:
                if managed_object_ref.config.template:
                    image_block = {'name': managed_object_ref.name, 'datetime': managed_object_ref.config.createDate}
                    if self.check_image_name_format(image_block['name']):
                        image_block['type'] = image_block.get('name').split('-')[0]
                        image_block['release'] = image_block.get('name').split('-')[1]
                        templates.append(image_block)
            container.Destroy()

            self.vmware_templates = templates
            return self.vmware_templates
        except Exception as err:
            raise VMwareDriverError(f"can not get template: {err}")


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

    @staticmethod
    def details(machine_type: str) -> Union[dict, None]:
        for machine in CloudBase.VMWARE_MACHINE_TYPES:
            if machine['name'] == machine_type:
                return {'name': machine['name'],
                        'cpu': machine['cpu'],
                        'memory': machine['memory'],
                        'disk': CloudBase.VMWARE_DISK_SIZE}


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
