# AEROGRID Architecture

## Core Principle

**AI interprets evidence. Deterministic domain logic makes operational decisions.**

Gemini identifies what is visible — smoke, dust, combustion patterns — but it never decides whether an incident is real. That decision is made by the deterministic correlation engine.

## System Layers

```
┌─────────────────────────────────┐
│         React Frontend          │  Citizen App + Command Centre
├─────────────────────────────────┤
│         API Layer               │  FastAPI, validation, auth, CORS
├─────────────────────────────────┤
│      Application Layer          │  Use cases, orchestration
├─────────────────────────────────┤
│        Domain Layer             │  Entities, policies, state machines
├─────────────────────────────────┤
│     Infrastructure Layer        │  PostgreSQL, Gemini, providers, Redis
└─────────────────────────────────┘
```

**Dependency rule:** Domain layer has zero external dependencies.

## Key Components

### Observation Independence Engine
Determines whether observations are genuinely independent. Uses SHA-256 fingerprints for O(1) exact-match deduplication, plus similarity scoring for fuzzy matching.

### Correlation Engine
Evaluates five dimensions: semantic, spatial, temporal, independence, environmental context. Entirely deterministic — same inputs produce same outputs.

### Evidence Convergence Engine
Produces a unified evidence picture per signal. Configurable policies, versioned thresholds, human-readable explainability.

### Signal Lifecycle
Watch → Probable Hotspot → High Confidence → Archived. Every transition is an immutable event.

## Data Flow

```
Citizen submits observation
  → Fingerprint computed (SHA-256)
  → Gemini interprets evidence (multimodal)
  → Correlation Engine evaluates against existing signals
  → Evidence Convergence computes composite score
  → Signal lifecycle state machine updates state
  → Audit event recorded
  → Notification sent (if escalation)
  → Dashboard updates
```

## Clean Architecture

- **Domain:** Zero external imports. Pure Python.
- **Application:** Depends only on domain. No infrastructure.
- **Infrastructure:** Implements domain ports. External adapters.
- **API:** Depends on application and domain. Never on infrastructure directly.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Frontend | React 18, TypeScript, Tailwind CSS, Zustand |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| AI | Google Gemini 2.0 Flash |
| Deployment | Google Cloud Run, Docker |
| CI/CD | GitHub Actions |
