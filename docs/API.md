# AEROGRID API Reference

**Base URL:** `https://aerogrid.run.app/api/v1`

**Authentication:** Citizen endpoints are open. Municipal endpoints require `X-API-Key` header.

**Error Format:** All errors return `{"error": {"code": "...", "message": "...", "correlation_id": "...", "timestamp": "..."}}`

---

## Observations

### POST /observations

Submit a citizen observation.

**Request:**
```json
{
  "content": "Heavy smoke from factory",
  "latitude": 19.076,
  "longitude": 72.878,
  "category": "smoke",
  "language": "en",
  "device_id": "device-123"
}
```

**Response (201):**
```json
{
  "observation_id": "uuid",
  "fingerprint": "sha256-hash",
  "status": "submitted",
  "tracking_ref": "first-8-chars"
}
```

**Categories:** `smoke`, `dust`, `chemical`, `water`, `noise`, `fire`, `gas_leak`, `construction_dust`, `sewage`, `other`

**Languages:** `en`, `hi`, `mr`

---

### GET /observations/{id}

Retrieve a submitted observation.

**Response (200):**
```json
{
  "id": "uuid",
  "fingerprint": "sha256-hash",
  "content": "Heavy smoke from factory",
  "category": "smoke",
  "language": "en",
  "latitude": 19.076,
  "longitude": 72.878,
  "status": "interpreted",
  "created_at": "ISO-8601",
  "interpreted_at": "ISO-8601"
}
```

---

## Signals

### GET /signals

List signals with optional state filter.

**Query Parameters:**
- `state`: Filter by state (`watch`, `probable_hotspot`, `high_confidence`, `archived`)
- `offset`: Pagination offset (default: 0)
- `limit`: Page size 1–100 (default: 20)

**Response (200):** Array of signal objects.

---

### GET /signals/{id}

Get full signal detail.

**Response (200):**
```json
{
  "id": "uuid",
  "state": "probable_hotspot",
  "latitude": 19.076,
  "longitude": 72.878,
  "category": "smoke",
  "confidence_value": 0.72,
  "contributing_observation_ids": ["uuid1", "uuid2"],
  "contributions": [
    {
      "observation_id": "uuid1",
      "fingerprint": "hash",
      "dimension_scores": {"semantic": 0.82, "spatial": 0.91},
      "contribution_score": 0.79,
      "weighted_contribution": 0.55,
      "evaluation_timestamp": "ISO-8601"
    }
  ],
  "environmental_context": {"temperature": 38, "humidity": 35},
  "version": 3,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

---

### POST /signals/{id}/verify

Mark signal as field-verified (archives it).

**Response (200):**
```json
{"signal_id": "uuid", "state": "archived", "message": "Signal verified and archived"}
```

---

### POST /signals/{id}/archive

Manually archive a signal.

**Response (200):**
```json
{"signal_id": "uuid", "state": "archived", "message": "Signal archived"}
```

---

## Analytics

### GET /analytics

Aggregate statistics.

**Response (200):**
```json
{
  "total_observations": 1234,
  "total_signals": 56,
  "active_signals": 12,
  "high_confidence_signals": 3,
  "avg_confidence": 0.65,
  "signals_by_state": {"watch": 5, "probable_hotspot": 4, "high_confidence": 3, "archived": 44}
}
```

### GET /analytics/heatmap

Signal locations for map overlay. Max 500 points.

### GET /analytics/timeline

Recent signal activity. Max 50 entries.

---

## Health

| Endpoint | Description |
|---|---|
| GET /health | Service health status |
| GET /ready | Readiness with DB/Redis check |
| GET /metrics | Operational metrics |

---

## Response Headers

Every response includes:
- `X-Correlation-ID`: Unique request ID for debugging
- `X-Response-Time`: Server processing time in ms
- `X-Request-ID`: Unique request identifier
