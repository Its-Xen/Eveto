ADR-0002: Dependency and Environment Tool (uv)

Date: 2026-8-16 Status: Accepted
Context

Eveto requires a dependency manager that can handle a complex stack (FastAPI, SQLAlchemy, OpenTelemetry, testcontainers). The development workflow relies heavily on Docker. A major pain point in modern Python development is the slow resolution and installation of dependencies, which drastically slows down Docker builds and CI/CD pipelines. We need a tool that provides strict lockfiles for reproducible builds, manages virtual environments, and is fast.
Options Considered
1. uv

    What it is: An extremely fast Python package installer and resolver, written in Rust by Astral.
    Strengths: 10x-100x faster than pip/Poetry; supports PEP 621 standard (pyproject.toml); generates a universal uv.lock file; manages Python versions itself (can download Python 3.12 automatically); excellent Docker caching support.
    Weaknesses: Relatively new tool; lacks the extensive plugin ecosystem of Poetry (e.g., publishing to private registries has some edge cases).

2. Poetry

    What it is: The de facto standard Python dependency manager for years.
    Strengths: Very mature, huge community, handles virtual environments and publishing packages to PyPI flawlessly.
    Weaknesses: Notoriously slow dependency resolver; Docker builds using Poetry often take minutes due to lack of global caching; does not manage the Python runtime version itself.

3. Pipenv

    What it is: An older dependency manager by Python Packaging Authority.
    Strengths: Creates Pipfile and Pipfile.lock.
    Weaknesses: Largely abandoned by the community; incredibly slow; frequently gets stuck in dependency resolution deadlocks; poor support for modern Docker workflows.

4. Raw pip + requirements.txt

    What it is: The standard library approach.
    Strengths: Works everywhere; zero third-party dependencies.
    Weaknesses: No true lockfile (doesn't lock transitive dependencies unless using pip freeze, which is brittle); manual virtual environment management.

Decision

We choose uv.

Speed is critical for developer experience. uv reduces Docker build times from minutes to seconds. Its adherence to the pyproject.toml standard means we aren't locked into a proprietary config format. Furthermore, uv's ability to download and pin specific Python versions (via .python-version) ensures that local dev, Docker, and CI all use the exact same runtime (Python 3.12).
Consequences

    We rely on a relatively new tool (uv). We may encounter edge cases with very bleeding-edge libraries, though none are expected in this stack.
    Developers must install uv locally rather than relying on pre-installed pip.
    We get a strictly reproducible uv.lock file that guarantees Docker builds are identical across all machines.

Under what conditions would this change?

If uv becomes unmaintained, or if we need to publish this project as a public package to PyPI and uv's publishing capabilities prove inadequate, we would migrate to Poetry. However, the pyproject.toml standard makes this migration relatively painless.