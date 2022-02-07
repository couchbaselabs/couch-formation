# terraform-couchbase
Toolset for running and managing Couchbase clusters. Supports AWS, GCP, Azure, and VMware vSphere.

Runs on any POSIX style client including macOS and Linux.

## Prerequisites
- Python 3
- [Packer](https://learn.hashicorp.com/tutorials/packer/get-started-install-cli)
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- Cloud CLI/SDKs
  - [AWS CLI](https://aws.amazon.com/cli/)
  - [Google Cloud CLI](https://cloud.google.com/sdk/docs/quickstart)
  - [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- vCenter
- Homebrew (for macOS)

## Quick Start
Setup Python environment:
````
$ cd terraform-couchbase
$ ./setup.sh
````
Create an image in the target cloud:
````
$ bin/populate --packer --location gcp
````
Create the environment (development environment number 1):
````
$ bin/populate --dev 1 --location gcp
````
Deploy the environment:
````
$ cd gcp/dev-01
$ terraform init
$ terraform apply
````
To refresh the configuration files in an environment with updates to the default files:
````
$ bin/populate --dev 1 --location gcp --refresh
````

### VMware
For VMware environments with static IPs, you can supply the answers to IP related variables via parameters:
````
$ bin/populate --dev 1 --location vmware --static --dns --domain unix.us.com --subnet 172.16.100.0/24 --gateway 172.16.100.1
````

## Populate Utility
The populate utility helps create required variable files to support image and environment builds. It accelerates environment build time by attempting to autoconfigure as much as possible, and using multiple choice prompts when possible for any answers it requires.

Option | Description
------ | -----------
-h, --help | Show help message and exit
--template TEMPLATE | Variable template file
--globals GLOBALS | Global variables file
--locals LOCALS | Local variables file
--debug DEBUG | Debug level
--packer | Packer mode
--cluster | Cluster only mode
--dev DEV | Development environment number
--test TEST | Test environment number
--prod PROD | Prod environment number
--location LOCATION | Cloud type (aws,gcp,azure,vmware)
--singlezone | Use One Availability Zone
--refresh | Overwrite configuration files from defaults
--host HOST | vCenter host name
--user USER | vCenter administrative user
--password PASSWORD | vCenter administrative user password
--static | Assign Static IPs (where supported)
--dns | Update DNS with static IPs (required dynamic DNS service) 
--gateway GATEWAY | Default gateway with static IPs
--domain DOMAIN | DNS Domain with static IPs
--subnet SUBNET | Network subnet with static IPs
--omit OMIT | Omit IP range when auto assigning IPs

## Supported Variables
The following are the variable tokens recognized by the populate utility. The populate utility will work to get the value for these variables and create the appropriate variable file for either an image or environment build.

Variable Token | Description
-------------- | -----------
AWS_AMI_ID | AWS Couchbase AMI ID to use (created in Packer mode)
AWS_AMI_OWNER | AWS base image owner to use with Packer (supplied in local variable file)
AWS_AMI_USER | AWS OS user to use for SSH from base image (supplied in local variable file)
AWS_IMAGE | AWS base image to use to build Couchbase image (supplied in local variable file)
AWS_INSTANCE_TYPE | AWS EC2 instance type
AWS_REGION | AWS region (should be auto configured from the AWS CLI environment)
AWS_ROOT_IOPS | Root disk IOPS (supplied in local variable file, defaults to 0)
AWS_ROOT_SIZE | Root disk size (supplied in local variable file, defaults to 50Gb)
AWS_ROOT_TYPE | Root disk type (supplied in local variable file, defaults to gp3)
AWS_SECURITY_GROUP | AWS Security group
AWS_SSH_KEY | AWS SSH key to use for node access
AWS_SUBNET_ID | AWS Subnet ID
AWS_VPC_ID | AWS VPC ID
AZURE_ADMIN_USER | Azure SSH user (supplied in local variable file)
AZURE_DISK_SIZE | Azure root disk size (supplied in local variable file, defaults to 50Gb)
AZURE_DISK_TYPE | Azure root disk type (supplied in local variable file, defaults to StandardSSD_LRS)
AZURE_IMAGE_NAME | Azure Couchbase image to use (created in Packer mode)
AZURE_LOCATION | Azure location
AZURE_MACHINE_TYPE | Azure machine type
AZURE_NSG | Azure network security group
AZURE_OFFER | Azure Offer for base image (supplied in local variable file)
AZURE_PUBLISHER | Azure Publisher for base image (supplied in local variable file)
AZURE_RG | Azure Resource Group
AZURE_SKU | Azure SKU for base image (supplied in local variable file)
AZURE_SUBNET | Azure Subnet Name
AZURE_SUBSCRIPTION_ID | Azure Subscription ID (should get populated from CLI environment)
AZURE_VNET | Azure virtual network
CB_CLUSTER_NAME | Couchbase cluster name (default will be auto-constructed from environment type and number)
CB_INDEX_MEM_TYPE | Couchbase index memory storage option
CB_VERSION | Couchbase Server version
DNS_SERVER_LIST | List of statically assigned DNS servers
DOMAIN_NAME | DNS domain name
GCP_ACCOUNT_FILE | JSON file with GCP authentication credentials
GCP_CB_IMAGE | GCP Couchbase image (created in Packer mode)
GCP_IMAGE | GCP base image (supplied in local variable file)
GCP_IMAGE_FAMILY | GCP image family (supplied in local variable file)
GCP_IMAGE_USER | GCP SSH user for node access (supplied in local variable file)
GCP_MACHINE_TYPE | GCP machine type
GCP_PROJECT | GCP Project
GCP_REGION | GCP region 
GCP_ROOT_SIZE | GCP root disk size (supplied in local variable file, defaults to 50Gb)
GCP_ROOT_TYPE | GCP root disk type (supplied in local variable file, defaults to pd-standard)
GCP_SA_EMAIL | GCP service account email (should be obtained from auth JSON)
GCP_SUBNET | GCP subnet
GCP_ZONE | GCP availability zone (the complete zone list is constructed based on region)
LINUX_RELEASE | Linux OS release (supplied in local variable file)
LINUX_TYPE | Linux distribution type (supplied in local variable file)
SSH_PRIVATE_KEY | SSH private key file
SSH_PUBLIC_KEY_FILE | SSH public key file (may be auto configured based on private key file)
USE_PUBLIC_IP | Use the public IP for node SSH access
VMWARE_BUILD_PASSWORD | VMware password to use for Packer to build template
VMWARE_BUILD_PWD_ENCRYPTED | Auto-generated from password entered 
VMWARE_BUILD_USERNAME | VMware template administrative user
VMWARE_CLUSTER | VMware cluster
VMWARE_CPU_CORES | VMware cores for virtual machines 
VMWARE_DATACENTER | VMware datacenter 
VMWARE_DATASTORE | VMware datastore
VMWARE_DISK_SIZE | VMware root disk size (supplied in local variable file)
VMWARE_DVS | VMware distributed virtual switch
VMWARE_FOLDER | VMware folder
VMWARE_HOSTNAME | vCenter IP or host name
VMWARE_ISO_CHECKSUM | VMware build ISO file checksum (supplied in local variable file)
VMWARE_ISO_URL | Linux distribution ISO URL (supplied in local variable file)
VMWARE_KEY | SSH key to use for host access
VMWARE_MEM_SIZE | VMware memory for virtual machines
VMWARE_NETWORK | VMware port group to use for virtual machines
VMWARE_OS_TYPE | VMware linux OS type (supplied in local variable file)
VMWARE_PASSWORD | vCenter administrative user password 
VMWARE_SW_URL | Linux distribution software repo (used for Centos Kickstart - supplied in local variable file)
VMWARE_TEMPLATE | VMware template to use (created in Packer mode)
VMWARE_TIMEZONE | VMware timezone for template 
VMWARE_USERNAME | VMware vCenter administrative username 
