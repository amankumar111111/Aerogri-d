# Operations Guide

## Monitoring Dashboard

Access the Cloud Run dashboard at:
`https://console.cloud.google.com/run/detail/asia-south1/aerogrid-production`

### Key Metrics to Watch

| Metric | Normal | Alert Threshold |
|---|---|---|
| Request latency (p95) | < 500ms | > 1s for 5 min |
| Error rate | < 1% | > 5% for 5 min |
| Active instances | 1–3 | Maxed out (10) for 5 min |
| Gemini API latency | < 5s | > 15s for 5 min |
| Provider failures | 0/hr | > 3/hr |

## Backup Strategy

| Resource | Strategy | Frequency | Retention |
|---|---|---|---|
| PostgreSQL | Cloud SQL automated backup | Daily | 30 days |
| PostgreSQL WAL | Continuous archiving | Continuous | 7 days |
| Media files | Cross-region replication | Real-time | Indefinite |
| Audit logs | Append-only, replicated | Real-time | 2 years |
| Config (convergence policy) | Git version control | On change | Indefinite |

## Disaster Recovery

| Metric | Target |
|---|---|
| RTO (Recovery Time Objective) | 30 minutes |
| RPO (Recovery Point Objective) | 5 minutes |

### Recovery Steps

1. **Database failure:** Cloud SQL point-in-time recovery within 30-day window
2. **Service failure:** Redeploy from Docker image (latest successful build)
3. **Full disaster:** Rebuild from database backup + media replica + config from git
4. **Test restoration quarterly** via tabletop exercise

## Security Checklist

| Check | Frequency |
|---|---|
| API key rotation | Every 90 days |
| Dependency vulnerability scan | Every CI run |
| CORS configuration review | Monthly |
| Rate limit tuning | Monthly |
| Access log review | Weekly |
| Secrets rotation | Every 90 days |
| SSL certificate check | Monthly |

## Capacity Planning

Current: 0–10 Cloud Run instances, db-f1-micro PostgreSQL

Scale triggers:
- > 80% CPU utilization for 15 min → increase max instances
- > 80% DB connections → upgrade PostgreSQL tier
- > 1000 observations/day → consider dedicated Redis
- > 10,000 signals/day → consider read replicas
