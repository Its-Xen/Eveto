ADR-0011: Testing Pyramid Strategy

Date: 2026-9-15 Status: Accepted

Context

Eveto requires a testing strategy that provides confidence in the system's correctness without slowing down the development pipeline. We need to balance fast, isolated unit tests with slower, realistic integration and contract tests.
Options Considered
1. The Testing Pyramid (Standard)

    What it is: A base of many fast, isolated unit tests (mocking DB/external services), a smaller layer of integration tests (hitting a real test DB), and a tiny peak of end-to-end/contract tests.
    Strengths: Fast feedback loop; developers know within seconds if business logic is broken; cheap to run.
    Weaknesses: Unit tests can sometimes pass while the real database fails (false confidence) if mocks are inaccurate.

2. The Testing Trophy (Integration Heavy)

    What it is: Fewer unit tests, heavy emphasis on integration tests with a real database.
    Strengths: High confidence that the application actually works in a real environment.
    Weaknesses: Slower to run; requires spinning up Docker containers for every test run; makes Test-Driven Development (TDD) feel sluggish.

3. Ice Cream Cone (Manual/UI Heavy)

    What it is: Relying mostly on manual testing or end-to-end UI tests.
    Weaknesses: Very slow, brittle, and impossible to automate in CI/CD pipelines efficiently.

Decision

We choose The Testing Pyramid.

    Unit Tests (pytest -m unit): Used for business logic and service layers. We will mock the repository layer (AsyncSession) to test pricing, availability math, and validation rules in milliseconds.
    Integration Tests (pytest -m integration): Used for repositories and API endpoints. We will use testcontainers to spin up real PostgreSQL/Redis containers to verify SQL queries, constraints, and migrations.
    Contract Tests (pytest -m contract): Used for the Partner API to ensure OpenAPI schemas are strictly adhered to.

Consequences

    We accept the risk that unit tests might occasionally have false positives due to mocking.
    We mitigate this by running integration tests against a real database to catch SQL syntax errors or constraint violations that mocks might miss.
    Coverage targets will be strictly enforced on the Service layer (business logic), not on boilerplate CRUD routes.

Under what conditions would this change?

If the application becomes highly distributed (microservices) where network boundaries are the primary source of bugs, we would shift towards the Testing Trophy (more integration/contract tests).