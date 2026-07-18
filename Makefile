.PHONY: dev test lint typecheck build clean setup

# Developer Experience — one command to rule them all

setup: ## First-time setup: install all dependencies
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev: ## Start development servers (backend + frontend)
	cd backend && uvicorn app.main:app --reload --port 8080 &
	cd frontend && npm run dev

test: ## Run all tests
	cd backend && python -m pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	cd backend && python -m pytest tests/test_domain_unit.py tests/test_domain_value_objects.py tests/test_domain_policies.py -v

test-integration: ## Run integration tests
	cd backend && python -m pytest tests/test_integration.py tests/test_end_to_end.py tests/test_providers_comprehensive.py -v

test-security: ## Run security tests
	cd backend && python -m pytest tests/test_security.py -v

test-load: ## Run load tests
	cd backend && python -m pytest tests/test_load.py -v -s

lint: ## Lint code
	cd backend && ruff check app/

typecheck: ## Type check
	cd backend && pyright .

build: ## Build frontend
	cd frontend && npm run build

clean: ## Clean build artifacts
	rm -rf frontend/dist frontend/node_modules backend/.pytest_cache backend/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up: ## Start with Docker Compose
	docker compose up -d

docker-down: ## Stop Docker Compose
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
