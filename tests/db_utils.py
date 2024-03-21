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


def make_alembic_config(
    cmd_opts: Namespace, base_path: Union[str, Path] = settings.project_root
) -> AlembicConfig:
    # Replace path to alembic.ini file to absolute
    base_path = Path(base_path)
    if not Path(cmd_opts.config).is_absolute():
        cmd_opts.config = str(base_path.joinpath(cmd_opts.config).absolute())
    config = AlembicConfig(
        file_=cmd_opts.config,
        ini_section=cmd_opts.name,
        cmd_opts=cmd_opts,
    )
    # Replace path to alembic folder to absolute
    alembic_location = config.get_main_option("script_location")
    if not Path(alembic_location).is_absolute():
        config.set_main_option(
            "script_location", str(base_path.joinpath(alembic_location).absolute())
        )
    if cmd_opts.pg_url:
        #cmd_opts.pg_url = str(cmd_opts.pg_url).replace("***", settings.db_pass).replace("chat_db", "test_chat_db")
        config.set_main_option("sqlalchemy.url", cmd_opts.pg_url)
    return config


def alembic_config_from_url(pg_url: Optional[str] = None) -> AlembicConfig:
    """Provides python object, representing alembic.ini file."""
    cmd_options = Namespace(
        config="alembic.ini",  # Config file name
        name="alembic",  # Name of section in .ini file to use for Alembic config
        pg_url=pg_url,  # DB URI
        raiseerr=True,  # Raise a full stack trace on error
        x=None,  # Additional arguments consumed by custom env.py scripts
    )
    return make_alembic_config(cmd_opts=cmd_options)


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
