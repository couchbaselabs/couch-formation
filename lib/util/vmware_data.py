##
##

import logging
from lib.util.filemgr import FileManager
from lib.util.inquire import Inquire
from lib.exceptions import VMWareDataError, EmptyResultSet
import lib.config as config
from lib.util.envmgr import PathMap, PathType, ConfigFile
from lib.hcl.vmware_image import VMWareImageDataRecord
from lib.util.cfgmgr import ConfigMgr
from lib.util.network import NetworkUtil


class DataCollect(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vmware_hostname = None
        self.vmware_username = None
        self.vmware_password = None
        self.vmware_datacenter = None
        self.vmware_cluster = None
        self.vmware_datastore = None
        self.vmware_template_folder = None
        self.vmware_cluster_folder = None
        self.vmware_network = None
        self.vmware_dvs = None
        self.vmware_folder = None
        self.vmware_cpucores = None
        self.vmware_memsize = None
        self.vmware_disksize = None
        self.vmware_network = None
        self.vmware_build_password = None
        self.vmware_build_pwd_encrypted = None
        self.vmware_template = None
        self.ssh_fingerprint = None
        self.public_key = None
        self.private_key = None
        self.public_key_data = None
        self.domain_name = None
        self.dns_server_list = []
        self.image_user = None
        self.image_release = None
        self.image_type = None
        self.vm_mem_size = None
        self.vm_cpu_cores = None
        self.instance_type = None
        self.cb_index_mem_type = None
        self.vmware_hosts = []
        self.subnet_list = []
        self.disk_iops = 0
        self.disk_size = config.cloud_base().VMWARE_DISK_SIZE
        self.disk_type = config.cloud_base().VMWARE_DISK_TYPE

        self.path_map = PathMap(config.env_name, config.cloud)
        self.path_map.map(PathType.CONFIG)
        cfg_file: ConfigFile
        cfg_file = self.path_map.use(config.cloud_operator.CONFIG_FILE, PathType.CONFIG)
        self.env_cfg = ConfigMgr(cfg_file.file_name)

    def get_infrastructure(self):
        config.static_ip = True
        print("")
        in_progress = self.env_cfg.get("vmware_base_in_progress")

        if in_progress is not None and in_progress is False:
            print("VMware infrastructure is configured")

            self.vmware_hostname = self.env_cfg.get("vmware_hostname")
            self.vmware_username = self.env_cfg.get("vmware_username")
            self.vmware_password = self.env_cfg.get("vmware_password")
            self.vmware_datacenter = self.env_cfg.get("vmware_datacenter")
            self.vmware_cluster = self.env_cfg.get("vmware_cluster")
            self.vmware_template_folder = self.env_cfg.get("vmware_template_folder")
            self.vmware_cluster_folder = self.env_cfg.get("vmware_cluster_folder")
            self.vmware_datastore = self.env_cfg.get("vmware_datastore")
            self.vmware_network = self.env_cfg.get("vmware_network")
            self.vmware_dvs = self.env_cfg.get("vmware_dvs")
            self.subnet_list = self.env_cfg.get("vmware_subnet_list")
            print(f"Hostname        = {self.vmware_hostname}")
            print(f"Username        = {self.vmware_username}")
            print(f"Password        = {self.vmware_password}")
            print(f"Datacenter      = {self.vmware_datacenter}")
            print(f"Cluster         = {self.vmware_cluster}")
            print(f"Template Folder = {self.vmware_template_folder}")
            print(f"Cluster Folder  = {self.vmware_cluster_folder}")
            print(f"Datastore       = {self.vmware_datastore}")
            print(f"Network         = {self.vmware_network}")
            print(f"Switch          = {self.vmware_dvs}")
            subnet_display = ','.join(list(f"{i['zone']}" for i in self.subnet_list))
            print(f"Zones           = {subnet_display}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(vmware_base_in_progress=True)

        config.cloud_base()
        self.vmware_datacenter = config.cloud_base().vmware_datacenter
        self.vmware_username = config.cloud_base().vmware_username
        self.vmware_hostname = config.cloud_base().vmware_hostname
        self.vmware_password = config.cloud_base().vmware_password
        self.vmware_cluster = config.cloud_base().vmware_get_cluster()
        self.vmware_template_folder = config.cloud_base().vmware_get_template_folder()
        self.vmware_cluster_folder = config.cloud_base().vmware_get_cluster_folder()
        self.vmware_datastore = config.cloud_base().vmware_get_datastore()
        self.vmware_dvs = config.cloud_base().vmware_get_dvs_switch()
        self.vmware_network = config.cloud_base().vmware_get_dvs_network(self.vmware_dvs)
        self.vmware_hosts = config.cloud_base().vmware_get_hosts(self.vmware_cluster)
        self.subnet_list.clear()
        for host in self.vmware_hosts:
            subnet_record = {'name': host['hostname'],
                             'zone': host['name']}
            self.subnet_list.append(subnet_record)

        self.env_cfg.update(vmware_hostname=self.vmware_hostname)
        self.env_cfg.update(vmware_username=self.vmware_username)
        self.env_cfg.update(vmware_password=self.vmware_password)
        self.env_cfg.update(vmware_datacenter=self.vmware_datacenter)
        self.env_cfg.update(vmware_cluster=self.vmware_cluster)
        self.env_cfg.update(vmware_template_folder=self.vmware_template_folder)
        self.env_cfg.update(vmware_cluster_folder=self.vmware_cluster_folder)
        self.env_cfg.update(vmware_datastore=self.vmware_datastore)
        self.env_cfg.update(vmware_dvs=self.vmware_dvs)
        self.env_cfg.update(vmware_network=self.vmware_network)
        self.env_cfg.update(vmware_subnet_list=self.subnet_list)
        self.env_cfg.update(vmware_base_in_progress=False)

    def get_build_password(self):
        print("")
        in_progress = self.env_cfg.get("vmware_password_in_progress")

        if in_progress is not None and in_progress is False:
            print("VMware build password is configured")

            self.vmware_build_password = self.env_cfg.get("vmware_build_password")
            self.vmware_build_pwd_encrypted = self.env_cfg.get("vmware_build_password_encrypted")
            print(f"Build Password           = {self.vmware_build_password}")
            print(f"Build Password Encrypted = {self.vmware_build_pwd_encrypted}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(vmware_password_in_progress=True)

        self.vmware_build_password = config.cloud_base().vmware_get_build_password()
        self.vmware_build_pwd_encrypted = config.cloud_base().vmware_get_build_pwd_encrypted(self.vmware_build_password)

        self.env_cfg.update(vmware_build_password=self.vmware_build_password)
        self.env_cfg.update(vmware_build_password_encrypted=self.vmware_build_pwd_encrypted)
        self.env_cfg.update(vmware_password_in_progress=False)

    def get_keys(self):
        in_progress = self.env_cfg.get("ssh_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("SSH key is configured")

            self.private_key = self.env_cfg.get("ssh_private_key")
            self.ssh_fingerprint = self.env_cfg.get("ssh_fingerprint")
            self.public_key = self.env_cfg.get("ssh_public_key")
            self.public_key_data = self.env_cfg.get("ssh_public_key_data")
            print(f"Private Key       = {self.private_key}")
            print(f"Fingerprint       = {self.ssh_fingerprint}")
            print(f"Public Key        = {self.public_key}")
            print(f"Public Key Data   = {self.public_key_data}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(ssh_in_progress=True)

        try:
            key_file_list = FileManager.list_private_key_files()
            ssh_key = Inquire().ask_list_dict("Select SSH private key file", key_file_list, hide_key=["pub_fingerprint"])
            self.private_key = ssh_key.get("file")
            self.ssh_fingerprint = ssh_key.get("fingerprint")
        except EmptyResultSet:
            raise VMWareDataError(f"can not find any SSH private key files, please create a SSH key")

        self.public_key = FileManager().get_ssh_public_key_file(self.private_key)
        self.public_key_data = FileManager().get_ssh_public_key(self.private_key)

        self.env_cfg.update(ssh_private_key=self.private_key)
        self.env_cfg.update(ssh_fingerprint=self.ssh_fingerprint)
        self.env_cfg.update(ssh_public_key=self.public_key)
        self.env_cfg.update(ssh_public_key_data=self.public_key_data)
        self.env_cfg.update(ssh_in_progress=False)

    def get_domain(self):
        in_progress = self.env_cfg.get("vmware_network_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Network is configured")

            self.domain_name = self.env_cfg.get("vmware_domain_name")
            self.dns_server_list = self.env_cfg.get("vmware_dns_server_list")
            print(f"Domain Name     = {self.domain_name}")
            print(f"DNS Server List = {','.join(self.dns_server_list)}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(vmware_network_in_progress=True)

        self.domain_name = NetworkUtil().get_domain_name()

        self.domain_name = Inquire().ask_text('DNS Domain', default=self.domain_name)

        self.dns_server_list = NetworkUtil().get_dns_servers(self.domain_name)
        try:
            server = self.dns_server_list[0]
        except (IndexError, TypeError):
            server = None

        server = Inquire().ask_text('DNS Server', default=server)
        self.dns_server_list = NetworkUtil().get_dns_servers(self.domain_name, server=server)

        self.env_cfg.update(vmware_domain_name=self.domain_name)
        self.env_cfg.update(vmware_dns_server_list=self.dns_server_list)
        self.env_cfg.update(vmware_network_in_progress=False)

    def get_image(self):
        in_progress = self.env_cfg.get("vmware_image_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Image is configured")

            self.image_user = self.env_cfg.get("ssh_user_name")
            self.vmware_template = self.env_cfg.get("vmware_template")
            print(f"SSH User Name = {self.image_user}")
            print(f"Template      = {self.vmware_template}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(vmware_image_in_progress=True)

        template_list = config.cloud_base().vmware_get_templates()

        template = Inquire().ask_list_dict(f"Select {config.cloud} image", template_list)

        self.vmware_template = template['name']
        self.image_type = template['type']
        self.image_release = template['release']

        distro_table = VMWareImageDataRecord.by_version(self.image_type, self.image_release, config.cloud_operator().config.build)

        self.image_user = distro_table.user

        self.env_cfg.update(ssh_user_name=self.image_user)
        self.env_cfg.update(vmware_template=self.vmware_template)
        self.env_cfg.update(vmware_image_in_progress=False)

    def get_cluster_settings(self):
        option_list = [
            {
                'name': 'default',
                'description': 'Standard Index Storage'
            },
            {
                'name': 'memopt',
                'description': 'Memory-optimized'
            },
        ]

        in_progress = self.env_cfg.get("cbs_in_progress")

        print("")
        if in_progress is not None and in_progress is False:
            print("Cluster settings are configured")

            self.cb_index_mem_type = self.env_cfg.get("cbs_index_memory")
            print(f"CBS Index Memory = {self.cb_index_mem_type}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(cbs_in_progress=True)

        selection = Inquire().ask_list_dict('Select index storage option', option_list)
        self.cb_index_mem_type = selection['name']

        self.env_cfg.update(cbs_index_memory=self.cb_index_mem_type)
        self.env_cfg.update(cbs_in_progress=False)

    def get_node_settings(self, default: bool = True):
        in_progress = self.env_cfg.get("vmware_node_in_progress")

        print("")
        if in_progress is not None and (in_progress is False or default is False):
            print("Node settings")

            self.instance_type = self.env_cfg.get("vmware_machine_type")
            self.vm_cpu_cores = self.env_cfg.get("vmware_vm_cpu_cores")
            self.vm_mem_size = self.env_cfg.get("vmware_vm_mem_size")
            print(f"Machine Type    = {self.instance_type}")
            print(f"CPU Size        = {self.vm_cpu_cores}")
            print(f"Memory Size     = {self.vm_mem_size}")

            if not Inquire().ask_bool("Update settings", recommendation='false'):
                return

        self.env_cfg.update(vmware_node_in_progress=True)

        selection = Inquire().ask_list_dict("Select machine type", config.cloud_base().VMWARE_MACHINE_TYPES)

        self.instance_type = selection['name']
        self.vm_cpu_cores = selection['cpu']
        self.vm_mem_size = selection['memory']

        self.env_cfg.update(vmware_machine_type=self.instance_type)
        self.env_cfg.update(vmware_vm_cpu_cores=self.vm_cpu_cores)
        self.env_cfg.update(vmware_vm_mem_size=self.vm_mem_size)
        self.env_cfg.update(vmware_node_in_progress=False)
