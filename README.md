# AEROGRID

**AI-Powered Hyperlocal Environmental Intelligence Platform**

> A city speaks before a crisis. We connect the signals.

AEROGRID correlates independent citizen observations, satellite data, weather conditions, and government monitoring into actionable environmental signals for municipal teams.

## How It Works

```
Citizen submits observation (photo + voice + text + GPS)
        ↓
Gemini interprets evidence (categories, severity, alignment)
        ↓
Correlation Engine evaluates 5 dimensions:
  Semantic · Spatial · Temporal · Independence · Environmental
        ↓
Signal Lifecycle: Watch → Probable Hotspot → High Confidence → Archived
        ↓
Municipal Command Centre receives prioritized alerts
```

**Core principle:** AI interprets evidence. Deterministic engine makes decisions.

## Quick Start

### Option 1: Local Development

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8080

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- Backend: http://localhost:8080
- Frontend: http://localhost:3000
- API Docs: http://localhost:8080/api/docs

### Option 2: Docker

```bash
docker compose up -d
```

### Option 3: Run Demo

```bash
cd backend
python -m seed_demo      # Generate 12 observations
python -m import_demo    # Import through full pipeline
```

## API

```bash
# Health check
curl http://localhost:8080/api/v1/health

# Submit observation
curl -X POST http://localhost:8080/api/v1/observations \
  -H "Content-Type: application/json" \
  -d '{"content":"smoke visible","latitude":19.076,"longitude":72.878,"category":"smoke","device_id":"test"}'

# List signals
curl http://localhost:8080/api/v1/signals

# Get signal detail
curl http://localhost:8080/api/v1/signals/{id}
```

Full API reference: [docs/API.md](./docs/API.md)

## Architecture

```
┌─────────────────────────────────┐
│         React Frontend          │  Citizen App + Command Centre
├─────────────────────────────────┤
│         API Layer               │  FastAPI, validation, auth, rate limiting
├─────────────────────────────────┤
│      Application Layer          │  Use cases: submit, interpret, correlate
├─────────────────────────────────┤
│        Domain Layer             │  Entities, policies, state machines
├─────────────────────────────────┤
│     Infrastructure Layer        │  PostgreSQL, Gemini, providers, Redis
└─────────────────────────────────┘
```

- **Domain:** Zero external imports. Pure Python. Fully testable.
- **Application:** Depends only on domain. No infrastructure.
- **Infrastructure:** Implements domain ports. Swappable adapters.
- **API:** Depends on application and domain. Never on infrastructure.

Full architecture: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Frontend | React 18, TypeScript, Tailwind CSS |
| Database | PostgreSQL 15 (SQLite for local dev) |
| Cache | Redis 7 |
| AI | Google Gemini 2.0 Flash |
| Deployment | Google Cloud Run, Docker |
| CI/CD | GitHub Actions (10-stage pipeline) |

## Testing

```bash
# Backend tests
cd backend && python -m pytest tests/ -v

# Frontend tests
cd frontend && npx vitest run

# Full test suite
python -m pytest tests/ -v --ignore=tests/test_api.py --ignore=tests/test_load.py
```

**Test coverage:** 234 backend + 16 frontend = 250 tests

## Project Structure

```
aerogrid/
├── backend/
│   ├── app/
│   │   ├── domain/          # Pure Python — no external dependencies
│   │   ├── application/     # Use cases — depends only on domain
│   │   ├── infrastructure/  # Adapters — implements domain ports
│   │   ├── api/             # REST endpoints, middleware, schemas
│   │   └── config/          # Settings and pilot configuration
│   ├── migrations/          # Alembic database migrations
│   └── tests/               # Unit, integration, e2e, security tests
├── frontend/
│   └── src/
│       ├── pages/           # 5 workflows
│       ├── __tests__/       # Vitest tests
│       ├── api.ts           # Typed API client
│       ├── store.ts         # Zustand state
│       └── types.ts         # TypeScript types
├── infra/terraform/         # Cloud Run, PostgreSQL, Redis
├── docker/                  # Multi-stage Dockerfile
├── docs/                    # Architecture, API, deployment, runbook
├── docs/adr/                # 10 Architecture Decision Records
├── tests/                   # Backend test suite
├── Makefile                 # make setup, make dev, make test
└── .github/workflows/       # CI/CD pipeline
```

## Documentation

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design and data flow |
| [API.md](./docs/API.md) | Complete API reference |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | How to deploy |
| [RUNBOOK.md](./docs/RUNBOOK.md) | Incident response (2:00 AM guide) |
| [OPERATIONS.md](./docs/OPERATIONS.md) | Monitoring, backup, security |
| [BENCHMARKS.md](./docs/BENCHMARKS.md) | Performance measurements |
| [PILOT-REVIEW.md](./docs/PILOT-REVIEW.md) | Pilot evaluation framework |
| [WHY.md](./WHY.md) | Why AEROGRID exists |
| [ROADMAP-v2.0.md](./ROADMAP-v2.0.md) | Research problems for v2.0 |
| ADR-001 through ADR-010 | Architecture Decision Records |

## License

MIT
