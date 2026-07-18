variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "database_url" { type = string, sensitive = true }
variable "redis_url" { type = string, sensitive = true }
variable "gemini_api_key" { type = string, sensitive = true }

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = toset(["gemini-api-key", "database-url", "redis-url"])
  secret_id = "aerogrid-${each.key}-${var.environment}"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "app_secrets" {
  for_each = {
    "gemini-api-key" = var.gemini_api_key
    "database-url"   = var.database_url
    "redis-url"      = var.redis_url
  }
  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value
}

resource "google_cloud_run_v2_service" "aerogrid" {
  name     = "aerogrid-${var.environment}"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/aerogrid:latest"

      env {
        name  = "AEROGRID_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secrets["database-url"].id
            version = "latest"
          }
        }
      }
      env {
        name  = "AEROGRID_REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secrets["redis-url"].id
            version = "latest"
          }
        }
      }
      env {
        name  = "AEROGRID_GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secrets["gemini-api-key"].id
            version = "latest"
          }
        }
      }
      env {
        name  = "AEROGRID_ENVIRONMENT"
        value = var.environment
      }

      ports { container_port = 8080 }

      startup_probe {
        http_get { path = "/api/v1/health" port = 8080 }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get { path = "/api/v1/health" port = 8080 }
        period_seconds    = 30
        failure_threshold = 3
      }

      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
    }

    scaling {
      min_instance_count = var.environment == "production" ? 1 : 0
      max_instance_count = var.environment == "production" ? 10 : 3
    }

    service_account = google_service_account.aerogrid.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_service_account" "aerogrid" {
  account_id   = "aerogrid-${var.environment}"
  display_name = "AEROGRID ${var.environment}"
}

resource "google_secret_manager_secret_iam_binding" "app_secrets" {
  for_each  = google_secret_manager_secret.app_secrets
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  members   = ["serviceAccount:${google_service_account.aerogrid.email}"]
}

resource "google_project_iam_member" "cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.aerogrid.email}"
}

output "service_url" { value = google_cloud_run_v2_service.aerogrid.uri }
