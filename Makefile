# Makefile for Bank API
.PHONY: help up down logs test test-cov shell migrate migrate-create format lint clean fresh seed

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
	docker-compose exec api pytest -v

test-cov:  ## Run tests with coverage
	docker-compose exec api pytest --cov=app --cov-report=html --cov-report=term

shell:  ## Open Python shell with Flask context
	docker-compose exec api flask shell

db-shell:  ## Open PostgreSQL shell
	docker-compose exec db psql -U bank_user -d bank_api_dev

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

fresh:  ## Fresh start (rebuild and migrate)
	docker-compose down -v
	docker-compose up -d --build
	@echo "Waiting for database to be ready..."
	@sleep 5
	docker-compose exec api alembic upgrade head

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
	@echo "✅ Setup complete! API available at http://localhost:5000"
	@echo "📚 API docs at http://localhost:5000/api/docs"

