##

variable "region_name" {
  description = "Region name"
  default     = "us-central1"
  type        = string
}

variable "cf_gcp_project" {
  description = "The GCP project"
  default     = "couchbase-se-central-us"
  type        = string
}

variable "cf_gcp_account_file" {
  description = "The auth JSON"
  default     = "/Users/michaelminichino/.config/gcloud/couchbase-se-central-us-e3b50e2b4bad.json"
  type        = string
}

variable "cf_env_name" {
  description = "Couchbase cluster name"
  default     = "dev10db"
  type        = string
}

variable "cf_vpc_cidr" {
  description = "Couchbase cluster name"
  default     = "10.99.0.0/16"
  type        = string
}

variable "cf_subnet_cidr_1" {
  description = "Couchbase cluster name"
  default     = "10.99.1.0/24"
  type        = string
}

provider "google" {
 credentials = file(var.cf_gcp_account_file)
 project     = var.cf_gcp_project
 region      = var.region_name
}

resource "google_compute_network" "cf_vpc" {
  name = "${var.cf_env_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "cf_subnet_1" {
  name          = "${var.cf_env_name}-subnet-1"
  ip_cidr_range = var.cf_subnet_cidr_1
  region        = var.region_name
  network       = google_compute_network.cf_vpc.id
}

resource "google_compute_firewall" "cf_fw_vpc" {
  name    = "${var.cf_env_name}-fw-vpc"
  network = google_compute_network.cf_vpc.name

  allow {
    protocol = "all"
  }

  source_ranges = [var.cf_vpc_cidr]
}

resource "google_compute_firewall" "cf_fw_ssh" {
  name    = "${var.cf_env_name}-fw-ssh"
  network = google_compute_network.cf_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "cf_fw_cb" {
  name    = "${var.cf_env_name}-fw-cb"
  network = google_compute_network.cf_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8091-8097", "9123", "9140", "11210", "11280", "11207", "18091-18097", "4984-4986"]
  }

  source_ranges = ["0.0.0.0/0"]
}
