packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

source "amazon-ebs" "cb-node" {
  ami_name      = "${var.os_linux_type}-ami"
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
}

build {
  name    = "${var.os_linux_type}-${var.os_linux_release}-couchbase-ami"
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
    "sudo apt-get update",
    "sudo apt-get install -y couchbase-server",
  ]
  }
}
