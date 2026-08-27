ADR-0003: Data Layer Choice (SQLAlchemy 2.0 Async)

Date: 2026-8-27 Status: Accepted
Context

Eveto's core business logic revolves around high-concurrency ticket reservations (flash sales). To prevent overselling, the system must execute atomic database decrements using row-level locking (SELECT ... FOR UPDATE). The web framework (FastAPI) is entirely async. The data layer must not block the event loop during I/O, must support strong typing, and must allow for complex querying capabilities.
Options Considered
1. SQLAlchemy 2.0 (Async)

    What it is: The latest major version of the standard Python ORM, featuring a native async API, AsyncSession, and modern typed syntax (Mapped / mapped_column).
    Strengths: Full support for async/await; native integration with asyncpg; excellent support for explicit row-level locking (with_for_update()); strong typing support for IDE and Mypy; seamless integration with Alembic for migrations.
    Weaknesses: Can be verbose; the unit-of-work pattern (Sessions) can be tricky to manage correctly in a stateless API; historically had a steep learning curve.

2. Sync SQLAlchemy (in a Threadpool)

    What it is: Using standard synchronous SQLAlchemy, relying on Starlette/FastAPI to run the blocking DB calls in a separate threadpool.
    Strengths: Simpler mental model; massive ecosystem of legacy code and tutorials.
    Weaknesses: Threadpool context switching adds overhead; under high concurrency (flash sales), threads can become exhausted, leading to request timeouts; less efficient than native async I/O.

3. Raw asyncpg

    What it is: Bypassing an ORM entirely and writing raw SQL queries directly against the asyncpg driver.
    Strengths: Maximum performance; zero ORM overhead; absolute control over the exact SQL executed.
    Weaknesses: Loss of strong typing; no built-in migrations; heavy boilerplate for mapping SQL rows to Python objects; highly susceptible to SQL injection if not extremely careful; much harder to maintain as the schema grows.

4. SQLModel

    What it is: A library by FastAPI's author that combines Pydantic and SQLAlchemy into a single model.
    Strengths: Reduces boilerplate by using one model for both API validation and DB tables.
    Weaknesses: Built on SQLAlchemy 1.4 paradigms; mixes concerns (DB schema vs. API schema should often diverge); abstracts away advanced SQLAlchemy features, making complex queries (like FOR UPDATE) more difficult to implement.

Decision

We choose SQLAlchemy 2.0 (Async).

Eveto requires complex, safe concurrency controls (pessimistic locking) and strong typing. SQLAlchemy 2.0 provides with_for_update() natively, integrates perfectly with asyncpg to prevent event-loop blocking, and its new Mapped syntax satisfies strict Mypy requirements. Keeping Pydantic schemas separate from SQLAlchemy models enforces a clean boundary between API transport and database persistence.
Consequences

    We accept the verbosity of defining both SQLAlchemy models and Pydantic schemas.
    We must carefully manage the AsyncSession lifecycle (per-request) to avoid lazy-loading exceptions in async contexts.
    We must explicitly configure expire_on_commit=False to prevent async lazy-load crashes.

Under what conditions would this change?

If the application's data access patterns became purely key-value based (requiring no complex joins or relations), we might migrate to a simpler NoSQL driver. Alternatively, if performance profiling shows that ORM overhead is the primary bottleneck under extreme load, we would drop the ORM and use raw asyncpg for the specific bottlenecked endpoints.