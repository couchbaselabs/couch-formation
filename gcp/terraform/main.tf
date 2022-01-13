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
}

resource "google_compute_instance" "couchbase_nodes" {
  for_each     = var.cluster_spec
  name         = each.key
  machine_type = var.gcp_machine_type
  zone         = var.gcp_zone

  boot_disk {
   initialize_params {
     size = var.gcp_disk_size
     type = var.gcp_disk_type
     image = data.google_compute_image.cb_image.self_link
   }
  }

  network_interface {
    subnetwork = var.gcp_subnet
    access_config {
   }
  }

  metadata = {
   ssh-keys = "${var.gcp_image_user}:${file(var.ssh_public_key_file)}"
 }

  service_account {
    scopes = ["cloud-platform"]
  }

  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/refresh.sh",
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m write -i ${self.network_interface.0.network_ip} -e ${self.network_interface.0.access_config.0.nat_ip} -s ${each.value.node_services} -o ${var.index_memory}",
    ]
    connection {
      host        = self.network_interface.0.network_ip
      type        = "ssh"
      user        = var.gcp_image_user
      private_key = file(var.ssh_private_key)
    }
  }
}

locals {
  rally_node = element([for node in google_compute_instance.couchbase_nodes: node.network_interface.0.network_ip], 0)
}

resource "null_resource" "couchbase-init" {
  for_each = google_compute_instance.couchbase_nodes
  triggers = {
    cb_nodes = join(",", keys(google_compute_instance.couchbase_nodes))
  }
  connection {
    host        = each.value.network_interface.0.network_ip
    type        = "ssh"
    user        = var.gcp_image_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m config -r ${local.rally_node}",
    ]
  }
  depends_on = [google_compute_instance.couchbase_nodes]
}

resource "null_resource" "couchbase-rebalance" {
  triggers = {
    cb_nodes = join(",", keys(google_compute_instance.couchbase_nodes))
  }
  connection {
    host        = local.rally_node
    type        = "ssh"
    user        = var.gcp_image_user
    private_key = file(var.ssh_private_key)
  }
  provisioner "remote-exec" {
    inline = [
      "sudo /usr/local/hostprep/bin/clusterinit.sh -m rebalance -r ${local.rally_node}",
    ]
  }
  depends_on = [null_resource.couchbase-init]
}
