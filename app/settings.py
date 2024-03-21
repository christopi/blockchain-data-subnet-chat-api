import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "Blockchain Insights Chat API"
    app_host: str = os.getenv("APP_HOST", "localhost")
    host_url: str = os.getenv("HOST_URL", "https://chat-api-dev.chain-insights.ai")
    app_port: int = 8000
    db_user: str = os.getenv("POSTGRES_USER", "postgres")
    db_pass: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_host: str = os.getenv("DATABASE_URL", "localhost")
    db_name: str = os.getenv("POSTGRES_DB", "chat_db")
    secret_key: str = os.getenv("SECRET_KEY", "njsreob45309")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    sendgrid_key: str = os.getenv("SENDGRID_API_KEY", "")
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    hotkeys_api_url: str = os.getenv("HOTKEYS_API_URL", "")
    hotkeys_api_key: str = os.getenv("HOTKEYS_API_KEY", "")

    db_url_obj: URL = URL.create(
            "postgresql+asyncpg",
            username=os.environ.get("POSTGRES_USER"),
            password=os.environ.get("POSTGRES_PASSWORD"),
            host=os.environ.get("POSTGRES_HOST"),
            port=os.environ.get("POSTGRES_PORT"),
            database=os.environ.get("POSTGRES_DB")
        )

    database_url: str = f"{db_url_obj.drivername}://{db_url_obj.username}:{db_url_obj.password}@{db_url_obj.host}:{db_url_obj.port}/{db_url_obj.database}"

    project_root: Path = Path(__file__).parent.parent.resolve()

    model_config = SettingsConfigDict(env_file=".env", extra='allow')


settings = Settings()
