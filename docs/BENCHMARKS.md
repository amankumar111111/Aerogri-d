# Performance Benchmarks

**Date:** July 2026
**Environment:** Local development (Python 3.12, SQLite in-memory)
**Note:** Production benchmarks will differ. These are baseline measurements.

## Core Metrics

| Metric | Value | Target | Status |
|---|---|---|---|
| Observation submission | < 5 ms | < 3000 ms | ✓ |
| Gemini interpretation | ~2 s (network) | < 10 s | ✓ |
| Correlation engine (100 signals) | < 1 ms | < 2000 ms | ✓ |
| Dashboard load (API) | < 50 ms | < 2000 ms | ✓ |
| API p95 latency | < 50 ms | < 500 ms | ✓ |
| OpenAPI generation | < 100 ms | < 1 s | ✓ |

## Load Test Results

| Concurrency | Throughput | Latency (avg) | Status |
|---|---|---|---|
| 100 concurrent submissions | 32,134 obs/sec | 0.003 s | ✓ |
| 100 concurrent correlations | 44,926 corr/sec | 0.002 s | ✓ |
| Mixed (50 submit + 50 correlate) | 33,333 ops/sec | 0.003 s | ✓ |

*Note: Load tests use in-memory stores. Production with PostgreSQL will be slower.*

## Component Breakdown

### Correlation Engine

| Operation | Time |
|---|---|
| Semantic scoring | < 0.01 ms |
| Spatial scoring (haversine) | < 0.01 ms |
| Temporal scoring | < 0.01 ms |
| Independence scoring | < 0.01 ms |
| Environmental scoring | < 0.01 ms |
| Composite scoring | < 0.01 ms |
| Signal scan (100 signals) | < 0.5 ms |

### Provider Latency (Network)

| Provider | Typical | Timeout |
|---|---|---|
| Weather (Open-Meteo) | 300–500 ms | 10 s |
| FIRMS (NASA) | 1–3 s | 15 s |
| CPCB | 500 ms–2 s | 10 s |
| Gemini | 1–3 s | 10 s |

### Frontend

| Metric | Value |
|---|---|
| Build time | 195 ms |
| JS bundle (gzip) | 82 KB |
| CSS (gzip) | 4 KB |
| First contentful paint | < 500 ms (local) |

## Database (PostgreSQL 15)

| Operation | Expected |
|---|---|
| Single observation insert | < 5 ms |
| Signal list (20 records) | < 10 ms |
| Signal count by state | < 5 ms |
| Analytics aggregation | < 50 ms |
| Heatmap query (500 points) | < 100 ms |

## Scalability Notes

Current architecture handles up to ~1000 observations/day comfortably. For 50M+ observations:

- Add PostgreSQL read replicas
- Add spatial indexing (PostGIS)
- Move correlation to background workers
- Add Redis caching layer
- Pre-compute analytics views
