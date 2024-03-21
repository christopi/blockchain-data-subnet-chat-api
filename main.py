import contextlib
import logging
from typing import AsyncIterator

import anyio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

import orm
from api.middleware import log_request_middleware
from api.routers import auth, chat, validator
from api.utils.exception_handlers import request_validation_exception_handler, http_exception_handler, \
    unhandled_exception_handler
from app.settings import settings
from app.tasks import load_data_task
from alembic.config import Config
from alembic import command


load_dotenv()
logging.basicConfig(level=logging.DEBUG)


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    run_migrations()
    orm.db_manager.init(settings.db_url_obj)
    async with anyio.create_task_group() as tg:
        tg.start_soon(load_data_task, orm.db_manager)
        yield
    await orm.db_manager.close()

description = """
This API allows users using Chain Insights to ask validators on the Omicron Subnetwork for Bittensor information on
the Bitcoin network.
"""


app = FastAPI(lifespan=lifespan,
              title="chat-api",
              description=description,
              swagger_ui_parameters={
    "filter": True,
    "syntaxHighlight.activate": True,
})

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat-api-dev.chain-insights.ai",
                   "https://chat-api-tst.chain-insights.ai",
                   "https://chat-api-preprod.chain-insights.ai",
                   "https://chat-app-dev.chain-insights.ai",
                   "https://chat-app-tst.chain-insights.ai",
                   "https://chat-app-preprod.chain-insights.ai",
                   "https://accounts.google.com",
                   "https://google.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.middleware("http")(log_request_middleware)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include your routers#
app.include_router(auth.router, tags=["authentication"], prefix="/api/v1")
app.include_router(chat.router, tags=["chat"], prefix="/api/v1")
app.include_router(validator.router, tags=["validators"], prefix="/api/v1")


@app.get("/health")
async def health():
    return {'status': 'up'}


@app.get("/")
async def docs_redirect():
    response = RedirectResponse(url='/docs')
    return response


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level="debug"
    )

