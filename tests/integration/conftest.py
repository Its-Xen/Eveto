import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session")
def postgres_container():
    """Spins up a real Postgres container for the whole test session."""

    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_container):
    """Creates an async engine connected to the test container."""
    # * Convert the testcontainer URL to use asyncpg
    async_url = postgres_container.get_connection_url().replace("+psycopg2", "+asyncpg")
    engine = create_async_engine(async_url)

    # * Wrap the Alembic command in a synchronous function
    def run_migrations():
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)
        command.upgrade(alembic_cfg, "head")

    # * Run the synchronous function in a separate thread!
    # * This allows env.py to use asyncio.run() without clashing with pytest-asyncio.
    await asyncio.to_thread(run_migrations)

    yield engine

    # * Teardown
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provides a clean database session for each test, and cleans up after."""
    async_session = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

        # * Clean up all data after the test runs to keep tests isolated!
        # (We don't drop the tables, just delete the rows)
        from sqlalchemy import text

        await session.execute(
            text("TRUNCATE TABLE venues, events, users, tickettypes CASCADE;")
        )
        await session.commit()
