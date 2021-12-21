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

resource "aws_instance" "couchbase_nodes" {
  for_each               = var.cluster_spec
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.ssh_key
  vpc_security_group_ids = var.security_group_ids
  subnet_id              = var.subnet_id

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = var.root_volume_type
    iops        = var.root_volume_iops
  }

  tags = {
    Name = "${each.key}-${random_id.labid.hex}"
    Role = "${each.value.node_role}"
    Services = "${each.value.node_services}"
    LabName = "lab-${random_id.labid.hex}"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /home/${var.ssh_user}/callhostprep.sh",
      "/home/${var.ssh_user}/callhostprep.sh -t cbnode -h ${each.key}-${random_id.labid.hex} -d ${var.domain_name} -n ${var.dns_server} -v ${var.sw_version}",
    ]
    connection {
      host        = self.private_ip
      type        = "ssh"
      user        = var.ssh_user
      private_key = file(var.ssh_private_key)
    }
  }
}
