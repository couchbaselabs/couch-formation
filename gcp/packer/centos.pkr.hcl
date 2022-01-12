packer {
  required_plugins {
    googlecompute = {
      version = ">= 0.0.1"
      source = "github.com/hashicorp/googlecompute"
    }
  }
}

locals {
  timestamp = "${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
}

variable "cb_version" {
  description = "Software version"
  type        = string
}

variable "os_linux_type" {
  description = "Linux type"
  type        = string
}

variable "os_linux_release" {
  description = "Linux release"
  type        = string
}

variable "gcp_account_file" {
  description = "GCP auth JSON"
  type        = string
}

variable "gcp_image_name" {
  description = "GCP image"
  type        = string
}

variable "gcp_image_family" {
  description = "GCP image family"
  type        = string
}

variable "gcp_project" {
  description = "GCP project"
  type        = string
}

variable "gcp_image_user" {
  description = "Image SSH user"
  type        = string
}

variable "gcp_zone" {
  description = "GCP zone"
  type        = string
}

source "googlecompute" "cb-node" {
  account_file        = var.gcp_account_file
  project_id          = var.gcp_project
  source_image        = var.gcp_image_name
  source_image_family = var.gcp_image_family
  zone                = var.gcp_zone
  disk_size           = 50
  machine_type        = "n1-standard-2"
  communicator        = "ssh"
  ssh_username        = var.gcp_image_user
  ssh_timeout         = "1h"
}

build {
  name    = "centos-couchbase-ami"
  sources = [
    "source.googlecompute.cb-node"
  ]
  provisioner "shell" {
  environment_vars = [
    "SW_VERSION=${var.cb_version}",
  ]
  inline = [
    "echo Installing Couchbase",
    "sleep 30",
    "sudo yum update -y",
    "sudo yum install -y git",
    "sudo git clone https://github.com/mminichino/hostprep /usr/local/hostprep",
    "sudo /usr/local/hostprep/bin/hostprep.sh -t couchbase -v ${var.cb_version}",
  ]
  }
}