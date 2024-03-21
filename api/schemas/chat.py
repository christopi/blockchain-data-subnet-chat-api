from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from uuid import UUID


class ChatCreateSchema(BaseModel):
    message_content: str


class ChatCreateResponseSchema(BaseModel):
    id: UUID
    name: str
    message_id: UUID
    reply: str
    created_at: datetime


class ChatUpdateSchema(BaseModel):
    user_id: UUID
    validator_id: UUID
    name: str


class MessageUpdateSchema(BaseModel):
    content: str


class MessageVariationCreateSchema(BaseModel):
    content: str


class MessageVariationReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    message_id: UUID
    created_at: datetime
    reply: str


class MessageCreateSchema(BaseModel):
    content: str


class MessageCreateResponseSchema(BaseModel):
    chat_id: UUID
    message_id: UUID
    content: str


class MessageReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    chat_id: UUID
    prompt: str
    created_at: datetime
    variations: List[MessageVariationReadSchema]


class ChatReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    user_id: UUID
    validator_id: UUID
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageReadSchema]]

class ChatListReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total: int
    skip: int
    limit: int
    items: List[ChatReadSchema]


class MessageVariationUpdateSchema(BaseModel):
    content: str

class ValidatorRespond(BaseModel):
    # id: int
    # chat_id: int
    # message_id: int
    respond: str