##
##

import logging
from passlib.hash import sha512_crypt
import random
import string
import os
import json
from typing import Union
from pyVim.connect import SmartConnectNoSSL
from pyVmomi import vim, vmodl
from lib.varfile import varfile
from lib.exceptions import VMwareDriverError
from lib.ask import ask
from lib.toolbox import toolbox
from lib.prereq import prereq


class vmware(object):
    TEMPLATE = True
    VARIABLES = [
        ('VMWARE_BUILD_PASSWORD', 'build_password', 'vmware_get_build_password', None),
        ('VMWARE_BUILD_PWD_ENCRYPTED', 'build_password_encrypted', 'vmware_get_build_pwd_encrypted', None),
        ('VMWARE_CLUSTER', 'vsphere_cluster', 'vmware_get_cluster', None),
        ('VMWARE_CPU_CORES', 'vm_cpu_cores', 'vmware_get_cpucores', None),
        ('VMWARE_DATACENTER', 'vsphere_datacenter', 'vmware_get_datacenter', None),
        ('VMWARE_DATASTORE', 'vsphere_datastore', 'vmware_get_datastore', None),
        ('VMWARE_DISK_SIZE', 'vm_disk_size', 'vmware_get_disksize', None),
        ('VMWARE_DVS', 'vsphere_dvs_switch', 'vmware_get_dvs_switch', None),
        ('VMWARE_FOLDER', 'vsphere_folder', 'vmware_get_folder', None),
        ('VMWARE_HOSTNAME', 'vsphere_server', 'vmware_get_hostname', None),
        ('VMWARE_MEM_SIZE', 'vm_mem_size', 'vmware_get_memsize', None),
        ('VMWARE_NETWORK', 'vsphere_network', 'vmware_get_dvs_network', None),
        ('VMWARE_PASSWORD', 'vsphere_password', 'vmware_get_password', None),
        ('VMWARE_TEMPLATE', 'vsphere_template', 'vmware_get_template', None),
        ('VMWARE_USERNAME', 'vsphere_user', 'vmware_get_username', None),
    ]
    PREREQUISITES = {
        'vmware_get_build_pwd_encrypted': [
            'vmware_get_build_password'
        ]
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vf = varfile()
        self.vmware_hostname = None
        self.vmware_username = None
        self.vmware_password = None
        self.vmware_datacenter = None
        self.vmware_dc_folder = None
        self.vmware_network_folder = None
        self.vmware_host_folder = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_create_folder = False
        self.cb_cluster_name = None
        self.vmware_cluster = None
        self.vmware_datastore = None
        self.vmware_folder = None
        self.vmware_cpucores = None
        self.vmware_memsize = None
        self.vmware_disksize = None
        self.vmware_network = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_template = None
        self.vmware_dvs = None

    def vmware_init(self, create_folder=False):
        tb = toolbox()
        config_directory = os.environ['HOME'] + '/.config'
        auth_directory = config_directory + '/imagemgr'
        config_file = auth_directory + '/vmware_auth.json'

        if create_folder:
            self.vmware_create_folder = True

        tb.create_dir(auth_directory)

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

            cfg_data = {}
            cfg_data['hostname'] = self.vmware_hostname
            cfg_data['username'] = self.vmware_username
            cfg_data['datacenter'] = self.vmware_datacenter

            try:
                with open(config_file, 'w') as cfgFile:
                    json.dump(cfg_data, cfgFile, indent=2)
                    cfgFile.write("\n")
                    cfgFile.close()
            except OSError as err:
                raise VMwareDriverError(f"can not write config file {config_file}: {err}")

            return True

    def vmware_set_cluster_name(self, name: str):
        self.cb_cluster_name = name

    def vmware_get_template(self, select=True, default=None, write=None) -> Union[dict, list[dict]]:
        inquire = ask()
        tb = toolbox()

        if write:
            self.vmware_template = write
            return self.vmware_template

        if self.vmware_template:
            return self.vmware_template

        templates = []
        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            for managed_object_ref in container.view:
                if managed_object_ref.config.template:
                    image_block = {}
                    image_block['name'] = managed_object_ref.name
                    image_block['datetime'] = managed_object_ref.config.createDate
                    if tb.check_image_name_format(image_block['name']):
                        image_block['type'] = tb.get_linux_type_from_image_name(image_block['name'])
                        image_block['release'] = tb.get_linux_release_from_image_name(image_block['name'])
                        templates.append(image_block)
            container.Destroy()
            if select:
                selection = inquire.ask_list('Select template', templates, default=default)
                self.vmware_template = templates[selection]
            else:
                self.vmware_template = templates

            return self.vmware_template
        except Exception as err:
            raise VMwareDriverError(f"can not get template: {err}")

    @prereq(requirements=('vmware_get_template',))
    def get_image(self):
        return self.vmware_template

    def vmware_delete_template(self, name: str):
        inquire = ask()

        if inquire.ask_yn(f"Delete template {name}", default=True):
            try:
                si = SmartConnectNoSSL(host=self.vmware_hostname,
                                       user=self.vmware_username,
                                       pwd=self.vmware_password,
                                       port=443)
                content = si.RetrieveContent()
                container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                for managed_object_ref in container.view:
                    if managed_object_ref.config.template:
                        if managed_object_ref.name == name:
                            task = managed_object_ref.Destroy_Task()
            except Exception as err:
                raise VMwareDriverError(f"can not delete template: {err}")

    def vmware_get_build_password(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_build_password = write
            return self.vmware_build_password

        if self.vmware_build_password:
            return self.vmware_build_password

        selection = inquire.ask_pass("Build password", default=default)
        self.vmware_build_password = selection

        return self.vmware_build_password

    @prereq(requirements=('vmware_get_build_password',))
    def vmware_get_build_pwd_encrypted(self) -> str:
        if self.vmware_build_pwd_encrypted:
            return self.vmware_build_pwd_encrypted

        self.vmware_build_pwd_encrypted = sha512_crypt.using(salt=''.join([random.choice(string.ascii_letters + string.digits) for _ in range(16)]), rounds=5000).hash(
            self.vmware_build_password)
        return self.vmware_build_pwd_encrypted

    def vmware_get_dvs_network(self, default=None, write=None) -> str:
        inquire = ask()
        pgList = []

        if write:
            self.vmware_network = write
            return self.vmware_network

        if self.vmware_network:
            return self.vmware_network

        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(self.vmware_network_folder, [vim.dvs.DistributedVirtualPortgroup], True)
            for managed_object_ref in container.view:
                pgList.append(managed_object_ref.name)
            container.Destroy()
            pgList = sorted(set(pgList))
            selection = inquire.ask_list('Select port group', pgList, default=default)
            self.vmware_network = pgList[selection]
            return self.vmware_network
        except Exception as err:
            raise VMwareDriverError(f"can not get port group: {err}")

    def vmware_get_dvs_switch(self, default=None, write=None) -> str:
        inquire = ask()
        dvsList = []

        if write:
            self.vmware_dvs = write
            return self.vmware_dvs

        if self.vmware_dvs:
            return self.vmware_dvs

        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            container = content.viewManager.CreateContainerView(self.vmware_network_folder,
                                                                [vim.dvs.VmwareDistributedVirtualSwitch],
                                                                True)
            for managed_object_ref in container.view:
                dvsList.append(managed_object_ref.name)
            container.Destroy()
            selection = inquire.ask_list('Select distributed switch', dvsList, default=default)
            self.vmware_dvs = dvsList[selection]
            return self.vmware_dvs
        except Exception as err:
            raise VMwareDriverError(f"can not get distributed switch: {err}")

    def vmware_get_disksize(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_disksize = write
            return self.vmware_disksize

        if self.vmware_disksize:
            return self.vmware_disksize

        default_selection = self.vf.vmware_get_default('vm_disk_size')
        self.logger.info("Default disk size is %s" % default_selection)
        selection = inquire.ask_text('Disk size', recommendation=default_selection, default=default)
        self.vmware_disksize = selection
        return self.vmware_disksize

    def vmware_get_memsize(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_memsize = write
            return self.vmware_memsize

        if self.vmware_memsize:
            return self.vmware_memsize

        default_selection = self.vf.vmware_get_default('vm_mem_size')
        self.logger.info("Default memory size is %s" % default_selection)
        selection = inquire.ask_text('Memory size', recommendation=default_selection, default=default)
        self.vmware_memsize = selection
        return self.vmware_memsize

    def vmware_get_cpucores(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_cpucores = write
            return self.vmware_cpucores

        if self.vmware_cpucores:
            return self.vmware_cpucores

        default_selection = self.vf.vmware_get_default('vm_cpu_cores')
        self.logger.info("Default CPU cores is %s" % default_selection)
        selection = inquire.ask_text('CPU cores', recommendation=default_selection, default=default)
        self.vmware_cpucores = selection
        return self.vmware_cpucores

    def vmware_get_folder(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_folder = write
            return self.vmware_folder

        if self.cb_cluster_name:
            default_selection = self.cb_cluster_name
        else:
            default_selection = self.vf.vmware_get_default('folder')

        self.logger.debug("Default folder is %s" % default_selection)

        if not self.vmware_folder:
            selection = inquire.ask_text('Folder', recommendation=default_selection, default=default)
            self.vmware_folder = selection

        if self.vmware_create_folder:
            for folder in self.vmware_dc_folder.vmFolder.childEntity:
                if folder.name == self.vmware_folder:
                    self.logger.info("Folder %s already exists." % self.vmware_folder)
                    return self.vmware_folder

            self.logger.info("Folder %s does not exist." % self.vmware_folder)
            print("Creating folder %s" % self.vmware_folder)
            try:
                self.vmware_dc_folder.vmFolder.CreateFolder(self.vmware_folder)
            except Exception as err:
                raise VMwareDriverError(f"can not create folder {self.vmware_folder}: {err}")

        return self.vmware_folder

    def vmware_get_datastore(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_datastore = write
            return self.vmware_datastore

        if self.vmware_datastore:
            return self.vmware_datastore

        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            datastore_name = []
            datastore_type = []
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
            esxi_hosts = container.view
            for esxi_host in esxi_hosts:
                storage_system = esxi_host.configManager.storageSystem
                host_file_sys_vol_mount_info = storage_system.fileSystemVolumeInfo.mountInfo
                for host_mount_info in host_file_sys_vol_mount_info:
                    if host_mount_info.volume.type == 'VFFS' or host_mount_info.volume.type == 'OTHER':
                        continue
                    datastore_name.append(host_mount_info.volume.name)
                    datastore_type.append(host_mount_info.volume.type)
            selection = inquire.ask_list('Select datastore', datastore_name, datastore_type, default=default)
            container.Destroy()
            self.vmware_datastore = datastore_name[selection]
            return self.vmware_datastore
        except Exception as err:
            raise VMwareDriverError(f"can not get datastore: {err}")

    def vmware_get_cluster(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_cluster = write
            return self.vmware_cluster

        if self.vmware_cluster:
            return self.vmware_cluster

        try:
            clusters = []
            for c in self.vmware_host_folder.childEntity:
                if isinstance(c, vim.ClusterComputeResource):
                    clusters.append(c.name)
            selection = inquire.ask_list('Select cluster', clusters, default=default)
            self.vmware_cluster = clusters[selection]
            return self.vmware_cluster
        except Exception as err:
            raise VMwareDriverError(f"can not get cluster: {err}")

    def vmware_get_datacenter(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_datacenter = write
            return self.vmware_datacenter

        try:
            si = SmartConnectNoSSL(host=self.vmware_hostname,
                                   user=self.vmware_username,
                                   pwd=self.vmware_password,
                                   port=443)
            content = si.RetrieveContent()
            datacenter = []
            container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)

            if not self.vmware_datacenter:
                for c in container.view:
                    datacenter.append(c.name)
                selection = inquire.ask_list('Select datacenter', datacenter, default=default)
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

    def vmware_get_hostname(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_hostname = write
            return self.vmware_hostname

        if self.vmware_hostname:
            return self.vmware_hostname

        self.vmware_hostname = inquire.ask_text("vSphere Host Name", default=default)
        return self.vmware_hostname

    def vmware_get_username(self, default=None, write=None) -> str:
        inquire = ask()

        if write:
            self.vmware_username = write
            return self.vmware_username

        if self.vmware_username:
            return self.vmware_username

        self.vmware_username = inquire.ask_text("vSphere Admin User", recommendation='administrator@vsphere.local', default=default)
        return self.vmware_username

    def vmware_get_password(self, default=None, write=None) -> bool:
        inquire = ask()

        if write:
            self.vmware_password = write
            return self.vmware_password

        if self.vmware_password:
            return self.vmware_password

        self.vmware_password = inquire.ask_pass("vSphere Admin Password", verify=False, default=default)
        return self.vmware_password
