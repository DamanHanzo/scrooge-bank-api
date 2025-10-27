# Makefile for Bank API
.PHONY: help up down logs test test-cov shell migrate migrate-create format lint clean fresh seed db-create-test test-setup test-clean test-full

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up:  ## Start all services
	docker-compose up -d

down:  ## Stop all services
	docker-compose down

logs:  ## View API logs
	docker-compose logs -f api

logs-db:  ## View database logs
	docker-compose logs -f db

test:  ## Run tests
	@$(MAKE) -s db-create-test
	docker-compose exec -T api pytest -v

test-cov:  ## Run tests with coverage
	@$(MAKE) -s db-create-test
	docker-compose exec -T api pytest --cov=app --cov-report=html --cov-report=term

test-setup:  ## Setup test database and run tests
	@$(MAKE) -s db-create-test
	@echo "Running tests..."
	@docker-compose exec -T api pytest -v

test-clean:  ## Drop test database (cleanup after tests)
	@echo "Dropping test database..."
	@docker-compose exec -T db psql -U bank_user -d postgres -c "DROP DATABASE IF EXISTS bank_api_test;" 2>/dev/null || true
	@echo "✅ Test database cleaned"

test-full:  ## Run tests and cleanup test database after
	@$(MAKE) -s test
	@$(MAKE) -s test-clean

shell:  ## Open Python shell with Flask context
	docker-compose exec api flask shell

db-shell:  ## Open PostgreSQL shell
	docker-compose exec db psql -U bank_user -d bank_api_dev

db-create-test:  ## Create test database
	@echo "Creating test database..."
	@docker-compose exec -T db psql -U bank_user -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'bank_api_test'" | grep -q 1 || docker-compose exec -T db psql -U bank_user -d postgres -c "CREATE DATABASE bank_api_test;"
	@echo "✅ Test database ready"

migrate:  ## Run database migrations
	docker-compose exec api alembic upgrade head

migrate-create:  ## Create new migration (usage: make migrate-create msg="your message")
	docker-compose exec api alembic revision --autogenerate -m "$(msg)"

migrate-down:  ## Rollback one migration
	docker-compose exec api alembic downgrade -1

migrate-history:  ## Show migration history
	docker-compose exec api alembic history

format:  ## Format code with black
	docker-compose exec api black app tests

lint:  ## Run linters
	docker-compose exec api flake8 app tests
	docker-compose exec api mypy app

lint-fix:  ## Run linters and auto-fix where possible
	docker-compose exec api black app tests
	docker-compose exec api flake8 app tests

clean:  ## Remove containers and volumes
	docker-compose down -v
	@$(MAKE) -s test-clean

fresh:  ## Fresh start (rebuild and migrate)
	docker-compose down -v
	docker-compose up -d --build
	@echo "Waiting for database to be ready..."
	@sleep 5
	docker-compose exec api alembic upgrade head
	@$(MAKE) -s db-create-test

seed:  ## Seed database with sample data
	docker-compose exec api python scripts/seed_data.py

build:  ## Build Docker images
	docker-compose build

rebuild:  ## Rebuild Docker images from scratch
	docker-compose build --no-cache

ps:  ## Show running containers
	docker-compose ps

restart:  ## Restart all services
	docker-compose restart

restart-api:  ## Restart only API service
	docker-compose restart api

tools:  ## Start services with pgAdmin
	docker-compose --profile tools up -d

install:  ## Install pre-commit hooks
	pre-commit install

setup: up migrate seed  ## Complete setup (start, migrate, seed)
	@$(MAKE) -s db-create-test
	@echo "✅ Setup complete! API available at http://localhost:5025"
	@echo "📚 API docs at http://localhost:5025/api/docs"
	@echo "🧪 Run 'make test' to run tests"

