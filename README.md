# AEROGRID

**AI-Powered Hyperlocal Environmental Intelligence Platform**

A city speaks before a crisis. We connect the signals.

## Quick Start

```bash
# Start services
docker-compose up -d

# Run backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload

# Run frontend
cd frontend && npm install && npm run dev
```

App runs at http://localhost:3000 (frontend) → http://localhost:8080 (API).

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design.

**Core principle:** AI interprets evidence; deterministic domain logic makes operational decisions.

## API

See [API.md](./API.md) for the complete API reference.

```bash
# Submit an observation
curl -X POST http://localhost:8080/api/v1/observations \
  -H "Content-Type: application/json" \
  -d '{"content":"smoke visible","latitude":19.076,"longitude":72.878,"category":"smoke","device_id":"test"}'

# List signals
curl http://localhost:8080/api/v1/signals
```

## Development

```bash
# Run tests
cd backend && python -m pytest tests/ -v

# Lint
ruff check backend/

# Type check
cd backend && pyright .

# Build frontend
cd frontend && npm run build
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md).

## License

MIT
