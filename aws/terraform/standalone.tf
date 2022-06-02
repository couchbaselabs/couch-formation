terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region = var.region_name
}

resource "aws_instance" "standalone_nodes" {
  for_each               = var.node_spec
  ami                    = var.aws_market_name
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
}

output "node-public" {
  value = var.use_public_ip ? [
    for instance in aws_instance.standalone_nodes:
    instance.public_ip
  ] : null
}

output "node-private" {
  value = [
    for instance in aws_instance.standalone_nodes:
    instance.private_ip
  ]
}
