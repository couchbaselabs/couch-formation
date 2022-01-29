packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
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

variable "aws_image_name" {
  description = "AWS image"
  type        = string
}

variable "aws_image_owner" {
  description = "AMI owner"
  type        = string
}

variable "aws_image_user" {
  description = "AMI SSH user"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

source "amazon-ebs" "cb-node" {
  ami_name      = "${var.os_linux_type}-${var.os_linux_release}-couchbase-${local.timestamp}"
  instance_type = "c5.large"
  region        = "${var.aws_region}"
  source_ami_filter {
    filters = {
      name                = "${var.aws_image_name}"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["${var.aws_image_owner}"]
  }
  ssh_username = "${var.aws_image_user}"
  tags = {
    Name    = "${var.os_linux_type}-${var.os_linux_release}-${var.cb_version}"
    Type    = "${var.os_linux_type}"
    Release = "${var.os_linux_release}"
    Version = "${var.cb_version}"
  }
}

build {
  name    = "centos-couchbase-ami"
  sources = [
    "source.amazon-ebs.cb-node"
  ]
  provisioner "shell" {
  environment_vars = [
    "SW_VERSION=${var.cb_version}",
  ]
  inline = [
    "echo Installing Couchbase",
    "sleep 30",
    "curl -sfL https://raw.githubusercontent.com/mminichino/hostprep/main/bin/bootstrap.sh | sudo -E bash -",
    "sudo git clone https://github.com/mminichino/hostprep /usr/local/hostprep",
    "sudo /usr/local/hostprep/bin/hostprep.sh -t couchbase -v ${var.cb_version}",
  ]
  }
}
