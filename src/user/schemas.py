from pydantic import BaseModel, Field, UUID4

from src.user.enums import UserRole


class NewUser(BaseModel):
    name: str = Field(min_length=3)


class User(BaseModel):
    id: UUID4
    name: str
    role: UserRole
    api_key: str