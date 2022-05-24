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

resource "random_id" "cluster-id" {
  byte_length = 4
}

data "google_compute_image" "cb_image" {
  name  = var.gcp_cb_image
  project = var.gcp_project
}

resource "google_compute_instance" "sgw_nodes" {
  for_each     = var.sgw_spec
  name         = each.key
  machine_type = var.gcp_machine_type
  zone         = each.value.node_zone
  project      = var.gcp_project

  boot_disk {
   initialize_params {
     size = var.gcp_disk_size
     type = var.gcp_disk_type
     image = data.google_compute_image.cb_image.self_link
   }
  }

  network_interface {
    subnetwork = each.value.node_subnet
    subnetwork_project = var.gcp_project
    dynamic "access_config" {
    for_each = var.use_public_ip ? ["pub-ip"] : []
    content {}
  }
  }

  metadata = {
   ssh-keys = "${var.os_image_user}:${file(var.ssh_public_key_file)}"
 }

  service_account {
    email = var.gcp_service_account_email
    scopes = ["cloud-platform"]
  }

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/hostprep.sh -t sgw",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m sgw -r ${var.cb_node_1}",
    ]
    connection {
      host        = var.use_public_ip ? self.network_interface.0.access_config.0.nat_ip : self.network_interface.0.network_ip
      type        = "ssh"
      user        = var.os_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}
