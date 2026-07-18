variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }

resource "google_redis_instance" "aerogrid" {
  name           = "aerogrid-${var.environment}"
  region         = var.region
  memory_size_gb = var.environment == "production" ? 1 : 1
  tier           = "BASIC"

  redis_version = "REDIS_7_0"
  display_name  = "AEROGRID Cache (${var.environment})"

  authorized_network = "projects/${var.project_id}/global/networks/default"

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time { hours = 3; minutes = 0 }
    }
  }
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "aerogrid-redis-url-${var.environment}"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "redis://:${google_redis_instance.aerogrid.auth_string}@${google_redis_instance.aerogrid.host}:${google_redis_instance.aerogrid.port}"
}

output "connection_name" { value = google_redis_instance.aerogrid.name }
output "connection_url" {
  value     = "redis://:${google_redis_instance.aerogrid.auth_string}@${google_redis_instance.aerogrid.host}:${google_redis_instance.aerogrid.port}"
  sensitive = true
}
