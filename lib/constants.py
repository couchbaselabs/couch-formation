##
##

PUBLIC_CLOUD = True
MODE_TFVAR = 0x0001
MODE_CLUSTER_MAP = 0x0002
MODE_PACKER = 0x0003
MODE_KUBE_MAP = 0x0004
MODE_APP_MAP = 0x0005

CLUSTER_CONFIG = 0x0010
APP_CONFIG = 0x0011
SGW_CONFIG = 0x0012

CB_CFG_HEAD = """####
variable "cluster_spec" {
  description = "Map of cluster nodes and services."
  type        = map
  default     = {"""

APP_CFG_HEAD = """####
variable "app_spec" {
  description = "Map of app nodes."
  type        = map
  default     = {"""

SGW_CFG_HEAD = """####
variable "sgw_spec" {
  description = "Map of Sync Gateway nodes."
  type        = map
  default     = {"""

CB_CFG_NODE = """
    {{ NODE_NAME }} = {
      node_number     = {{ NODE_NUMBER }},
      node_services   = "{{ NODE_SERVICES }}",
      install_mode    = "{{ NODE_INSTALL_MODE }}",
      node_env        = "{{ NODE_ENV }}",
      node_zone       = "{{ NODE_ZONE }}",
      node_subnet     = "{{ NODE_SUBNET }}",
      node_ip_address = "{{ NODE_IP_ADDRESS }}",
      node_netmask    = "{{ NODE_NETMASK }}",
      node_gateway    = "{{ NODE_GATEWAY }}",
    }
"""

CB_CFG_TAIL = """
  }
}
"""

SUPPORTED_VARIABLES = [
            ('AWS_AMI_ID', 1, 'ami_id', None),
            ('AWS_AMI_OWNER', 2, 'aws_image_owner', None),
            ('AWS_AMI_USER', 2, 'aws_image_user', None),
            ('AWS_IMAGE', 2, 'aws_image_name', None),
            ('AWS_INSTANCE_TYPE', 6, 'instance_type', None),
            ('AWS_REGION', 0, 'region_name', None),
            ('AWS_ROOT_IOPS', 7, 'root_volume_iops', None),
            ('AWS_ROOT_SIZE', 8, 'root_volume_size', None),
            ('AWS_ROOT_TYPE', 9, 'root_volume_type', None),
            ('AWS_SECURITY_GROUP', 5, 'security_group_ids', None),
            ('AWS_SSH_KEY', 0, 'ssh_key', None),
            ('AWS_SUBNET_ID', 4, 'subnet_id', None),
            ('AWS_VPC_ID', 3, 'vpc_id', None),
            ('AZURE_ADMIN_USER', 4, 'azure_admin_user', None),
            ('AZURE_DISK_SIZE', 9, 'azure_disk_size', None),
            ('AZURE_DISK_TYPE', 10, 'azure_disk_type', None),
            ('AZURE_IMAGE_NAME', 3, 'azure_image_name', None),
            ('AZURE_LOCATION', 1, 'azure_location', None),
            ('AZURE_MACHINE_TYPE', 2, 'azure_machine_type', None),
            ('AZURE_NSG', 2, 'azure_nsg', None),
            ('AZURE_OFFER', 4, 'azure_image_offer', None),
            ('AZURE_PUBLISHER', 5, 'azure_image_publisher', None),
            ('AZURE_RG', 0, 'azure_resource_group', None),
            ('AZURE_SKU', 6, 'azure_image_sku', None),
            ('AZURE_SUBNET', 8, 'azure_subnet', None),
            ('AZURE_SUBSCRIPTION_ID', 0, 'azure_subscription_id', None),
            ('AZURE_VNET', 7, 'azure_vnet', None),
            ('CB_CLUSTER_NAME', 2, 'cb_cluster_name', None),
            ('CB_INDEX_MEM_TYPE', 2, 'index_memory', None),
            ('CB_VERSION', 2, 'cb_version', None),
            ('DNS_SERVER_LIST', 2, 'dns_server_list', None),
            ('DOMAIN_NAME', 1, 'domain_name', None),
            ('GCP_ACCOUNT_FILE', 0, 'gcp_account_file', None),
            ('GCP_CB_IMAGE', 3, 'gcp_cb_image', None),
            ('GCP_IMAGE', 3, 'gcp_image_name', None),
            ('GCP_IMAGE_FAMILY', 5, 'gcp_image_family', None),
            ('GCP_IMAGE_USER', 6, 'gcp_image_user', None),
            ('GCP_MACHINE_TYPE', 7, 'gcp_machine_type', None),
            ('GCP_PROJECT', 1, 'gcp_project', None),
            ('GCP_REGION', 2, 'gcp_region', None),
            ('GCP_ROOT_SIZE', 8, 'gcp_disk_size', None),
            ('GCP_ROOT_TYPE', 9, 'gcp_disk_type', None),
            ('GCP_SA_EMAIL', 2, 'gcp_service_account_email', None),
            ('GCP_SUBNET', 10, 'gcp_subnet', None),
            ('GCP_ZONE', 4, 'gcp_zone', None),
            ('LINUX_RELEASE', 1, 'os_linux_release', None),
            ('LINUX_TYPE', 1, 'os_linux_type', None),
            ('SSH_PRIVATE_KEY', 1, 'ssh_private_key', None),
            ('SSH_PUBLIC_KEY_FILE', 2, 'ssh_public_key_file', None),
            ('USE_PUBLIC_IP', 1, 'use_public_ip', None),
            ('VMWARE_BUILD_PASSWORD', 20, 'build_password', None),
            ('VMWARE_BUILD_PWD_ENCRYPTED', 19, 'build_password_encrypted', None),
            ('VMWARE_BUILD_USERNAME', 18, 'build_username', None),
            ('VMWARE_CLUSTER', 4, 'vsphere_cluster', None),
            ('VMWARE_CPU_CORES', 16, 'vm_cpu_cores', None),
            ('VMWARE_DATACENTER', 3, 'vsphere_datacenter', None),
            ('VMWARE_DATASTORE', 7, 'vsphere_datastore', None),
            ('VMWARE_DISK_SIZE', 15, 'vm_disk_size', None),
            ('VMWARE_DVS', 5, 'vsphere_dvs_switch', None),
            ('VMWARE_FOLDER', 14, 'vsphere_folder', None),
            ('VMWARE_HOSTNAME', 2, 'vsphere_server', None),
            ('VMWARE_ISO_CHECKSUM', 9, 'iso_checksum', None),
            ('VMWARE_ISO_URL', 8, 'iso_url', None),
            ('VMWARE_KEY', 13, 'build_key', None),
            ('VMWARE_MEM_SIZE', 17, 'vm_mem_size', None),
            ('VMWARE_NETWORK', 6, 'vsphere_network', None),
            ('VMWARE_OS_TYPE', 4, 'vm_guest_os_type', None),
            ('VMWARE_PASSWORD', 1, 'vsphere_password', None),
            ('VMWARE_SW_URL', 10, 'sw_url', None),
            ('VMWARE_TEMPLATE', 11, 'vsphere_template', None),
            ('VMWARE_TIMEZONE', 12, 'vm_guest_os_timezone', None),
            ('VMWARE_USERNAME', 0, 'vsphere_user', None),
        ]
