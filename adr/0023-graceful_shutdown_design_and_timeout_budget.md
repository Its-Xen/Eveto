## ADR-0023: Graceful Shutdown Design and Timeout Budget

Date: 2026-11-17 Status: Accepted

Related: ADR-0024 (Connection Pool Sizing)

## Context

When deploying a new version of the API, the orchestrator (Docker Compose for dev, Kubernetes in prod) sends SIGTERM to the container. The default behavior is:

    SIGTERM received
    Process stops accepting new connections
    Wait for in-flight requests to complete
    Close database connections, Redis pools, background workers
    SIGKILL arrives after the grace period (default 10s in Docker, 30s in Kubernetes)

If the shutdown is too abrupt:

    In-flight requests get 502 errors (bad UX, retries flood the new version)
    Database connections aren't returned to the pool (PostgreSQL has to wait for tcp_keepalive_time to detect dead connections)
    Background workers (Dramatiq) may leave messages in-flight without acknowledgment

If the shutdown waits too long:

    Deployments take excessive time
    Old and new versions run simultaneously for longer than necessary

## Decision

Use a layered shutdown timeout budget:
| Layer | Timeout | Purpose |
|-------|---------|---------|
| Uvicorn `--timeout-graceful-shutdown` | 30s | Wait for in-flight HTTP requests to complete |
| ASGI lifespan shutdown handler | runs after uvicorn stops accepting | Close DB engine, Redis pool, Dramatiq workers |
| Orchestrator grace period | 45s (K8s `terminationGracePeriodSeconds`) | Buffer beyond app-level timeout |


The 30s uvicorn timeout gives slow endpoints (payment provider calls up to 5s per ADR-0025, webhook delivery retries up to 10s) enough headroom to complete. The 45s orchestrator grace period ensures the process can exit cleanly even if lifespan shutdown takes additional time.
Health Check Separation

Split health checks into two endpoints to support graceful drain:

    /healthz (liveness): Returns 200 if the process is alive and the event loop is running. Does NOT check downstream dependencies. Used by orchestrator to decide whether to restart the container.
    /readyz (readiness): Returns 200 only if DB + Redis connections succeed. Used by load balancer to decide whether to route traffic.

During shutdown:

    SIGTERM received
    Uvicorn stops accepting new connections (load balancer sees connection refused)
    /readyz starts returning 503 (DB/Redis checks fail because lifespan is closing them)
    Load balancer stops routing traffic
    In-flight requests complete (up to 30s)
    Lifespan shutdown handler closes resources
    Process exits

## Lifespan Handler Responsibilities

The lifespan context manager:

    Startup: Initialize DB engine, Redis pool, Dramatiq workers, OTEL tracer provider
    Shutdown (in reverse order):
        Stop Dramatiq workers (drain in-progress messages, ~5s)
        Close Redis connection pool (returns connections to Redis server)
        Dispose DB engine (returns connections to PostgreSQL pool)
        Flush + shutdown OTEL BatchSpanProcessor (drops in-flight spans after timeout)

## Consequences

Positive:

    No 502 errors during deployments (in-flight requests complete)
    Database connections returned cleanly (no idle-in-transaction buildup)
    Dramatiq messages re-queued properly (no lost work)
    Health check separation allows fine-grained drain control

Negative:

    Deployments take up to 30s longer than hard kills
    Old and new versions run concurrently for ~30s during deploy
    Background worker drain adds 5s to shutdown window
    Requires orchestrator grace period > 30s (operational requirement)

Operational Requirements:

    Kubernetes: terminationGracePeriodSeconds: 45
    Docker Compose: stop_grace_period: 45s in compose file
    AWS ALB: deregistration delay ≥ 30s

Alternatives Considered
Hard kill (no graceful shutdown)

Rejected: causes 502 errors, leaked DB connections, lost Dramatiq messages.
Shorter timeout (10s)

Rejected: payment provider calls take up to 5s, webhook retries up to 10s — 10s timeout would interrupt legitimate slow operations.
Longer timeout (60s)

Rejected: extends deployment time unnecessarily; 30s is sufficient for all observed endpoint latencies (p99 < 2s under normal load, max ~5s for payment calls).

### References

- [Uvicorn graceful shutdown docs](https://uvicorn.dev/settings/)
- [Kubernetes termination grace period](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination)
- [PEP 3333 ASGI lifespan](https://asgi.readthedocs.io/en/latest/specs/lifespan.html)