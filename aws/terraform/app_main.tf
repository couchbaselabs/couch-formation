terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  region = var.region_name
}

resource "random_id" "cluster-id" {
  byte_length = 4
}

resource "aws_instance" "app_nodes" {
  for_each               = var.app_spec
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.ssh_key
  vpc_security_group_ids = var.security_group_ids
  subnet_id              = each.value.node_subnet
  availability_zone      = each.value.node_zone

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = var.root_volume_type
    iops        = var.root_volume_iops
  }

  tags = {
    Name = "${each.key}"
    Services = "${each.value.node_services}"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/hostprep.sh -t sdk",
    ]
    connection {
      host        = var.use_public_ip ? self.public_ip : self.private_ip
      type        = "ssh"
      user        = var.os_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}
