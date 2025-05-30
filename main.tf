 terraform {
   required_providers {
     yandex = {
       source = "yandex-cloud/yandex"
     }
   }
 }
  
 provider "yandex" {
   token  =  "y0__xC4urj8BxjB3RMgy4q7yBJbf6lwNc7oZxwMnq6RnXkp7vyPcw"
   cloud_id  = "b1gqhucdh9p1pqsm6msu"
   folder_id = "b1g4dpa5tn0o1dpo3411"
   zone      = "ru-central1-a"
 }


resource "yandex_iam_service_account" "stock_exchange_sa" {
  name        = "stock-exchange"
  description = "Service account for stock exchange project"
}

resource "yandex_iam_service_account_iam_binding" "sa_admin" {
  service_account_id = yandex_iam_service_account.stock_exchange_sa.id
  role               = "admin"
  members            = ["serviceAccount:${yandex_iam_service_account.stock_exchange_sa.id}"]
}

resource "yandex_vpc_network" "stock_exchange_network" {
  name = "stock-exchange-network"
}

resource "yandex_vpc_subnet" "subnet_a" {
  name           = "subnet-a"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.stock_exchange_network.id
  v4_cidr_blocks = ["10.128.0.0/24"]
}

resource "yandex_vpc_subnet" "subnet_b" {
  name           = "subnet-b"
  zone           = "ru-central1-b"
  network_id     = yandex_vpc_network.stock_exchange_network.id
  v4_cidr_blocks = ["10.129.0.0/24"]
}


resource "yandex_compute_instance" "vm1" {
  name        = "stock-exchanhe-machine-1"
  platform_id = "standard-v1"
  zone        = "ru-central1-a"
  service_account_id = yandex_iam_service_account.stock_exchange_sa.id

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = "fd8h44erh1t7gptj7p6e"
      size     = 10
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet_a.id
    nat       = true
  }

  metadata = {
    user-data = data.local_file.start_script.content
  }
}

resource "yandex_compute_instance" "vm2" {
  name        = "stock-exchanhe-machine-2"
  platform_id = "standard-v1"
  zone        = "ru-central1-a"
  service_account_id = yandex_iam_service_account.stock_exchange_sa.id

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = "fd8h44erh1t7gptj7p6e" 
      size     = 10
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet_b.id
    nat       = true
  }

  metadata = {
    user-data = data.local_file.start_script.content
  }
}

resource "yandex_lb_target_group" "stock_exchange_group" {
  name = "stock-exchange-group"

  description = "Target group for stock exchange VMs"

  labels = {
    project = "stock-exchange"
  }

  targets {
    subnet_id = yandex_vpc_subnet.subnet_a.id
    address   = yandex_compute_instance.vm1.network_interface[0].ip_address
    port      = 80
  }

  targets {
    subnet_id = yandex_vpc_subnet.subnet_b.id
    address   = yandex_compute_instance.vm2.network_interface[0].ip_address
    port      = 80
  }
}

resource "yandex_lb_network_load_balancer" "stock_exchange_balancer" {
  name = "stock-exchange-balancer"

  listener {
    name     = "http"
    port     = 80
    protocol = "TCP"
  }

  target_group_ids = [yandex_lb_target_group.stock_exchange_group.id]

  network_id = yandex_vpc_network.stock_exchange_network.id
}

resource "yandex_mdb_postgresql_cluster" "pg_cluster" {
  name        = "postgresql-stock-exchange"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.stock_exchange_network.id
  version     = "15"

  config {
    version = "15"

    postgresql_config = {
      max_connections           = 100
      password_encryption_type = "MD5"
    }

    resources {
      resource_preset_id = "s3-c2-m8"
      disk_type_id       = "network-ssd"
      disk_size          = 10
    }

    backup_window_start {
      hours   = 22
      minutes = 0
    }
  }

  maintenance_window {
    type = "ANYTIME"
  }

  host {
    zone      = "ru-central1-a"
    subnet_id = yandex_vpc_subnet.subnet_a.id
  }

  host {
    zone      = "ru-central1-b"
    subnet_id = yandex_vpc_subnet.subnet_b.id
  }

  database {
    name = "market_check"
  }

  user {
    name     = "alekron"
    password = "zxcvb55bvcxz"
    permission {
      database_name = "market_check"
    }
  }

  deletion_protection = false
}

resource "yandex_storage_bucket" "archive_bucket" {
  name     = "stock-exchange-archive"
  access_key = ""
  secret_key = ""
}

resource "yandex_storage_bucket" "www_bucket" {
  name     = "www.stock-exchange"
  acl      = "public-read"
}

resource "yandex_container_registry" "registry" {
  name = "stock-exchange-registry"
}