terraform {
  required_providers {
    aws = {
      source  = "hashicorp/google"
    }
  }
}

provider "google" {
 credentials = file(var.gcp_account_file)
 project     = var.gcp_project
 region      = var.gcp_region
}

data "google_compute_image" "node_image" {
  name  = var.gcp_market_image
  project = var.gcp_image_project
}

resource "google_compute_instance" "standalone_nodes" {
  for_each     = var.node_spec
  name         = each.key
  machine_type = var.gcp_machine_type
  zone         = each.value.node_zone
  project      = var.gcp_project

  boot_disk {
    initialize_params {
      size  = var.gcp_disk_size
      type  = var.gcp_disk_type
      image = data.google_compute_image.node_image.self_link
    }
  }

  network_interface {
    subnetwork         = each.value.node_subnet
    subnetwork_project = var.gcp_project
    dynamic "access_config" {
      for_each = var.use_public_ip ? ["pub-ip"] : []
      content {}
    }
  }

  metadata = {
    ssh-keys = "admin:${file(var.ssh_public_key_file)}"
  }

  service_account {
    email  = var.gcp_service_account_email
    scopes = ["cloud-platform"]
  }
}

output "node-public" {
  value = var.use_public_ip ? [
    for instance in google_compute_instance.standalone_nodes:
    instance.network_interface.0.access_config.0.nat_ip
  ] : null
}

output "node-private" {
  value = [
    for instance in google_compute_instance.standalone_nodes:
    instance.network_interface.0.network_ip
  ]
}
