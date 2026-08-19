# EVETO
A scaled-down, production-grade Eventbrite clone built to master advanced backend architecture patterns. Customers browse published events, reserve tickets under high concurrency, pay through a mocked provider, and receive confirmations. Admins manage inventory, and external partners pull data via a versioned, rate-limited API.

This project specifically forces the implementation of idempotency, retries, circuit breakers, database locking, and connection-pool tuning—mechanics that a standard CRUD app doesn't require, but a flash-sale ticketing system demands.


## Overview

### What is the project?
Eveto is a backend API service designed to handle the entire lifecycle of event ticket sales. It features a decoupled architecture using FastAPI, PostgreSQL for transactional data, Redis for caching and message brokering, and Dramatiq for asynchronous background processing.

### What problem does it solve?
It solves the problem of **ticket reservation under contention**. In real-world scenarios, hundreds of users might try to buy the last few tickets for an event simultaneously. Eveto ensures that inventory is never oversold, payment webhooks are safely retried (idempotent), and the system remains responsive under heavy load.

### Who is it for?
This project is designed as an advanced portfolio piece for backend engineers. It demonstrates mastery over distributed systems, concurrency, observability, and resilient architecture patterns.


## Features

- **Role-Based Access Control (RBAC):** JWT (RS256) authentication for Customers, Admins, and API Keys for Partners.
- **Concurrency-Safe Reservations:** Atomic inventory decrementing using PostgreSQL locking to guarantee zero overselling.
- **Asynchronous Payments:** Mock payment provider integration with idempotent webhooks, retries, and circuit breakers.
- **Background Processing:** Dramatiq workers handling payment processing, expiration sweeps, and notification logging.
- **Observability:** End-to-end tracing (OpenTelemetry), structured JSON logging (structlog), and Prometheus metrics.
- **Partner API:** Versioned, rate-limited, API-key authenticated endpoints for external integrations.

---

## Requirements

This project uses **`uv`** for fast, reliable Python package management. 

- **Prerequisites:** 
  - Docker and Docker Compose
  - Python 3.12+ (if running locally outside Docker)
  - `uv` package manager
- **Supported versions:** Python 3.12+
- **Dependencies:** All dependencies are managed via `pyproject.toml` and locked in `uv.lock`. Key dependencies include FastAPI, SQLAlchemy 2.0 (async), Alembic, Dramatiq, Redis, Pydantic v2, and OpenTelemetry, You can check others in requirement.txt.

## Configuration

Configuration is strictly environment-driven using `pydantic-settings`. There are zero hardcoded secrets. 

- **Environment variables:** Managed via a `.env` file at the project root. 
- **Configuration files:** Copy the `.env.sample` file to `.env` to start.

```bash
cp .env.sample .env
```

- **Optional settings:** The `.env` file allows you to toggle environment states (`dev`, `staging`, `prod`), configure database pool sizes, set Redis TTLs, and point to JWT RSA key paths.


## Installation

Installation is fully containerized using Docker Compose to ensure a consistent development environment.

### Clone/download
```bash
git clone https://github.com/Its-Xen/Eveto
cd Eveto
```

### Install dependencies (Local UV sync)
If you want IDE autocompletion and local linting, sync the Python dependencies:
```bash
uv sync
```

### Build/setup
To build the Docker images and start the infrastructure (Postgres, Redis, FastAPI):
```bash
# Build images and start containers in the background
docker compose up -d --build

# View running containers
docker compose ps

# Stop the application
docker compose down
```

### Running external commands (Migrations & Seeding)
Once the containers are running, apply database migrations and seed initial data:
```bash
# Run Alembic migrations
docker compose exec api alembic upgrade head

# (Optional) Run the seed script to generate fake venues/events
docker compose exec api python -m app.db.seed
```


## Usage

### Basic usage
Once running, the API is available at `http://localhost:8000`.

- **API Docs (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

### Common workflows
1. Register a user via `POST /auth/register`.
2. Log in to receive a JWT via `POST /auth/login`.
3. Browse events via `GET /events`.
4. Reserve tickets via `POST /reservations` (requires an `Idempotency-Key` header).
5. Checkout via `POST /checkout/{reservation_id}` to trigger the mock payment and webhook flow.

### Lint and Reformat + Pre-commit
This project enforces strict code quality using `pre-commit` hooks (Ruff, Black, isort, Mypy).

To set up the hooks locally:
```bash
uv run pre-commit install
```
To manually run the checks on all files:
```bash
uv run pre-commit run --all-files
```

### Documentation
- **API reference:** Interactive OpenAPI documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the server.
- **CLI reference:** Use `docker compose exec api <command>` (e.g., `alembic`, `pytest`).
- **Additional guides:** Architectural decisions are documented in the `/adr` folder.

### Testing
The project uses a split testing strategy: Unit, Integration, and Contract tests.

- **How to run tests:** Tests are executed inside the Docker container to ensure access to testcontainers.
```bash
# Run unit tests
docker compose exec api pytest -m unit

# Run integration tests (uses testcontainers for real Postgres/Redis)
docker compose exec api pytest -m integration

# Run contract tests (schemathesis)
docker compose exec api pytest -m contract
```
- **Test requirements:** Integration tests automatically spin up ephemeral Postgres and Redis containers via `testcontainers-python`.


## Project Structure

The project follows a layered, domain-driven structure to separate business logic from transport and persistence layers.

- **Important directories/files:**
```
EVETO/
├── app/
│   ├── api/              # Routers, grouped by domain (auth, events, reservations, admin, partners, ops)
│   ├── core/             # Settings, security, middleware, exceptions
│   ├── db/               # Engine/session, base model
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic (unit-testable, DB-agnostic where possible)
│   ├── repositories/     # DB access layer
│   ├── workers/          # Dramatiq actors
│   └── main.py           # FastAPI application factory
├── alembic/              # Database migrations
├── tests/                # Unit, integration, and contract tests
├── adr/                  # Architectural Decision Records
├── mock_payment_provider/# Tiny standalone FastAPI service simulating payments
├── k6/                   # Load testing scripts
├── docker/               # API and Worker Dockerfiles
└── docker-compose.yml    # Local infrastructure orchestration
```


## Architecture

Eveto follows a **Layered Architecture** combined with an **App Factory Pattern** to ensure modularity and testability.

- **High-level design:**
  - **Transport Layer (`api`):** Handles HTTP requests, auth, and routing.
  - **Service Layer (`services`):** Contains business logic (e.g., calculating availability, TTL expiry). DB-agnostic.
  - **Data Layer (`repositories` & `models`):** Handles SQLAlchemy queries and DB persistence.
  - **Async Layer (`workers`):** Dramatiq actors process webhooks, send notifications, and sweep expired reservations.
- **Components:** FastAPI (API), PostgreSQL (Relational DB), Redis (Cache & Broker), Dramatiq (Task Queue), Mock Payment Provider (External Service).
- **Data flow:**
  `Client -> FastAPI Router -> Service -> Repository -> PostgreSQL`
  `Client -> FastAPI -> Mock Payment -> Webhook -> Dramatiq Queue -> Worker -> PostgreSQL`

---

## Deployment

- **Production setup:** In production, Docker Compose is replaced by container orchestration (e.g., Kubernetes or Docker Swarm). Secrets are injected via the orchestrator (never `.env` files in Git).
- **Deployment instructions:** 
  1. Build multi-stage Docker images for `api` and `worker`.
  2. Push to a container registry.
  3. Apply database migrations (`alembic upgrade head`).
  4. Deploy containers with injected OS environment variables.
- **CI/CD:** (Future scope) A GitHub Actions pipeline runs `uv run pre-commit`, unit tests, and integration tests on every Pull Request before allowing a merge to `main`.


## Known Issues

- **Limitations:**
  - **No Token Revocation:** JWTs are stateless and short-lived. There is no blacklist for active tokens.
  - **No Seat-Level Selection:** Reservations are based on ticket-type quantities, not specific row/seat numbers.
  - **No Real Payments:** The payment provider is mocked to intentionally simulate failure modes for testing.
- **Current problems:**
  - CI/CD pipeline is not yet implemented; testing is manual/local.
  - Dynamic/surge pricing is not yet supported.


## References and Definitions

- **ADR (Architectural Decision Record):** A document capturing a decision, its context, and its consequences. See the `/adr` folder.
- **Idempotency Key:** A unique client-generated key ensuring that retrying a failed `POST /reservations` request does not result in duplicate bookings.
- **Cache-Aside:** A caching pattern where the application checks the cache first; if data is missing, it queries the database and then populates the cache.
- **RS256:** An asymmetric JWT signing algorithm using a private key to sign and a public key to verify.


## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
