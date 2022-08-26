terraform {
  required_providers {
    couchbasecapella = {
      source  = "terraform.couchbase.com/local/couchbasecapella"
      version = "1.0.0"
    }
  }
}

provider "couchbasecapella" {}

resource "couchbasecapella_project" "project" {
  name = var.project_name
}

resource "couchbasecapella_hosted_cluster" "cluster" {
  name        = var.cluster_name
  project_id  = couchbasecapella_project.project.id
  place {
    single_az = var.single_az
    hosted {
      provider = var.provider
      region   = var.region
      cidr     = var.cidr
    }
  }
  support_package {
    timezone = "GMT"
    support_package_type     = var.support_package
  }
  servers {
    size     = var.cluster_size
    compute  = var.machine_type
    services = [var.services]
    storage {
      storage_type = var.root_volume_type
      iops = var.root_volume_iops
      storage_size = var.root_volume_size
    }
  }
}
