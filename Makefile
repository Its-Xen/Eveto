.PHONY: help up down logs lint format check-all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Sync dependencies using uv
	uv sync

dev: ## Run the API locally with hot reload
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	uv run pytest -v

docker-up: ## Start all services via docker compose
	docker compose up -d --build

docker-down: ## Stop all services
	docker compose down

logs: ## Tail live logs for the API container
	docker compose logs -f api

bench: ## Run k6 load test via docker
	docker run --rm -i --network host grafana/k6 run - < k6/script.js

migrate: ## Run alembic migrations
	uv run alembic upgrade head

lint: ## Run linters in check-only mode 
	uv run ruff check .
	uv run black --check .
	uv run isort --check-only .
	uv run mypy app/

format: ## Auto-format and fix linting errors locally
	uv run ruff check . --fix
	uv run black .
	uv run isort .

check-all: ## Run pre-commit on ALL files 
	uv run pre-commit run --all-files