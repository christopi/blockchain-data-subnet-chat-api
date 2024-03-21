import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from orm.base_model import OrmBase
from sqlalchemy.dialects.postgresql import UUID, INET


class Validator(OrmBase):
    __tablename__ = "validators"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    uid = Column(Integer, unique=True)
    name = Column(String, index=True)
    hotkey = Column(String, unique=True, index=True)
    ip = Column(INET)
    port = Column(Integer)
    last_picked = Column(DateTime, nullable=True)
    is_active = Column(Boolean)
