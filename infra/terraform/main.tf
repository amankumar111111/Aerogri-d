terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
  backend "gcs" { bucket = "aerogrid-tf-state", prefix = "terraform" }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" { type = string }
variable "region" { type = string, default = "asia-south1" }
variable "environment" { type = string, default = "staging" }

module "postgres" {
  source      = "./postgres"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "redis" {
  source      = "./redis"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "cloudrun" {
  source           = "./cloudrun"
  project_id       = var.project_id
  region           = var.region
  environment      = var.environment
  database_url     = module.postgres.connection_url
  redis_url        = module.redis.connection_url
  gemini_api_key   = var.gemini_api_key
}

variable "gemini_api_key" {
  type      = string
  sensitive = true
}

output "service_url" { value = module.cloudrun.service_url }
output "database_connection" { value = module.postgres.connection_name }
