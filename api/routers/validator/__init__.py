import itertools
from typing import List

import requests
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.schemas.validator import ValidatorReadSchema
from orm.models.validator import Validator
from orm.session_manager import get_session as get_db


router = APIRouter()


@router.get("/validators/", response_model=List[ValidatorReadSchema])
async def get_validators(db: AsyncSession = Depends(get_db)):
    """
    Fetch all validators.

    This endpoint retrieves a list of all existing validators.

    **Returns:**
    - `List[ValidatorReadSchema]`: List of validators.
        - `id` (UUID): ID of the validator.
        - `uid` (int): Unique identifier of the validator.
        - `name` (str): Name of the validator.
        - `ip` (IPvAnyAddress): IP address of the validator.
        - `port` (int): Port number of the validator.

    **Example Response:**
    ```json
    [
        {
            "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            "uid": 1,
            "name": "Validator 1",
            "ip": "192.168.0.1",
            "port": 8000
        },
        {
            "id": "b1ffcd00-0d1e-2f3g-4h5i-6j7k8l9m0n1p",
            "uid": 2,
            "name": "Validator 2",
            "ip": "192.168.0.2",
            "port": 8001
        }
    ]
    ```
    """
    stmt = select(Validator)
    result = await db.execute(stmt)
    db_validators = result.scalars()

    return db_validators or []


@router.get("/validators/{validator_id}", response_model=ValidatorReadSchema)
async def get_validator_by_id(validator_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetch a validator by ID.

    This endpoint retrieves a specific validator by providing the `validator_id`.

    **Parameters:**
    - `validator_id` (UUID): ID of the validator to fetch.

    **Returns:**
    - `ValidatorReadSchema`: The validator details.
        - `id` (UUID): ID of the validator.
        - `uid` (int): Unique identifier of the validator.
        - `name` (str): Name of the validator.
        - `ip` (IPvAnyAddress): IP address of the validator.
        - `port` (int): Port number of the validator.

    **Raises:**
    - `HTTPException`: If the validator is not found (status code 404).

    **Example Response:**
    ```json
    {
        "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "uid": 1,
        "name": "Validator 1",
        "ip": "192.168.0.1",
        "port": 8000
    }
    ```
    """
    stmt = select(Validator).where(Validator.id == validator_id)
    result = await db.execute(stmt)
    db_agent = result.scalar_one_or_none()

    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return db_agent or []

@router.get("/validators/uid/{uid}", response_model=ValidatorReadSchema)
async def get_validator_by_uid(uid: int, db: AsyncSession = Depends(get_db)):
    """
    Fetch a validator by UID.

    This endpoint retrieves a specific validator by providing the `uid`.

    **Parameters:**
    - `uid` (int): Unique identifier of the validator to fetch.

    **Returns:**
    - `ValidatorReadSchema`: The validator details.
        - `id` (UUID): ID of the validator.
        - `uid` (int): Unique identifier of the validator.
        - `name` (str): Name of the validator.
        - `ip` (IPvAnyAddress): IP address of the validator.
        - `port` (int): Port number of the validator.

    **Raises:**
    - `HTTPException`: If the validator is not found (status code 404).

    **Example Response:**
    ```json
    {
        "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "uid": 1,
        "name": "Validator 1",
        "ip": "192.168.0.1",
        "port": 8000
    }
    ```
    """
    stmt = select(Validator).where(Validator.uid == uid)
    result = await db.execute(stmt)
    db_agent = result.scalar_one_or_none()

    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return db_agent or []
