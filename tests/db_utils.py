import contextlib
import logging
import uuid
from argparse import Namespace
from pathlib import Path
from typing import AsyncIterator, Optional, Union, List

import sqlalchemy as sa
from alembic.config import Config as AlembicConfig
from alembic import command
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy_utils.functions.database import (
    _set_url_database,
    make_url,
)
from sqlalchemy_utils.functions.orm import quote
from anyio.to_thread import run_sync
from yarl import URL
import orm

from app.settings import settings


@contextlib.asynccontextmanager
async def run_migrations(db_url: URL, **kwargs) -> AsyncIterator[str]:
    """Context manager for running migrations on an existing database and reverting them on exit."""
    # Configure Alembic
    alembic_cfg = alembic_config_from_url(str(db_url))

    # Run migrations
    await run_async_command("upgrade", alembic_cfg)

    try:
        yield str(db_url)
    finally:
        # Revert migrations
        await clean_database(db_url)
        await run_async_command("downgrade", alembic_cfg)


async def run_async_command(cmd: str, alembic_cfg: AlembicConfig) -> None:
    """Run an Alembic command asynchronously."""
    if cmd == "upgrade":
        await run_sync(command.upgrade, alembic_cfg, "head")
    elif cmd == "downgrade":
        await run_sync(command.downgrade, alembic_cfg, "base")
    else:
        raise ValueError(f"Unsupported command: {cmd}")


async def clean_database(db_url: URL) -> None:
    """Clean data from all tables in the database."""
    engine = create_async_engine(str(db_url))
    async with engine.begin() as conn:
        await conn.run_sync(orm.OrmBase.metadata.drop_all)
        await conn.run_sync(orm.OrmBase.metadata.create_all)
    await engine.dispose()
