# Deployment Guide

## Prerequisites

- Google Cloud account with billing enabled
- Terraform 1.5+
- Docker
- gcloud CLI authenticated

## One-Time Setup

```bash
# 1. Create GCP project
gcloud projects create aerogrid-prod --name="AEROGRID"

# 2. Enable APIs
gcloud services enable run.googleapis.com sqladmin.googleapis.com redis.googleapis.com secretmanager.googleapis.com

# 3. Create Terraform state bucket
gsutil mb -l asia-south1 gs://aerogrid-tf-state

# 4. Set up secrets
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create aerogrid-gemini-api-key --data-file=-
```

## Deploy Infrastructure

```bash
cd infra/terraform

# Initialize
terraform init

# Plan (review changes)
terraform plan -var="project_id=aerogrid-prod" -var="environment=production"

# Apply
terraform apply -var="project_id=aerogrid-prod" -var="environment=production"
```

## Deploy Application

```bash
# Build and push Docker image
gcloud auth configure-docker
docker build -t gcr.io/aerogrid-prod/aerogrid:latest .
docker push gcr.io/aerogrid-prod/aerogrid:latest

# Deploy to Cloud Run
gcloud run deploy aerogrid-production \
  --image gcr.io/aerogrid-prod/aerogrid:latest \
  --region asia-south1 \
  --platform managed \
  --memory 1Gi \
  --min-instances 1 \
  --max-instances 10
```

## Environment Variables

| Variable | Source | Description |
|---|---|---|
| `AEROGRID_DATABASE_URL` | Secret Manager | PostgreSQL connection string |
| `AEROGRID_REDIS_URL` | Secret Manager | Redis connection string |
| `AEROGRID_GEMINI_API_KEY` | Secret Manager | Google Gemini API key |
| `AEROGRID_ENVIRONMENT` | Environment | deployment environment |

## Rollback

```bash
# Rollback to previous revision
gcloud run services update-traffic aerogrid-production \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region asia-south1
```
