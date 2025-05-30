import uuid

from datetime import datetime

from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.status import HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from src.user.enums import UserRole
from src.user.models import User as UserDAL
from src.user.schemas import NewUser
from src.user.schemas import User as UserDTO
from src.user.utils import generate_api_key


async def create_user(*, user: NewUser, db_session: AsyncSession) -> UserDTO:
    existing_user = (await db_session.execute(select(UserDAL).where(UserDAL.username == user.name))).scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail=f"User with username '{user.name}' already exists.")

    key_id, api_key = generate_api_key()

    new_user = UserDAL(
        id=uuid.uuid4(),
        username=user.name,
        role=UserRole.user,
        api_key=key_id,
        created_at=datetime.now())

    db_session.add(new_user)
    await db_session.commit()

    return UserDTO(id=new_user.id, name=new_user.username, role=new_user.role, api_key=api_key)


async def delete_user(*, user_id: UUID4, request: Request, db_session: AsyncSession) -> UserDTO:
    user = request.state.user

    if not user:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="User not set in current context.")

    existing_user = (await db_session.execute(select(UserDAL).where(UserDAL.id == user_id))).scalar_one_or_none()

    if existing_user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"User with id '{user_id}' doesn't exist.")

    if existing_user.id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="You don't have permission to delete specified user.")

    await db_session.delete(existing_user)
    await db_session.commit()

    return UserDTO(id=user_id, name=existing_user.username, role=existing_user.role, api_key=existing_user.api_key)