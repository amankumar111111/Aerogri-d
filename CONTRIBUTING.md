# Contributing to AEROGRID

## Getting Started

```bash
# Clone
git clone https://github.com/helixorbit/aerogrid.git
cd aerogrid

# Setup (one command)
make setup

# Run development servers
make dev
```

## Project Structure

```
aerogrid/
├── backend/app/
│   ├── domain/          # Pure Python — no external dependencies
│   ├── application/     # Use cases — depends only on domain
│   ├── infrastructure/  # Adapters — implements domain ports
│   ├── api/             # REST endpoints
│   └── config/          # Settings and pilot config
├── frontend/src/        # React 18, TypeScript
├── tests/               # Unit, integration, e2e, security, load
├── docs/                # Architecture, API, deployment
└── infra/terraform/     # Infrastructure as Code
```

## Architecture Rules

1. **Domain layer has zero external imports.** No SQLAlchemy, no FastAPI, no httpx.
2. **Application layer depends only on domain.** No infrastructure imports.
3. **Infrastructure implements domain ports.** Adapters, not business logic.
4. **API layer depends on application and domain.** Never on infrastructure directly.

## Development Workflow

```bash
make test          # Run all tests
make lint          # Lint code
make typecheck     # Type check
make test-unit     # Unit tests only
make test-integration  # Integration tests
```

## Adding a New Provider

1. Implement `DataProvider` interface in `backend/app/domain/ports.py`
2. Create adapter in `backend/app/infrastructure/providers/`
3. Add configuration in `backend/app/config/settings.py`
4. Wire in `backend/app/main.py` lifespan
5. Write tests in `tests/test_providers_comprehensive.py`
6. Document in `docs/API.md`

## Adding a New API Endpoint

1. Add request/response schemas in `backend/app/api/schemas.py`
2. Add mapper in `backend/app/api/mappers.py`
3. Add route in `backend/app/api/routers/`
4. Wire router in `backend/app/main.py`
5. Write tests
6. OpenAPI spec auto-generates

## Commit Messages

Follow conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `test:` adding tests
- `docs:` documentation
- `refactor:` code restructuring
