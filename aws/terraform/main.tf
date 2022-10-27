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

resource "random_id" "cluster-id" {
  byte_length = 4
}

resource "aws_instance" "couchbase_nodes" {
  for_each               = var.cluster_spec
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

  ebs_block_device {
    device_name = "/dev/xvdb"
    volume_size = "32"
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
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${self.private_ip} -e ${var.use_public_ip ? self.public_ip : "none"} -s ${each.value.node_services} -o ${var.index_memory} -g ${each.value.node_zone}",
    ]
    connection {
      host        = var.use_public_ip ? self.public_ip : self.private_ip
      type        = "ssh"
      user        = var.os_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}

locals {
  rally_node = element([for node in aws_instance.couchbase_nodes: node.private_ip], 0)
  rally_node_public = element([for node in aws_instance.couchbase_nodes: node.public_ip], 0)
  cluster_init_name = var.cb_cluster_name != null ? var.cb_cluster_name : "cbdb"
}

resource "time_sleep" "pause" {
  depends_on = [aws_instance.couchbase_nodes]
  create_duration = "5s"
}

resource "null_resource" "couchbase-init" {
  for_each = aws_instance.couchbase_nodes
  triggers = {
    cb_nodes = join(",", keys(aws_instance.couchbase_nodes))
  }
  connection {
    host        = var.use_public_ip ? each.value.public_ip : each.value.private_ip
    type        = "ssh"
    user        = var.os_image_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node} -n ${local.cluster_init_name}",
    ]
  }
  depends_on = [aws_instance.couchbase_nodes, time_sleep.pause]
}

resource "null_resource" "couchbase-rebalance" {
  triggers = {
    cb_nodes = join(",", keys(aws_instance.couchbase_nodes))
  }
  connection {
    host        = var.use_public_ip ? local.rally_node_public : local.rally_node
    type        = "ssh"
    user        = var.os_image_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m rebalance -r ${local.rally_node}",
    ]
  }
  depends_on = [null_resource.couchbase-init]
}
