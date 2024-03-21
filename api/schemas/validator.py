from pydantic import BaseModel, ConfigDict, IPvAnyAddress
from uuid import UUID


class ValidatorCreateSchema(BaseModel):
    name: str
    uid: int


class ValidatorReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uid: int
    name: str
    ip: IPvAnyAddress
    port: int