# AEROGRID v1.0.0

**Release date:** July 2026
**Tag:** `v1.0.0`

---

## What is AEROGRID?

A city speaks before a crisis. AEROGRID connects the signals.

AEROGRID is an AI-powered hyperlocal environmental intelligence platform that transforms isolated citizen observations into correlated environmental signals. Instead of treating every complaint as independent, AEROGRID measures whether multiple compatible observations describe the same emerging event.

---

## What's in v1.0

### Citizen Reporting

Citizens submit observations with photo, voice, text, and GPS in English, Hindi, or Marathi. The submission flow is designed for speed — under 60 seconds from open to submit.

### Correlation Engine

A deterministic five-dimension scoring engine evaluates whether observations are related:

- **Semantic:** Do observations describe the same event type?
- **Spatial:** Are they geographically proximate?
- **Temporal:** Were they reported around the same time?
- **Independence:** Are they genuinely independent sources?
- **Environmental Context:** Does weather, satellite, or government data corroborate?

Same inputs always produce same outputs. No randomness. No learned parameters.

### Evidence Convergence

A configurable policy engine computes composite evidence scores. Every signal carries per-observation contribution breakdowns. Explainability reports show exactly why a signal was classified at its current level.

### Signal Lifecycle

Signals progress through a deterministic state machine:

```
Watch → Probable Hotspot → High Confidence → Archived
```

Every transition is an immutable event. Every state change is recorded.

### Command Centre

A municipal dashboard answering three questions:

1. What is happening now?
2. Where is it happening?
3. What deserves attention first?

Map-first layout. Signal feed sorted by priority. One-click verification and archival.

### AI Interpretation

Google Gemini interprets citizen observations — identifying visible evidence, categorizing events, assessing severity. Gemini interprets evidence. It never decides whether an incident is real. That decision belongs to the deterministic correlation engine.

### Provider Integrations

- **Weather (Open-Meteo):** Temperature, humidity, wind, precipitation
- **FIRMS (NASA):** Satellite fire detection
- **CPCB:** Government air quality monitoring

All providers are behind ports. If any provider fails, the system continues with reduced context. No fabricated values.

### Explainability

Every signal carries a human-readable explanation showing:

- How many observations contributed
- Per-dimension scores (semantic, spatial, temporal, environmental)
- Which observations contributed most and why
- Policy version used for classification

### Audit Trail

Every action generates an audit event. Every state transition is recorded. Every signal is reproducible — replay the event log to reconstruct state at any historical point.

### Policy Engine

Correlation thresholds, evidence weights, and minimum observation counts are configurable per ward. Every policy change creates a new version. Existing signals retain their original policy. Historical signals are always reproducible.

### Clean Architecture

- **Domain layer:** Pure Python. Zero external imports. Fully testable.
- **Application layer:** Depends only on domain.
- **Infrastructure layer:** Implements domain ports. External adapters.
- **API layer:** Depends on application and domain.

---

## Test Coverage

| Category | Tests |
|---|---|
| Domain unit tests | 107 |
| Policy tests | 25 |
| Integration tests | 27 |
| End-to-end tests | 8 |
| Workflow tests | 25 |
| Security tests | 22 |
| Load tests | 3 |
| **Total** | **222** |

---

## Known Limitations

- **Authentication:** API key stub only. No real RBAC or user management.
- **Media storage:** Observation media (photos, voice) is accepted but not persisted to cloud storage.
- **Notifications:** Email notification is a stub. In-app notifications work.
- **Rate limiting:** Configured but backed by in-memory store. Needs Redis for production.
- **CORS:** Configured as `*` for development. Must be locked to production domain.
- **Single database instance:** No read replicas. Not production-scaled.
- **Correlation scan:** Linear scan of signals. Needs spatial indexing at scale.

---

## Technology

| Component | Version |
|---|---|
| Python | 3.12 |
| FastAPI | 0.115+ |
| SQLAlchemy | 2.0+ |
| PostgreSQL | 15 |
| React | 18 |
| TypeScript | 5.x |
| Tailwind CSS | 4.x |
| Google Gemini | 2.0 Flash |

---

## License

MIT
