import logging
from asyncio import Task
from typing import Optional

import pytest
import responses
from httpx import AsyncClient, ASGITransport
from yarl import URL

from app.settings import settings
from orm.session_manager import db_manager
from tests.db_utils import run_migrations

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('passlib').setLevel(logging.ERROR)


@pytest.fixture(scope="session", autouse=True)
def anyio_backend():
    return "asyncio", {"use_uvloop": True}


@pytest.fixture(scope="session")
def pg_url():
    """Provides base PostgreSQL URL for creating temporary databases."""
    url = settings.database_url.replace("chat_db", "test_chat_db")
    return URL(url)


@pytest.fixture(scope="session")
async def migrated_postgres(pg_url):
    """
    Applies migrations to the existing database.

    Has "session" scope, so is called only once per tests run.
    """
    async with run_migrations(pg_url) as migrated_db_url:
        yield migrated_db_url


@pytest.fixture(scope="session")
async def sessionmanager_for_tests(migrated_postgres):
    logging.debug("Starting sessionmanager_for_tests")
    db_manager.init(db_url=migrated_postgres)
    try:
        yield db_manager
    finally:
        logging.debug("Tearing down sessionmanager_for_tests")
        await db_manager.close()


@pytest.fixture()
async def session(sessionmanager_for_tests):
    async with db_manager.session() as session:
        yield session

"""
@pytest.fixture(scope="session", autouse=True)
def cleanup_database(sessionmanager_for_tests):
    yield
    sync_url = str(db_manager._engine.url).replace("***", settings.db_pass)
    sync_engine = create_engine(sync_url)
    with sync_engine.connect() as conn:
        for table in reversed(orm.OrmBase.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
"""

MIGRATION_TASK: Optional[Task] = None


@pytest.fixture()
async def app():
    from main import app

    yield app


@pytest.fixture()
async def client(session, app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def mock_validator():
    with responses.RequestsMock() as rsps:
        yield rsps
