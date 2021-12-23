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
    Name = "${each.key}"
    Services = "${each.value.node_services}"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${self.private_ip} -e ${self.public_ip} -s ${each.value.node_services} -o ${var.index_memory}",
    ]
    connection {
      host        = self.private_ip
      type        = "ssh"
      user        = var.ssh_user
      private_key = file(var.ssh_private_key)
    }
  }
}

resource "null_resource" "couchbase-init" {
  for_each = aws_instance.couchbase_nodes
  triggers = {
    cb_nodes = join(",", keys(aws_instance.couchbase_nodes))
  }
  connection {
    host        = each.value.private_ip
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m debug -r ${element([for node in aws_instance.couchbase_nodes: node.private_ip], 0)}",
    ]
  }
  depends_on = [aws_instance.couchbase_nodes]
}
