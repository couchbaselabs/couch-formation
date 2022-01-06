packer {
  required_plugins {
    amazon = {
      version = ">= 1.0.3"
      source  = "github.com/hashicorp/vmware"
    }
  }
}

locals {
  timestamp = "${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
}

variable "cb_version" {
  description = "Software version"
  type        = string
}

variable "os_linux_type" {
  description = "Linux type"
  type        = string
}

variable "os_linux_release" {
  description = "Linux release"
  type        = string
}

variable "vsphere_cluster" {
  description = "AWS image"
  type        = string
}

variable "vm_cpu_cores" {
  description = "AMI owner"
  type        = string
}

variable "vsphere_datacenter" {
  description = "AMI SSH user"
  type        = string
}

variable "vsphere_folder" {
  description = "AWS region"
  type        = string
}

variable "vm_guest_os_keyboard" {
  description = "AWS region"
  type        = string
}

variable "vsphere_password" {
  description = "AWS region"
  type        = string
}

variable "build_username" {
  description = "AWS region"
  type        = string
}

variable "vm_guest_os_timezone" {
  description = "AWS region"
  type        = string
}

variable "build_key" {
  description = "AWS region"
  type        = string
}

variable "build_password" {
  description = "AWS region"
  type        = string
}

variable "vsphere_datastore" {
  description = "AWS region"
  type        = string
}

variable "vm_mem_size" {
  description = "AWS region"
  type        = string
}

variable "vm_guest_os_type" {
  description = "AWS region"
  type        = string
}

variable "vm_disk_size" {
  description = "AWS region"
  type        = string
}

variable "iso_url" {
  description = "AWS region"
  type        = string
}

variable "iso_checksum" {
  description = "AWS region"
  type        = string
}

variable "sw_url" {
  description = "AWS region"
  type        = string
}

variable "vsphere_hostname" {
  description = "AWS region"
  type        = string
}

variable "vsphere_username" {
  description = "AWS region"
  type        = string
}

variable "vsphere_network" {
  description = "AWS region"
  type        = string
}

variable "build_password_encrypted" {
  description = "AWS region"
  type        = string
}

variable "vm_guest_os_language" {
  description = "AWS region"
  type        = string
}

source "vsphere-iso" "cb-node" {
  vcenter_server       = var.vsphere_hostname
  username             = var.vsphere_username
  password             = var.vsphere_password
  insecure_connection  = true
  datacenter           = var.vsphere_datacenter
  cluster              = var.vsphere_cluster
  datastore            = var.vsphere_datastore
  folder               = var.vsphere_folder
  guest_os_type        = var.vm_guest_os_type
  vm_name              = "couchbase-template-linux-centos"
  firmware             = "bios"
  CPUs                 = 1
  cpu_cores            = var.vm_cpu_cores
  CPU_hot_plug         = false
  RAM                  = var.vm_mem_size
  RAM_hot_plug         = false
  cdrom_type           = "sata"
  disk_controller_type = ["pvscsi"]
  storage {
    disk_size             = var.vm_disk_size
    disk_thin_provisioned = true
  }
  network_adapters {
    network      = var.vsphere_network
    network_card = "vmxnet3"
  }
  vm_version           = 14
  remove_cdrom         = true
  tools_upgrade_policy = true
  notes                = "Built by HashiCorp Packer on ${local.timestamp}."
  #iso_paths           = ["[${var.vsphere_iso_datastore}] ${var.vsphere_iso_path}/${var.iso_file}"]
  #iso_checksum        = "${var.vsphere_iso_hash}:${var.iso_checksum}"
  iso_url              = var.iso_url
  iso_checksum         = var.iso_checksum
  http_port_min        = 8000
  http_port_max        = 8099
  http_content = {
    "/ks.cfg" = templatefile("ks-cfg.pkrtpl.hcl", { build_username = var.build_username, build_password_encrypted = var.build_password_encrypted, vm_guest_os_language = var.vm_guest_os_language, vm_guest_os_keyboard = var.vm_guest_os_keyboard, vm_guest_os_timezone = var.vm_guest_os_timezone, build_key = var.build_key, sw_url = var.sw_url })
  }
  boot_order          = "disk,cdrom"
  boot_wait           = "5s"
  boot_command        = ["<up><wait><tab><wait> ", " inst.text ", "inst.ks=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ks.cfg ", "<enter><wait>"]
  ip_wait_timeout     = "20m"
  shutdown_command    = "echo '${var.build_password}' | sudo -S -E shutdown -P now"
  shutdown_timeout    = "15m"
  communicator        = "ssh"
  ssh_username        = var.build_username
  ssh_password        = var.build_password
  ssh_port            = 22
  ssh_timeout         = "30m"
  convert_to_template = true
}

build {
  sources = [
    "source.vsphere-iso.cb-node"
  ]
  provisioner "shell" {
    environment_vars = [
      "SW_VERSION=${var.cb_version}",
  ]
  inline = [
    "echo Installing Couchbase",
    "sleep 30",
    "sudo yum update -y",
    "sudo yum install -y git",
    "sudo git clone https://github.com/mminichino/hostprep /usr/local/hostprep",
    "sudo /usr/local/hostprep/bin/hostprep.sh -t couchbase -v ${var.cb_version}",
  ]
  }
}
