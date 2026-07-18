variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }

resource "google_sql_database_instance" "aerogrid" {
  name             = "aerogrid-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled          = true
      start_time       = "03:00"
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/${var.project_id}/global/networks/default"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }
}

resource "google_sql_database" "aerogrid" {
  name     = "aerogrid"
  instance = google_sql_database_instance.aerogrid.name
}

resource "google_sql_user" "aerogrid" {
  name     = "aerogrid"
  instance = google_sql_database_instance.aerogrid.name
  password = google_secret_manager_secret_version.db_password.secret_data
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "aerogrid-db-password-${var.environment}"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret = google_secret_manager_secret.db_password.id
  secret_data = random_password.db.result
}

resource "random_password" "db" {
  length  = 32
  special = false
}

output "connection_name" { value = google_sql_database_instance.aerogrid.connection_name }
output "connection_url" {
  value     = "postgresql+asyncpg://${google_sql_user.aerogrid.name}:${google_secret_manager_secret_version.db_password.secret_data}@/${google_sql_database.aerogrid.name}?host=/cloudsql/${google_sql_database_instance.aerogrid.connection_name}"
  sensitive = true
}
