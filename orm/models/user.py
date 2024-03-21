from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, String, UUID, DateTime, Boolean

from orm.base_model import OrmBase


class User(OrmBase):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    password = Column(String)
    refresh_token = Column(String)
    reset_token = Column(String)
    source = Column(String)
    is_verified = Column(Boolean, default=False)