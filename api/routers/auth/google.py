from authlib.integrations.starlette_client import OAuth
from app.settings import settings


google_oauth = OAuth().register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    authorize_state=settings.secret_key,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid email profile'},
)
