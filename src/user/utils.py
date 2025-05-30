import hashlib
import hmac
import uuid

from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from src import config
from src.user.models import User as UserDAL

TOKEN_PREFIX = "TOKEN"

def get_secret_key() -> str:
    secret_key = config.SECRET_KEY

    if secret_key is None:
        raise ValueError("SECRET_KEY environment variable is not set.")

    return secret_key


def generate_api_key() -> Tuple[str, str]:
    key_id = uuid.uuid4().hex
    secret = get_secret_key()

    signature = hmac.new(str(secret).encode(), key_id.encode(), hashlib.sha256).hexdigest()
    full_api_key = f"{TOKEN_PREFIX} {key_id}.{signature}"

    return key_id, full_api_key


async def get_user(api_key: str, db_session: AsyncSession) -> UserDAL:
    try:
        _, key_part = api_key.split(" ", 1)
        key_id, signature = key_part.split(".")
    except ValueError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    secret = get_secret_key()
    expected_sig = hmac.new(str(secret).encode(), key_id.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    return (await db_session.execute(select(UserDAL).filter_by(api_key=key_id))).scalar_one_or_none()