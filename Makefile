# Makefile for Bank API
.PHONY: help setup up down logs test migrate seed shell db-shell fresh clean

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Complete first-time setup (start services, run migrations, seed data)
	@echo "🚀 Setting up Bank API..."
	@docker-compose up -d
	@echo "⏳ Waiting for database to be ready..."
	@sleep 5
	@docker-compose exec -T api alembic upgrade head
	@docker-compose exec -T db psql -U bank_user -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'bank_api_test'" | grep -q 1 || docker-compose exec -T db psql -U bank_user -d postgres -c "CREATE DATABASE bank_api_test;"
	@docker-compose exec -T api python scripts/seed_data.py
	@echo ""
	@echo "✅ Setup complete!"
	@echo "📍 API:  http://localhost:5025"
	@echo "📚 Docs: http://localhost:5025/api/docs"
	@echo "🧪 Tests: make test"

up:  ## Start all services
	@docker-compose up -d
	@echo "✅ Services started"
	@echo "📍 API:  http://localhost:5025"
	@echo "📚 Docs: http://localhost:5025/api/docs"

down:  ## Stop all services
	@docker-compose down
	@echo "✅ Services stopped"

logs:  ## View API logs (use Ctrl+C to exit)
	@docker-compose logs -f api

test:  ## Run all tests
	@echo "🧪 Running tests..."
	@docker-compose exec -T db psql -U bank_user -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'bank_api_test'" | grep -q 1 || docker-compose exec -T db psql -U bank_user -d postgres -c "CREATE DATABASE bank_api_test;"
	@docker-compose exec -T api pytest -v
	@echo "✅ Tests complete"

migrate:  ## Run database migrations
	@docker-compose exec -T api alembic upgrade head
	@echo "✅ Migrations complete"

seed:  ## Seed database with sample data
	@docker-compose exec -T api python scripts/seed_data.py
	@echo "✅ Database seeded"

shell:  ## Open Python shell with Flask context
	@docker-compose exec api flask shell

db-shell:  ## Open PostgreSQL shell
	@docker-compose exec db psql -U bank_user -d bank_api_dev

fresh:  ## Clean restart (removes all data)
	@echo "🗑️  Removing all containers and data..."
	@docker-compose down -v
	@echo "🔨 Rebuilding and starting services..."
	@docker-compose up -d --build
	@echo "⏳ Waiting for database to be ready..."
	@sleep 5
	@docker-compose exec -T api alembic upgrade head
	@docker-compose exec -T db psql -U bank_user -d postgres -c "CREATE DATABASE bank_api_test;"
	@echo ""
	@echo "✅ Fresh restart complete!"
	@echo "📍 API:  http://localhost:5025"
	@echo "📚 Docs: http://localhost:5025/api/docs"

clean:  ## Stop services and remove all data
	@docker-compose down -v
	@echo "✅ All containers and data removed"
