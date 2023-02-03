# couch-formation
Toolset for running and managing Couchbase clusters. Supports AWS, GCP, Azure, and VMware vSphere. Runs on any POSIX style client such as macOS and Linux.

## Version 3.0
> Version 3.0 Beta 1 will be released soon. Feel free to [try it out](https://github.com/couchbaselabs/couch-formation/tree/Version_3.0).<br>
> ```git clone -b Version_3.0 https://github.com/couchbaselabs/couch-formation```
## Disclaimer

> This package is **NOT SUPPORTED BY COUCHBASE**. The toolset is under active development, therefore features and functionality can change.

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
$ cd couch-formation
$ ./setup.sh
````
Create an image in the target cloud:
````
$ bin/cloudmgr image --build --cloud aws
$ bin/cloudmgr image --build --cloud gcp
$ bin/cloudmgr image --build --cloud azure
````
Create the environment (development environment number 4 with application and Sync Gateway nodes). Note the numbers are environment specifiers so that you can have multiple active environments. These are not node counts. You will be prompted for the node count for each node type.
````
$ bin/cloudmgr create --dev 4 --app 1 --sgw 1 --cloud gcp
````
List node information for an environment:
````
$ bin/cloudmgr list --dev 5 --cloud gcp
````
Remove an environment:
````
$ bin/cloudmgr destroy --dev 5 --cloud gcp
````

### VMware
For VMware environments with static IPs, store DNS and subnet details to be used for environment creation (requires DNS servers that allow TSIG dynamic updates):
````
$ bin/cloudmgr net --domain
$ bin/cloudmgr net --cidr
$ bin/cloudmgr create --dev 4 --app 1 --cloud vmware
````

## Cloudmgr Utility
The cloudmgr utility orchestrates environment builds. It accelerates environment build time by attempting to autoconfigure as much as possible, and using multiple choice prompts when possible for any answers it requires.

| Create/Destroy/List Options | Description                                               |
|-----------------------------|-----------------------------------------------------------|
| -h, --help                  | Show help message and exit                                |
| --debug DEBUG               | Debug level                                               |
| --dev DEV                   | Development environment number                            |
| --test TEST                 | Test environment number                                   |
| --prod PROD                 | Prod environment number                                   |
| --app APP                   | App environment number                                    |
| --sgw SGW                   | Sync Gateway environment number                           |
| --cloud CLOUD               | Cloud type (aws,gcp,azure,vmware)                         |
| --zone                      | Use One Availability Zone                                 |
| --static                    | Assign Static IPs (where supported)                       |
| --dns                       | Update DNS with static IPs (required dynamic DNS service) |
| --all                       | List all environments                                     |

| Image Options | Description                                               |
|---------------|-----------------------------------------------------------|
| --list        | List images                                               |
| --build       | Build an image                                            |
| --delete      | Delete an image                                           |

| Net Options | Description                     |
|-------------|---------------------------------|
| --list      | List stored network information |
| --domain    | Add domain                      |
| --cidr      | Add Subnet                      |

## Supported Variables
The following are the variable tokens recognized by the cloudmgr utility. The cloudmgr package includes embedded assets for environment creation, so under normal circumstances it should not be necessary to modify these files.

| Variable Token             | Description                                                                                    |
|----------------------------|------------------------------------------------------------------------------------------------|
| AWS_AMI_ID                 | AWS Couchbase AMI ID to use (created in Packer mode)                                           |
| AWS_AMI_OWNER              | AWS base image owner to use with Packer (supplied in local variable file)                      |
| AWS_AMI_USER               | AWS OS user to use for SSH from base image (supplied in local variable file)                   |
| AWS_IMAGE                  | AWS base image to use to build Couchbase image (supplied in local variable file)               |
| AWS_INSTANCE_TYPE          | AWS EC2 instance type                                                                          |
| AWS_REGION                 | AWS region (should be auto configured from the AWS CLI environment)                            |
| AWS_ROOT_IOPS              | Root disk IOPS (supplied in local variable file, defaults to 0)                                |
| AWS_ROOT_SIZE              | Root disk size (supplied in local variable file, defaults to 50Gb)                             |
| AWS_ROOT_TYPE              | Root disk type (supplied in local variable file, defaults to gp3)                              |
| AWS_SECURITY_GROUP         | AWS Security group                                                                             |
| AWS_SSH_KEY                | AWS SSH key to use for node access                                                             |
| AWS_SUBNET_ID              | AWS Subnet ID                                                                                  |
| AWS_VPC_ID                 | AWS VPC ID                                                                                     |
| AZURE_ADMIN_USER           | Azure SSH user (supplied in local variable file)                                               |
| AZURE_DISK_SIZE            | Azure root disk size (supplied in local variable file, defaults to 50Gb)                       |
| AZURE_DISK_TYPE            | Azure root disk type (supplied in local variable file, defaults to StandardSSD_LRS)            |
| AZURE_IMAGE_NAME           | Azure Couchbase image to use (created in Packer mode)                                          |
| AZURE_LOCATION             | Azure location                                                                                 |
| AZURE_MACHINE_TYPE         | Azure machine type                                                                             |
| AZURE_NSG                  | Azure network security group                                                                   |
| AZURE_OFFER                | Azure Offer for base image (supplied in local variable file)                                   |
| AZURE_PUBLISHER            | Azure Publisher for base image (supplied in local variable file)                               |
| AZURE_RG                   | Azure Resource Group                                                                           |
| AZURE_SKU                  | Azure SKU for base image (supplied in local variable file)                                     |
| AZURE_SUBNET               | Azure Subnet Name                                                                              |
| AZURE_SUBSCRIPTION_ID      | Azure Subscription ID (should get populated from CLI environment)                              |
| AZURE_VNET                 | Azure virtual network                                                                          |
| CB_CLUSTER_NAME            | Couchbase cluster name (default will be auto-constructed from environment type and number)     |
| CB_INDEX_MEM_TYPE          | Couchbase index memory storage option                                                          |
| CB_VERSION                 | Couchbase Server version                                                                       |
| DNS_SERVER_LIST            | List of statically assigned DNS servers                                                        |
| DOMAIN_NAME                | DNS domain name                                                                                |
| GCP_ACCOUNT_FILE           | JSON file with GCP authentication credentials                                                  |
| GCP_CB_IMAGE               | GCP Couchbase image (created in Packer mode)                                                   |
| GCP_IMAGE                  | GCP base image (supplied in local variable file)                                               |
| GCP_IMAGE_FAMILY           | GCP image family (supplied in local variable file)                                             |
| GCP_IMAGE_USER             | GCP SSH user for node access (supplied in local variable file)                                 |
| GCP_MACHINE_TYPE           | GCP machine type                                                                               |
| GCP_PROJECT                | GCP Project                                                                                    |
| GCP_REGION                 | GCP region                                                                                     |
| GCP_ROOT_SIZE              | GCP root disk size (supplied in local variable file, defaults to 50Gb)                         |
| GCP_ROOT_TYPE              | GCP root disk type (supplied in local variable file, defaults to pd-standard)                  |
| GCP_SA_EMAIL               | GCP service account email (should be obtained from auth JSON)                                  |
| GCP_SUBNET                 | GCP subnet                                                                                     |
| GCP_ZONE                   | GCP availability zone (the complete zone list is constructed based on region)                  |
| LINUX_RELEASE              | Linux OS release (supplied in local variable file)                                             |
| LINUX_TYPE                 | Linux distribution type (supplied in local variable file)                                      |
| SSH_PRIVATE_KEY            | SSH private key file                                                                           |
| SSH_PUBLIC_KEY_FILE        | SSH public key file (may be auto configured based on private key file)                         |
| USE_PUBLIC_IP              | Use the public IP for node SSH access                                                          |
| VMWARE_BUILD_PASSWORD      | VMware password to use for Packer to build template                                            |
| VMWARE_BUILD_PWD_ENCRYPTED | Auto-generated from password entered                                                           |
| VMWARE_BUILD_USERNAME      | VMware template administrative user                                                            |
| VMWARE_CLUSTER             | VMware cluster                                                                                 |
| VMWARE_CPU_CORES           | VMware cores for virtual machines                                                              |
| VMWARE_DATACENTER          | VMware datacenter                                                                              |
| VMWARE_DATASTORE           | VMware datastore                                                                               |
| VMWARE_DISK_SIZE           | VMware root disk size (supplied in local variable file)                                        |
| VMWARE_DVS                 | VMware distributed virtual switch                                                              |
| VMWARE_FOLDER              | VMware folder                                                                                  |
| VMWARE_HOSTNAME            | vCenter IP or host name                                                                        |
| VMWARE_ISO_CHECKSUM        | VMware build ISO file checksum (supplied in local variable file)                               |
| VMWARE_ISO_URL             | Linux distribution ISO URL (supplied in local variable file)                                   |
| VMWARE_KEY                 | SSH key to use for host access                                                                 |
| VMWARE_MEM_SIZE            | VMware memory for virtual machines                                                             |
| VMWARE_NETWORK             | VMware port group to use for virtual machines                                                  |
| VMWARE_OS_TYPE             | VMware linux OS type (supplied in local variable file)                                         |
| VMWARE_PASSWORD            | vCenter administrative user password                                                           |
| VMWARE_SW_URL              | Linux distribution software repo (used for Centos Kickstart - supplied in local variable file) |
| VMWARE_TEMPLATE            | VMware template to use (created in Packer mode)                                                |
| VMWARE_TIMEZONE            | VMware timezone for template                                                                   |
| VMWARE_USERNAME            | VMware vCenter administrative username                                                         |
