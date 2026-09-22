ADR-0012: Integration Testing with Testcontainers

Date: 2026-9-22 Status: Accepted

Context

Integration tests need a database to verify SQL queries, constraints, and migrations. We need to choose how to provide this database during the testing phase without compromising the reliability of the tests or requiring developers to manually spin up databases.
Options Considered
1. SQLite In-Memory

    What it is: Replacing the Postgres engine with an in-memory SQLite database for tests.
    Strengths: Blazing fast; zero Docker required.
    Weaknesses: SQLite does not enforce foreign keys or data types the same way PostgreSQL does. Tests might pass in SQLite but fail in production. It masks real Postgres-specific bugs (like the ENUM type issues or SELECT ... FOR UPDATE locking).

2. Shared Test Database

    What it is: Running a local Postgres instance (e.g., via Docker Compose) and pointing the tests at it.
    Strengths: Tests against a real Postgres database.
    Weaknesses: State leaks between tests; developers must manually start/stop the database; parallel test execution is impossible due to race conditions on the shared DB.

3. Testcontainers

    What it is: A Python library that spins up a real, ephemeral Docker container for each test session and destroys it when finished.
    Strengths: 100% production parity (real Postgres); completely isolated (no state leaks); automatic cleanup; no manual Docker management.
    Weaknesses: Slower than SQLite (requires a few seconds to boot the container); requires Docker daemon to be running.

Decision

We choose Testcontainers.

For a project where database constraints and concurrency (Week 8) are critical, using SQLite is unacceptable because it hides real-world bugs. Testcontainers provides the highest confidence that our code will work in production without the manual overhead of managing a shared test database.
Consequences

    Developers must have Docker running to execute integration tests.
    The integration test suite will take slightly longer to start up compared to unit tests.
    We can safely test advanced Postgres features (like FOR UPDATE locking) knowing the database will behave exactly like production.

Under what conditions would this change?

If we move to a serverless architecture where cold-start times are critical, we might mock the database layer entirely and rely on a separate staging environment for integration testing.