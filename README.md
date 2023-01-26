# Couch Formation 3.0
Toolset for running and managing Couchbase clusters. Supports AWS, GCP, Azure, and Couchbase Capella.

Runs on any POSIX style client such as macOS and Linux.

## Disclaimer

> This package is **NOT SUPPORTED BY COUCHBASE**. The toolset is under active development, therefore features and functionality can change.

## Prerequisites
- Python 3.9
- Cloud CLI/SDKs
  - [AWS CLI](https://aws.amazon.com/cli/)
  - [Google Cloud CLI](https://cloud.google.com/sdk/docs/quickstart)
  - [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Homebrew (for macOS)

## Quick Start
Setup Python environment:
````
$ cd couch-formation
$ ./setup.sh
````
Create an image in the target cloud:
````
$ bin/cloudmgr image build --cloud aws
$ bin/cloudmgr image build --cloud gcp
$ bin/cloudmgr image build --cloud azure
````
Create the environment
````
$ bin/cloudmgr create cluster --name dev01 --cloud gcp
````
List node information:
````
$ bin/cloudmgr list nodes
````
Uninstall the nodes:
````
$ bin/cloudmgr destroy cluster --name dev03 --cloud capella
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
