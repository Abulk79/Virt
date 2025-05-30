from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

from src.user.utils import TOKEN_PREFIX

AUTHORIZATION_HEADER_NAME = "Authorization"

api_key_header = APIKeyHeader(name=AUTHORIZATION_HEADER_NAME, auto_error=False)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or not api_key.startswith(f"{TOKEN_PREFIX}"):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header.")

    return api_key