from datetime import datetime
from uuid import UUID

import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, UUID
from sqlalchemy.orm import relationship

from orm.base_model import OrmBase


class Chat(OrmBase):
    __tablename__ = "chats"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    name = Column(String)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(UUID, ForeignKey("users.id"))
    validator_id = Column(UUID, ForeignKey("validators.id"))
    user = relationship("User", lazy="selectin")
    validator = relationship("Validator", lazy="selectin")
    messages = relationship("Message", back_populates="chat")


class Message(OrmBase):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    chat_id = Column(UUID, ForeignKey("chats.id"))
    prompt = Column(String, default='')
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")
    variations = relationship("MessageVariation", back_populates="message", lazy="selectin")


class MessageVariation(OrmBase):
    __tablename__ = "message_variations"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=sqlalchemy.text("gen_random_uuid()"))
    message_id = Column(UUID, ForeignKey("messages.id"))
    validator_id = Column(UUID, ForeignKey("validators.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    reply = Column(String, default='')
    miner = Column(String, default='', index=True)
    message = relationship("Message", back_populates="variations", lazy="selectin")
