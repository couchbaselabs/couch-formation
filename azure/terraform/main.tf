terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
   features {}
}

resource "random_id" "cluster-id" {
  byte_length = 4
}

data "azurerm_subnet" "cb_subnet" {
  for_each             = var.cluster_spec
  name                 = each.value.node_subnet
  virtual_network_name = var.azure_vnet
  resource_group_name  = var.azure_resource_group
}

resource "azurerm_public_ip" "node_external" {
  for_each            = {
    for k, v in var.cluster_spec : k => v
    if var.use_public_ip
  }
  name                = "${each.key}-pub"
  resource_group_name = var.azure_resource_group
  location            = var.azure_location
  zones               = [each.value.node_zone]
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "node_nic" {
  for_each            = var.cluster_spec
  name                = "${each.key}-nic"
  location            = var.azure_location
  resource_group_name = var.azure_resource_group

  ip_configuration {
    name                          = "internal"
    subnet_id                     = data.azurerm_subnet.cb_subnet[each.key].id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = var.use_public_ip ? azurerm_public_ip.node_external[each.key].id : null
  }
}

data "azurerm_network_security_group" "cluster_nsg" {
  name                = var.azure_nsg
  resource_group_name = var.azure_resource_group
}

resource "azurerm_network_interface_security_group_association" "node_nsg" {
  for_each                  = var.cluster_spec
  network_interface_id      = azurerm_network_interface.node_nic[each.key].id
  network_security_group_id = data.azurerm_network_security_group.cluster_nsg.id
}

data "azurerm_image" "cb_image" {
  name                = var.azure_image_name
  resource_group_name = var.azure_resource_group
}

resource "azurerm_managed_disk" "swap_disk" {
  for_each             = var.cluster_spec
  name                 = "${each.key}-swap"
  location             = var.azure_location
  zone                 = each.value.node_zone
  resource_group_name  = var.azure_resource_group
  storage_account_type = var.azure_disk_type
  create_option        = "Empty"
  disk_size_gb         = each.value.node_ram
}

resource "azurerm_virtual_machine_data_disk_attachment" "swap_disk" {
  for_each           = var.cluster_spec
  managed_disk_id    = azurerm_managed_disk.swap_disk[each.key].id
  virtual_machine_id = azurerm_linux_virtual_machine.couchbase_nodes[each.key].id
  lun                = "0"
  caching            = "ReadWrite"
}

resource "azurerm_linux_virtual_machine" "couchbase_nodes" {
  for_each              = var.cluster_spec
  name                  = each.key
  size                  = var.azure_machine_type
  location              = var.azure_location
  zone                  = each.value.node_zone
  resource_group_name   = var.azure_resource_group
  source_image_id       = data.azurerm_image.cb_image.id
  admin_username        = var.os_image_user
  network_interface_ids = [
    azurerm_network_interface.node_nic[each.key].id,
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.azure_disk_type
    disk_size_gb         = var.azure_disk_size
  }

  admin_ssh_key {
    username   = var.os_image_user
    public_key = file(var.ssh_public_key_file)
  }

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/configure-swap.sh -o ${each.value.node_swap} -d /dev/sdb",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${self.private_ip_address} -e ${var.use_public_ip ? self.public_ip_address : "none"} -s ${each.value.node_services} -o ${var.index_memory} -g zone${each.value.node_zone}",
    ]
    connection {
      host        = var.use_public_ip ? self.public_ip_address : self.private_ip_address
      type        = "ssh"
      user        = var.os_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}

locals {
  rally_node = element([for node in azurerm_linux_virtual_machine.couchbase_nodes: node.private_ip_address], 0)
  rally_node_public = element([for node in azurerm_linux_virtual_machine.couchbase_nodes: node.public_ip_address], 0)
  cluster_init_name = var.cb_cluster_name != null ? var.cb_cluster_name : "cbdb"
}

resource "time_sleep" "pause" {
  depends_on = [azurerm_linux_virtual_machine.couchbase_nodes]
  create_duration = "5s"
}

resource "null_resource" "couchbase-init" {
  for_each = azurerm_linux_virtual_machine.couchbase_nodes
  triggers = {
    cb_nodes = join(",", keys(azurerm_linux_virtual_machine.couchbase_nodes))
  }
  connection {
    host        = var.use_public_ip ? each.value.public_ip_address : each.value.private_ip_address
    type        = "ssh"
    user        = var.os_image_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node} -n ${local.cluster_init_name}",
    ]
  }
  depends_on = [azurerm_linux_virtual_machine.couchbase_nodes, time_sleep.pause]
}

resource "null_resource" "couchbase-rebalance" {
  triggers = {
    cb_nodes = join(",", keys(azurerm_linux_virtual_machine.couchbase_nodes))
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
