ADR-0001: Web Framework Choice (FastAPI)

Date: 2026-8-15 Status: Accepted
Context

Eveto is a ticketing platform where the core business logic revolves around high-concurrency ticket reservations (flash sales). The system must handle concurrent inventory decrements, asynchronous webhooks, and background jobs without blocking I/O. The framework must natively support async database drivers (asyncpg), have first-class support for data validation, and automatically generate OpenAPI documentation for external partner integrations. 
Options Considered
1. FastAPI

    What it is: A modern, async ASGI web framework built on Starlette and Pydantic.
    Strengths: Native async/await support; seamless integration with Pydantic v2 for strict typing; automatic OpenAPI/Swagger generation (crucial for the Partner API); dependency injection system that makes testing (overriding DB sessions) trivial.
    Weaknesses: Does not dictate project structure (can lead to messy architectures if not disciplined); relies on Pydantic v2, which had breaking changes from v1; smaller ecosystem of "batteries-included" plugins compared to older frameworks.

2. Django + Django Ninja (or Django REST Framework)

    What it is: A mature, batteries-included web framework, combined with an async-friendly API layer.
    Strengths: Incredible ORM, built-in admin panel, mature authentication, vast ecosystem.
    Weaknesses: Django's async support is still maturing, and doing raw async DB transactions (like SELECT ... FOR UPDATE with asyncpg) requires dropping to raw SQL or fighting the ORM. The overhead is heavy for a microservice-style architecture.

3. Litestar (formerly Starlite)

    What it is: A newer ASGI framework, also built on Starlette and Pydantic.
    Strengths: Extremely fast, excellent dependency injection, built-in support for things like OpenTelemetry and DTOs out of the box.
    Weaknesses: Much smaller community and ecosystem compared to FastAPI. Finding third-party tutorials or hiring engineers with Litestar experience is significantly harder.

Decision

We choose FastAPI. 

Eveto's core requirement is safe, concurrent database access and async I/O (Redis, Dramatiq, external webhooks). FastAPI's native async nature allows direct use of asyncpg and SQLAlchemy 2.0 async. Furthermore, its dependency injection system allows us to easily swap out the database session during integration testing, and its automatic OpenAPI generation fulfills the Partner API documentation requirement out of the box.
Consequences

    We accept that we must architect the folder structure ourselves (App Factory pattern, service/repo layers) since FastAPI does not enforce one.
    We are tightly coupled to Pydantic v2 for all request/response validation.
    We must be disciplined about using async def for all I/O-bound routes to avoid blocking the event loop.

Under what conditions would this change?

This would change if the project requirements shift to need a highly complex, stateful admin panel (where Django would shine), or if Pydantic v2's performance becomes a bottleneck under extreme load testing, forcing a migration to a non-Pydantic framework (like Litestar or pure Starlette).
