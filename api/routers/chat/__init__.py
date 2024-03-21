import datetime
import logging
import uuid
from typing import List

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy import func, select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import contains_eager
from starlette.responses import JSONResponse

from api.routers.auth import get_current_user
from api.schemas.chat import ChatReadSchema, MessageReadSchema, \
    MessageVariationCreateSchema, ChatCreateSchema, MessageCreateSchema, ChatCreateResponseSchema, ValidatorRespond, \
    MessageCreateResponseSchema, ChatListReadSchema
from orm import Validator
from orm.models.chat import Chat, MessageVariation, Message
from orm.session_manager import get_session
from utils.logger import logger

router = APIRouter()


@router.post("/chats", response_model=ChatCreateResponseSchema)
async def post_chat(chat: ChatCreateSchema, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    """
    Create a new chat.

    This endpoint allows users to create a new chat by providing a `ChatCreateSchema` object.

    **Parameters:**
    - `chat` (ChatCreateSchema): The chat details to create.
        - `message_content` (str): The content of the initial message in the chat.

    **Returns:**
    - `ChatCreateResponseSchema`: The created chat details.
        - `id` (UUID): ID of the created chat.
        - `name` (str): Name of the created chat.
        - `message_id` (UUID): ID of the initial message in the chat.
        - `reply` (str): The content of the initial message in the chat.
        - `created_at` (datetime): The timestamp of when the chat was created.

    **Raises:**
    - `HTTPException`: If an error occurs during chat creation (status code 500).

    **Example Request:**
    ```json
    POST /chats
    {
        "message_content": "Hello, how can I assist you today?"
    }
    ```

    **Example Response:**
    ```json
    {
        "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "name": "Room: Hello, how can I assist you today?",
        "message_id": "5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b",
        "reply": "Hello, how can I assist you today?",
        "created_at": "2023-06-15T10:30:00Z"
    }
    ```
    """
    try:
        validator = await pick_validator(db)

        db_chat = Chat(user_id=user.id, name=f"Room: {chat.message_content}", validator_id=validator.id)
        db.add(db_chat)
        await db.commit()
        await db.refresh(db_chat)

        reply = await post_msg_request_to_validator(str(user.id), chat.message_content, str(validator.ip), validator.port)

        validator.last_picked = datetime.datetime.now()

        if reply == "Please try again. Can't receive any responses due to the poor network connection.":
            reply = {"text": reply, 'miner_id': str(uuid.UUID(int=0))}


        db_message = Message(chat_id=db_chat.id, prompt=chat.message_content)
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)

        db_message_variation = MessageVariation(message_id=db_message.id, reply=reply['text'], validator_id=validator.id, miner=reply['miner_id'])
        db.add(db_message_variation)
        await db.commit()
        await db.refresh(db_message_variation)

        return ChatCreateResponseSchema(id=db_chat.id, name=db_chat.name, message_id=db_message.id,
                                        reply=reply['text'], created_at=db_message.created_at)
    except Exception as e:
        logging.error(f"Chat creation failure: {e}")
        await db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail":"Failed to create chat"})


@router.get("/chats/{chat_id}", response_model=ChatReadSchema)
async def get_chat(chat_id: UUID, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    """
    Fetch a chat by ID.

    This endpoint allows users to retrieve a chat and its associated messages by providing the `chat_id`.

    **Parameters:**
    - `chat_id` (UUID): ID of the chat to fetch.

    **Returns:**
    - `ChatReadSchema`: The chat details.
        - `id` (UUID): ID of the chat.
        - `name` (str): Name of the chat.
        - `user_id` (UUID): ID of the user who owns the chat.
        - `validator_id` (UUID): ID of the validator involved in the chat.
        - `created_at` (datetime): The timestamp of when the chat was created.
        - `updated_at` (datetime): The timestamp of when the chat was last updated.
        - `messages` (Optional[List[MessageReadSchema]]): List of messages in the chat.
            - `id` (UUID): ID of the message.
            - `chat_id` (UUID): ID of the chat the message belongs to.
            - `prompt` (str): The content of the message prompt.
            - `variations` (List[MessageVariationReadSchema]): List of variations for the message.
                - `id` (UUID): ID of the message variation.
                - `message_id` (UUID): ID of the message the variation belongs to.
                - `reply` (str): The content of the message variation reply.

    **Raises:**
    - `HTTPException`: If the chat is not found (status code 404) or the user is not authorized (status code 403).

    **Example Request:**
    ```
    GET /chats/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
    ```

    **Example Response:**
    ```json
    {
        "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "name": "Room: Hello, how can I assist you today?",
        "user_id": "c3d0f2b2-8c1a-4b31-9c5c-bd8c6e8f9a7b",
        "validator_id": "e5f1g3h4-9c5c-4b6d-8c1a-bd8c6e8f9a7b",
        "created_at": "2023-06-15T10:30:00Z",
        "updated_at": "2023-06-15T11:15:00Z",
        "messages": [
            {
                "id": "5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b",
                "chat_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                "prompt": "Hello, how can I assist you today?",
                "variations": [
                    {
                        "id": "7a1b2c3d-4e5f-6g7h-8i9j-0k1l2m3n4o5p",
                        "message_id": "5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b",
                        "reply": "I'm looking for information about your product."
                    }
                ]
            }
        ]
    }
    ```
    """
    try:
        chat_stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        chat_result = await db.execute(chat_stmt)
        db_chat = chat_result.scalars().first()

        if not db_chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if db_chat.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot perform this action")

        stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False).join(Message).options(
            contains_eager(Chat.messages).joinedload(Message.variations)
        )
        result = await db.execute(stmt)
        db_chat = result.unique().scalars().first()

        return db_chat
    except Exception as e:
        logging.error(f"Chat fetch error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get chats")



@router.put("/chats/{chat_id}", response_model=ChatReadSchema)
async def put_chat(chat_id: UUID, name: str, db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    """
    Update a chat's name.

    This endpoint allows users to update the name of a chat by providing the `chat_id` and the new `name`.

    **Parameters:**
    - `chat_id` (UUID): ID of the chat to update.
    - `name` (str): New name for the chat.

    **Returns:**
    - `ChatReadSchema`: The updated chat details.
        - `id` (UUID): ID of the chat.
        - `name` (str): Updated name of the chat.
        - `user_id` (UUID): ID of the user who owns the chat.
        - `validator_id` (UUID): ID of the validator involved in the chat.
        - `created_at` (datetime): The timestamp of when the chat was created.
        - `updated_at` (datetime): The timestamp of when the chat was last updated.
        - `messages` (Optional[List[MessageReadSchema]]): List of messages in the chat.
            - `id` (UUID): ID of the message.
            - `chat_id` (UUID): ID of the chat the message belongs to.
            - `prompt` (str): The content of the message prompt.
            - `variations` (List[MessageVariationReadSchema]): List of variations for the message.
                - `id` (UUID): ID of the message variation.
                - `message_id` (UUID): ID of the message the variation belongs to.
                - `reply` (str): The content of the message variation reply.

    **Raises:**
    - `HTTPException`: If the chat is not found (status code 404) or the user is not authorized (status code 403).

    **Example Request:**
    ```
    PUT /chats/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
    {
        "name": "Updated Chat Name"
    }
    ```


@router.get("/chats/{chat_id}/message", response_model=List[MessageReadSchema])
async def get_chat_messages(
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_current_user)
):
    """
    Retrieve messages in a chat.

    This endpoint allows users to retrieve all messages in a chat by providing the `chat_id`.

    **Parameters:**
    - `chat_id` (UUID): ID of the chat.
    - `skip` (int): How many messages to skip
    - `limit` (int): How many messages to fetch

    **Returns:**
    - `List[MessageReadSchema]`: List of messages in the chat.
        - `id` (UUID): Message ID.
        - `chat_id` (UUID): ID of the chat the message belongs to.
        - `prompt` (str): The content of the message prompt.
        - `variations` (List[MessageVariationReadSchema]): List of variations for the message.
            - `id` (UUID): ID of the message variation.
            - `message_id` (UUID): ID of the message the variation belongs to.
            - `reply` (str): The content of the message variation reply.

    **Raises:**
    - `HTTPException`: If the message is not found (status code 404) or the user is not authorized (status code 403).

    **Example Request:**
    ```
    GET /chats/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/message
    ```

    **Example Response:**
    ```json
    [
        {
            "id": "5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b",
            "chat_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            "prompt": "Hello, how can I assist you today?",
            "variations": [
                {
                    "id": "7a1b2c3d-4e5f-6g7h-8i9j-0k1l2m3n4o5p",
                    "message_id": "5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b",
                    "reply": "I'm looking for information about your product."
                }
            ]
        }
    ]
    ```
    """
    try:
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id, Message.is_deleted == False)
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        db_messages = result.scalars().all()

        if not db_messages:
            raise HTTPException(status_code=404, detail="Messages not found")

        return db_messages
    except Exception as e:
        logging.error(f"Failed to fetch messages: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Failed to get chat messages"})


@router.delete("/chats/{chat_id}/message/{message_id}")
async def delete_message(chat_id: UUID, message_id: UUID, db: AsyncSession = Depends(get_session),
                         user=Depends(get_current_user)):
    """
    Delete a message in a chat.

    This endpoint allows users to delete a specific message in a chat by providing the `chat_id` and `message_id`.

    **Parameters:**
    - `chat_id` (UUID): ID of the chat the message belongs to.
    - `message_id` (UUID): ID of the message to delete.

    **Returns:**
    - `dict`: Success message.
        - `message` (str): "Message deleted"

    **Raises:**
    - `HTTPException`: If the chat or message is not found (status code 404) or the user is not authorized (status code 403).

    **Example Request:**
    ```
    DELETE /chats/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/message/5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b
    ```

    **Example Response:**
    ```json
    {
        "message": "Message deleted"
    }
    ```
    """
    try:
        chat_stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        chat_res = await db.execute(chat_stmt)
        chat = chat_res.scalar_one_or_none()

        if not chat:
            raise HTTPException(status_code=404, detail="Chat does not exist")

        if chat.user_id != user.id:
            raise HTTPException(status_code=403, detail="User cannot perform this action")

        stmt = select(Message).where(Message.id == message_id, Message.chat_id == chat_id)
        result = await db.execute(stmt)
        db_message = result.scalar_one_or_none()
        if not db_message:
            raise HTTPException(status_code=404, detail="Message not found")
        db_message.is_deleted = True
        await db.commit()
        return {"message": "Message deleted"}
    except Exception as e:
        await db.rollback()
        logging.error(f"Failed to delete message: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"detail": "Failed to delete message"})


@router.put("/chats/{chat_id}/message/{message_id}", response_model=MessageVariationCreateSchema)
async def create_message_variation(chat_id: UUID, message_id: UUID, message_variation: MessageVariationCreateSchema,
                                   db: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    """
    Create a message variation.

    This endpoint allows users to create a variation of a message in a chat by providing the `chat_id`, `message_id`, and the variation details.

    **Parameters:**
    - `chat_id` (UUID): ID of the chat the message belongs to.
    - `message_id` (UUID): ID of the message for the variation.
    - `message_variation` (MessageVariationCreateSchema): The message variation details.
        - `content` (str): Message text

    **Returns:**
    - `MessageVariationCreateSchema`: The created message variation details.
        - `content` (str): Message variation text

    **Raises:**
    - `HTTPException`: If the chat or message is not found (status code 404) or the user is not authorized (status code 403).

    **Example Request:**
    ```json
    PUT /chats/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/message/5c2d9b52-6f8c-4b6d-9c5c-bd8c6e8f9a7b
    {
        "content": "This is a variation of the message"
    }
    ```

    **Example Response:**
    ```json
    {
        "content": "This is a variation of the message"
    }
    ```
    """
    try:
        chat_stmt = select(Chat).where(Chat.id == chat_id, Chat.is_deleted == False)
        chat_result = await db.execute(chat_stmt)
        chat = chat_result.scalar_one_or_none()

        if chat.user_id != user.id:
            raise HTTPException(status_code=403, detail="User cannot perform this action")

        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        v_stmt = select(Validator).where(Validator.id == chat.validator_id)
        v_result = await db.execute(v_stmt)
        validator = v_result.scalars().first()

        msg_stmt = select(Message).where(Message.id == message_id, Message.chat_id == chat_id,
                                         Message.is_deleted == False)
        msg_result = await db.execute(msg_stmt)
        msg = msg_result.scalar_one_or_none()

        lv_stmt = select(MessageVariation).where(MessageVariation.message_id == msg.id).order_by(
            desc(MessageVariation.created_at)).limit(1)
        lv_result = await db.execute(lv_stmt)
        last_variation = lv_result.scalar_one()

        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        reply = await post_msg_request_to_validator(user.id, message_variation.content, str(validator.ip), validator.port, True, str(last_variation.miner))

        validator.last_picked = datetime.datetime.now()

        if reply == "Please try again. Can't receive any responses due to the poor network connection.":
            reply = {"miner_id": str(uuid.UUID(int=0)), "text": reply}

        db_message_variation = MessageVariation(message_id=message_id, validator_id=chat.validator_id, reply=reply['text'], miner=reply['miner_id'])
        msg.updated_at = datetime.datetime.utcnow()
        chat.updated_at = datetime.datetime.utcnow()
        db.add(db_message_variation)
        await db.commit()
        await db.refresh(db_message_variation)
        return MessageVariationCreateSchema(
            content=db_message_variation.reply
        )
    except Exception as e:
        logging.error(f"Failed to create message variation: {e.__traceback__}")
        await db.rollback()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"detail": "Failed to create variation"})
