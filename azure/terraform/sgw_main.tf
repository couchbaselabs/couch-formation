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

data "azurerm_subnet" "app_subnet" {
  for_each             = var.sgw_spec
  name                 = each.value.node_subnet
  virtual_network_name = var.azure_vnet
  resource_group_name  = var.azure_resource_group
}

resource "azurerm_public_ip" "node_external" {
  for_each            = {
    for k, v in var.sgw_spec : k => v
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
  for_each            = var.sgw_spec
  name                = "${each.key}-nic"
  location            = var.azure_location
  resource_group_name = var.azure_resource_group

  ip_configuration {
    name                          = "internal"
    subnet_id                     = data.azurerm_subnet.app_subnet[each.key].id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = var.use_public_ip ? azurerm_public_ip.node_external[each.key].id : null
  }
}

data "azurerm_network_security_group" "app_nsg" {
  name                = var.azure_nsg
  resource_group_name = var.azure_resource_group
}

resource "azurerm_network_interface_security_group_association" "node_nsg" {
  for_each                  = var.sgw_spec
  network_interface_id      = azurerm_network_interface.node_nic[each.key].id
  network_security_group_id = data.azurerm_network_security_group.app_nsg.id
}

data "azurerm_image" "app_image" {
  name                = var.azure_image_name
  resource_group_name = var.azure_resource_group
}

resource "azurerm_linux_virtual_machine" "sgw_nodes" {
  for_each              = var.sgw_spec
  name                  = each.key
  size                  = var.azure_machine_type
  location              = var.azure_location
  zone                  = each.value.node_zone
  resource_group_name   = var.azure_resource_group
  source_image_id       = data.azurerm_image.app_image.id
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
      "sudo /usr/local/hostprep/bin/hostprep.sh -t sgw",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m sgw -r ${var.cb_node_1}",
    ]
    connection {
      host        = var.use_public_ip ? self.public_ip_address : self.private_ip_address
      type        = "ssh"
      user        = var.os_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}
