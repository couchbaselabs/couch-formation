provider "azurerm" {
   features {}
}

variable "region_name" {
  description = "Azure Location"
  default     = "centralus"
  type        = string
}

variable "cf_env_name" {
  description = "Environment Name"
  default     = "dev10db"
  type        = string
}

variable "cf_vpc_cidr" {
  description = "Azure Virtual Network"
  default     = "10.99.0.0/16"
  type        = string
}

variable "cf_subnet_cidr_1" {
  description = "Azure Subnet"
  default     = "10.99.1.0/24"
  type        = string
}

resource "azurerm_resource_group" "cf_rg" {
  name     = "${var.cf_env_name}-rg"
  location = var.region_name
}

resource "azurerm_network_security_group" "cf_nsg" {
  name                = "${var.cf_env_name}-nsg"
  location            = azurerm_resource_group.cf_rg.location
  resource_group_name = azurerm_resource_group.cf_rg.name

  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["22"]
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowCB"
    priority                   = 101
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["8091-8097", "9123", "9140", "11210", "11280", "11207", "18091-18097", "4984-4986"]
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    name = "${var.cf_env_name}-nsg"
    environment = var.cf_env_name
  }
}

resource "azurerm_virtual_network" "cf_vpc" {
  name                = "${var.cf_env_name}-vpc"
  location            = azurerm_resource_group.cf_rg.location
  resource_group_name = azurerm_resource_group.cf_rg.name
  address_space       = [var.cf_vpc_cidr]

  subnet {
    name           = "${var.cf_env_name}-subnet-1"
    address_prefix = var.cf_subnet_cidr_1
    security_group = azurerm_network_security_group.cf_nsg.id
  }

  tags = {
    name = "${var.cf_env_name}-vpc"
    environment = var.cf_env_name
  }
}
