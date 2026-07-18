# Runbook — "AEROGRID stopped working at 2:00 AM"

## Step 1: Check Service Status (2 minutes)

```bash
# Health check
curl -sf https://aerogrid-prod.run.app/api/v1/health

# Readiness check (includes DB and Redis)
curl -sf https://aerogrid-prod.run.app/api/v1/ready

# If both fail → go to Step 2
# If health ok but ready degraded → go to Step 3
```

## Step 2: Service Down (5 minutes)

```bash
# Check Cloud Run logs
gcloud run services logs read aerogrid-production --region=asia-south1 --limit=50

# Check if recent deployment caused the issue
gcloud run services describe aerogrid-production --region=asia-south1

# If recent deploy → rollback
gcloud run services update-traffic aerogrid-production \
  --to-revisions=PREVIOUS_REVISION=100 --region=asia-south1
```

## Step 3: Database Issues

```bash
# Check Cloud SQL instance
gcloud sql instances describe aerogrid-production

# Check connections
gcloud sql operations list --instance=aerogrid-production --limit=5

# If connections exhausted → increase max_connections
gcloud sql instances patch aerogrid-production --database-flags=max_connections=200
```

## Step 4: Provider Failures

```bash
# Check provider health endpoint
curl -sf https://aerogrid-prod.run.app/api/v1/providers/health

# If Gemini down → system continues without AI interpretation (observations stored raw)
# If CPCB/FIRMS/Weather down → correlation continues with reduced context
# All providers degrade gracefully — no action needed unless all are down
```

## Step 5: High Error Rate

```bash
# Check error logs
gcloud run services logs read aerogrid-production --region=asia-south1 --filter="severity=ERROR" --limit=20

# Check API metrics
curl -sf https://aerogrid-prod.run.app/api/v1/metrics

# If error rate > 5% → check for:
# - Database connection pool exhaustion
# - Gemini API rate limiting
# - Invalid request payloads
```

## Escalation

| Severity | Response Time | Contact |
|---|---|---|
| Service completely down | 15 minutes | On-call engineer |
| Degraded (providers failing) | 1 hour | On-call engineer |
| Non-critical issues | Next business day | Development team |

## Backup Restoration

```bash
# List available backups
gcloud sql backups list --instance=aerogrid-production

# Restore to point in time
gcloud sql backups restore BACKUP_ID --restore-instance=aerogrid-production

# RPO: 5 minutes (WAL archiving) | RTO: 30 minutes
```
