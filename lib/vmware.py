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


class vmware(object):

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

    def vmware_init(self):
        tb = toolbox()
        config_directory = os.environ['HOME'] + '/.config'
        auth_directory = config_directory + '/imagemgr'
        config_file = auth_directory + '/vmware_auth.json'

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

    def vmware_get_template(self, select=True, default=None) -> Union[dict, list[dict]]:
        inquire = ask()

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
                    templates.append(image_block)
            container.Destroy()
            if select:
                selection = inquire.ask_list('Select template', templates, default=default)
                return templates[selection]
            else:
                return templates
        except Exception as err:
            raise VMwareDriverError(f"can not get template: {err}")

    def vmware_get_build_password(self, vmware_build_user: str, default=None) -> tuple[str, str]:
        inquire = ask()

        selection = inquire.ask_pass("Build user %s password" % vmware_build_user, default=default)
        vmware_build_password = selection
        vmware_build_pwd_encrypted = sha512_crypt.using(salt=''.join([random.choice(string.ascii_letters + string.digits) for _ in range(16)]), rounds=5000).hash(vmware_build_password)
        return vmware_build_password, vmware_build_pwd_encrypted

    def vmware_get_dvs_network(self, default=None) -> str:
        inquire = ask()
        pgList = []

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
            return pgList[selection]
        except Exception as err:
            raise VMwareDriverError(f"can not get port group: {err}")

    def vmware_get_dvs_switch(self, default=None) -> str:
        inquire = ask()
        dvsList = []

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
            return dvsList[selection]
        except Exception as err:
            raise VMwareDriverError(f"can not get distributed switch: {err}")

    def vmware_get_disksize(self, default=None) -> str:
        inquire = ask()

        default_selection = self.vf.gcp_get_default('vm_disk_size')
        self.logger.info("Default disk size is %s" % default_selection)
        selection = inquire.ask_text('Disk size', recommendation=default_selection, default=default)
        return selection

    def vmware_get_memsize(self, default=None) -> str:
        inquire = ask()

        default_selection = self.vf.gcp_get_default('vm_mem_size')
        self.logger.info("Default memory size is %s" % default_selection)
        selection = inquire.ask_text('Memory size', recommendation=default_selection, default=default)
        return selection

    def vmware_get_cpucores(self, default=None) -> str:
        inquire = ask()

        default_selection = self.vf.gcp_get_default('vm_cpu_cores')
        self.logger.info("Default CPU cores is %s" % default_selection)
        selection = inquire.ask_text('CPU cores', recommendation=default_selection, default=default)
        return selection

    def vmware_get_folder(self, dev_num=None, test_num=None, prod_num=None, create=False, default=None) -> str:
        inquire = ask()

        if dev_num:
            default_selection = "couchbase-dev{:02d}".format(dev_num)
        elif test_num:
            default_selection = "couchbase-tst{:02d}".format(test_num)
        elif prod_num:
            default_selection = "couchbase-prd{:02d}".format(prod_num)
        else:
            default_selection = self.vf.gcp_get_default('folder')

        self.logger.info("Default folder is %s" % default_selection)

        selection = inquire.ask_text('Folder', recommendation=default_selection, default=default)

        vmware_folder = selection

        if create:
            for folder in self.vmware_dc_folder.vmFolder.childEntity:
                if folder.name == vmware_folder:
                    self.logger.info("Folder %s already exists." % vmware_folder)
                    return vmware_folder

            self.logger.info("Folder %s does not exist." % vmware_folder)
            print("Creating folder %s" % vmware_folder)
            try:
                self.vmware_dc_folder.vmFolder.CreateFolder(vmware_folder)
            except Exception as err:
                raise VMwareDriverError(f"can not create folder {vmware_folder}: {err}")

        return vmware_folder

    def vmware_get_datastore(self, default=None) -> str:
        inquire = ask()

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
            return datastore_name[selection]
        except Exception as err:
            raise VMwareDriverError(f"can not get datastore: {err}")

    def vmware_get_cluster(self, default=None) -> str:
        inquire = ask()

        try:
            clusters = []
            for c in self.vmware_host_folder.childEntity:
                if isinstance(c, vim.ClusterComputeResource):
                    clusters.append(c.name)
            selection = inquire.ask_list('Select cluster', clusters, default=default)
            return clusters[selection]
        except Exception as err:
            raise VMwareDriverError(f"can not get cluster: {err}")

    def vmware_get_datacenter(self, default=None) -> str:
        inquire = ask()

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

    def vmware_get_hostname(self, default=None) -> bool:
        inquire = ask()
        self.vmware_hostname = inquire.ask_text("vSphere Host Name", default=default)
        return True

    def vmware_get_username(self, default=None) -> bool:
        inquire = ask()
        self.vmware_username = inquire.ask_text("vSphere Admin User", recommendation='administrator@vsphere.local', default=default)
        return True

    def vmware_get_password(self, default=None) -> bool:
        inquire = ask()
        self.vmware_password = inquire.ask_pass("vSphere Admin Password", verify=False, default=default)
        return True
