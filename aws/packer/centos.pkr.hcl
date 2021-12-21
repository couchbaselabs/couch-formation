packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

source "amazon-ebs" "centos-latest" {
  ami_name      = "centos-8-latest"
  instance_type = "c5.large"
  region        = "us-west-2"
  source_ami_filter {
    filters = {
      name                = "CentOS 8.4.2105 x86_64"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["125523088429"]
  }
  ssh_username = "centos"
}

build {
  name    = "centos-couchbase-ami"
  sources = [
    "source.amazon-ebs.centos-latest"
  ]
  provisioner "shell" {
  environment_vars = [
    "VERSION=7.0.3-7031",
  ]
  inline = [
    "echo Installing Redis",
    "sleep 30",
    "sudo apt-get update",
    "sudo apt-get install -y redis-server",
    "echo \"FOO is $FOO\" > example.txt",
  ]
  }
}
