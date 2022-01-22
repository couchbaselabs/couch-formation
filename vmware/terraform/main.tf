##

provider "vsphere" {
  user           = var.vsphere_user
  password       = var.vsphere_password
  vsphere_server = var.vsphere_server
  allow_unverified_ssl = true
}

data "vsphere_datacenter" "dc" {
  name = var.vsphere_datacenter
}

data "vsphere_resource_pool" "pool" {
  name          = "${var.vsphere_cluster}/Resources"
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "datastore" {
  name          = var.vsphere_datastore
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_distributed_virtual_switch" "dvs" {
  name          = var.vsphere_dvs_switch
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "network" {
  name          = var.vsphere_network
  datacenter_id = data.vsphere_datacenter.dc.id
  distributed_virtual_switch_uuid = data.vsphere_distributed_virtual_switch.dvs.id
}

data "vsphere_virtual_machine" "template" {
  name          = var.vsphere_template
  datacenter_id = data.vsphere_datacenter.dc.id
}

resource "vsphere_tag_category" "couchbase" {
  name        = var.vsphere_folder
  cardinality = "MULTIPLE"
  description = "Managed by Terraform"

  associable_types = [
    "VirtualMachine",
  ]
}

resource "vsphere_tag" "couchbase" {
  for_each    = var.cluster_spec
  name        = "${each.key}"
  category_id = vsphere_tag_category.couchbase.id
  description = "couchbase-server"
}

resource "vsphere_folder" "folder" {
  path          = var.vsphere_folder
  type          = "vm"
  datacenter_id = data.vsphere_datacenter.dc.id
}

resource "vsphere_virtual_machine" "couchbase_nodes" {
  for_each         = var.cluster_spec
  name             = each.key
  num_cpus         = var.vm_cpu_cores
  memory           = var.vm_mem_size
  datastore_id     = data.vsphere_datastore.datastore.id
  resource_pool_id = data.vsphere_resource_pool.pool.id
  guest_id         = data.vsphere_virtual_machine.template.guest_id
  scsi_type        = data.vsphere_virtual_machine.template.scsi_type
  folder           = vsphere_folder.folder.path

  network_interface {
    network_id = data.vsphere_network.network.id
  }

  disk {
    label = "disk0"
    size = data.vsphere_virtual_machine.template.disks.0.size
    thin_provisioned = data.vsphere_virtual_machine.template.disks.0.thin_provisioned
  }

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id

    customize {
      linux_options {
        host_name = each.key
        domain    = var.domain_name
      }
      network_interface {
        ipv4_address = each.value.node_ip_address
        ipv4_netmask = each.value.node_netmask
      }
      ipv4_gateway = each.value.node_gateway
      dns_server_list = var.dns_server_list
      dns_suffix_list = var.dns_domain_list
    }
  }

  tags = ["${vsphere_tag.couchbase[each.key].id}"]

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${each.value.node_ip_address} -s ${each.value.node_services} -o ${var.index_memory}",
    ]
    connection {
      host        = each.value.node_ip_address
      type        = "ssh"
      user        = var.ssh_user
      private_key = file(var.ssh_private_key)
    }
  }
}

locals {
  rally_node = element([for node in vsphere_virtual_machine.couchbase_nodes: node.default_ip_address], 0)
  depends_on = [vsphere_virtual_machine.couchbase_nodes]
}

resource "time_sleep" "pause" {
  depends_on = [vsphere_virtual_machine.couchbase_nodes]
  create_duration = "5s"
}

resource "null_resource" "couchbase-init" {
  for_each = vsphere_virtual_machine.couchbase_nodes
  triggers = {
    cb_nodes = join(",", keys(vsphere_virtual_machine.couchbase_nodes))
  }
  connection {
    host        = each.value.default_ip_address
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node}",
    ]
  }
  depends_on = [vsphere_virtual_machine.couchbase_nodes, time_sleep.pause]
}

resource "null_resource" "couchbase-rebalance" {
  triggers = {
    cb_nodes = join(",", keys(vsphere_virtual_machine.couchbase_nodes))
  }
  connection {
    host        = local.rally_node
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m rebalance -r ${local.rally_node}",
    ]
  }
  depends_on = [null_resource.couchbase-init]
}
