.PHONY: help install dev run test bench docker-up docker-down

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

bench: ## Run k6 load test via docker
	docker run --rm -i --network host grafana/k6 run - < k6/script.js

migrate: ## Run alembic migrations
	uv run alembic upgrade head