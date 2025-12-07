.PHONY: help test verify clean build up down logs install-dev

# Default target
help: ## Show this help message
	@echo "Vertex AR B2B Platform - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Development commands
install-dev: ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	cd frontend && npm install
	npx playwright install

# Docker commands
up: ## Start all services with Docker Compose
	@echo "🚀 Starting services..."
	docker compose up -d

down: ## Stop all services
	@echo "🛑 Stopping services..."
	docker compose down

logs: ## Show logs for all services
	docker compose logs -f

# Database commands
migrate: ## Run database migrations
	docker compose exec app alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="migration message")
	docker compose exec app alembic revision --autogenerate -m "$(MSG)"

reset-db: ## Reset database (WARNING: This will delete all data)
	docker compose exec app alembic downgrade base
	docker compose exec app alembic upgrade head

# Testing commands
test: ## Run all tests
	@echo "🧪 Running all tests..."
	pytest tests/ -v --cov=app

test-unit: ## Run unit tests only
	@echo "📋 Running unit tests..."
	pytest tests/unit/ -v --cov=app

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	pytest tests/integration/ -v

test-e2e: ## Run E2E tests only
	@echo "🌐 Running E2E tests..."
	cd frontend && npx playwright test

test-storage: ## Run storage-specific tests
	@echo "🗄️ Running storage tests..."
	pytest tests/unit/test_storage_providers.py tests/integration/test_storage_integration.py -v --cov=app.services.storage

# Verification commands
verify: ## Run complete storage verification
	@echo "🔍 Running complete storage verification..."
	./scripts/run_verification.sh

verify-quick: ## Run quick verification (unit + integration tests only)
	@echo "⚡ Running quick verification..."
	pytest tests/unit/test_storage_providers.py tests/integration/test_storage_integration.py -v

verify-full: ## Run full verification including E2E tests
	@echo "🔍 Running full verification..."
	./scripts/run_verification.sh

# Quality assurance commands
lint: ## Run code linting
	@echo "🔍 Running linting..."
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/

format: ## Format code
	@echo "✨ Formatting code..."
	black app/ tests/
	isort app/ tests/

type-check: ## Run type checking
	@echo "🔍 Running type checking..."
	mypy app/

security-check: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r app/
	safety check

# Build commands
build: ## Build Docker images
	@echo "🏗️ Building Docker images..."
	docker compose build

build-prod: ## Build production Docker images
	@echo "🏗️ Building production images..."
	docker compose -f docker-compose.yml build --no-cache

# Cleanup commands
clean: ## Clean up temporary files and containers
	@echo "🧹 Cleaning up..."
	docker compose down --volumes --remove-orphans
	docker system prune -f
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/

clean-test: ## Clean test artifacts only
	@echo "🧹 Cleaning test artifacts..."
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -rf frontend/test-results/ frontend/playwright-report/

# Development workflow commands
dev-setup: ## Set up complete development environment
	@echo "🛠️ Setting up development environment..."
	make install-dev
	make up
	sleep 10
	make migrate
	@echo "✅ Development environment ready!"

dev-reset: ## Reset development environment
	@echo "🔄 Resetting development environment..."
	make clean
	make dev-setup

# Production commands
prod-deploy: ## Deploy to production (simplified)
	@echo "🚀 Deploying to production..."
	make build-prod
	make down
	make up
	make migrate
	@echo "✅ Production deployment complete!"

# Monitoring commands
health: ## Check health of all services
	@echo "🏥 Checking service health..."
	curl -f http://localhost:8000/api/health/status || echo "❌ API health check failed"
	docker compose ps

status: ## Show status of all services
	@echo "📊 Service status:"
	docker compose ps

# Storage-specific commands
storage-test-local: ## Test local storage provider
	@echo "🗄️ Testing local storage..."
	STORAGE_TYPE=local STORAGE_BASE_PATH=/tmp/test_storage pytest tests/unit/test_storage_providers.py::TestStorageProviderFactory::test_create_local_provider -v

storage-test-minio: ## Test MinIO storage provider
	@echo "🗄️ Testing MinIO storage..."
	STORAGE_TYPE=minio MINIO_ENDPOINT=localhost:9000 MINIO_ACCESS_KEY=test MINIO_SECRET_KEY=test MINIO_BUCKET_NAME=test pytest tests/unit/test_storage_providers.py::TestStorageProviderFactory::test_create_minio_provider -v

storage-test-yandex: ## Test Yandex Disk storage provider
	@echo "🗄️ Testing Yandex Disk storage..."
	STORAGE_TYPE=yandex_disk YANDEX_DISK_OAUTH_TOKEN=test pytest tests/unit/test_storage_providers.py::TestStorageProviderFactory::test_create_yandex_disk_provider -v

storage-benchmark: ## Run storage performance benchmarks
	@echo "📊 Running storage benchmarks..."
	python scripts/benchmark_storage.py

# Documentation commands
docs-serve: ## Serve documentation locally
	@echo "📚 Serving documentation..."
	cd docs && python -m http.server 8001

docs-build: ## Build documentation
	@echo "📚 Building documentation..."
	@echo "Documentation is in Markdown format, no build step required."

# Backup commands
backup: ## Create backup of database and storage
	@echo "💾 Creating backup..."
	docker compose exec postgres pg_dump -U vertex_ar vertex_ar > backup_$(shell date +%Y%m%d_%H%M%S).sql
	tar -czf storage_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz storage/

# Utility commands
shell-app: ## Open shell in app container
	docker compose exec app bash

shell-db: ## Open database shell
	docker compose exec postgres psql -U vertex_ar vertex_ar

shell-redis: ## Open Redis shell
	docker compose exec redis redis-cli

# Quick start commands
quick-test: ## Quick test run for development
	@echo "⚡ Quick test run..."
	pytest tests/unit/test_storage_providers.py -v --tb=short

quick-verify: ## Quick verification for CI/CD
	@echo "⚡ Quick verification..."
	pytest tests/unit/test_storage_providers.py tests/integration/test_storage_integration.py -v --tb=short --maxfail=1