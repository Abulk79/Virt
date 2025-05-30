import logging

from fastapi import Request, status, HTTPException
from pydantic import ValidationError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from src.core.utils import AUTHORIZATION_HEADER_NAME
from src.dependencies import session_factory
from src.user.utils import get_user

log = logging.getLogger(__name__)


async def auth_user(request: Request, call_next: RequestResponseEndpoint):
    if request.url.path.startswith("/api/v1/public") or request.url.path in ["/docs", "/openapi.json", "/favicon.ico", "/"]:
        return await call_next(request)

    api_key = request.headers.get(AUTHORIZATION_HEADER_NAME)

    if not api_key:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"{AUTHORIZATION_HEADER_NAME} header is missing.")

    async with session_factory() as db_session:
        try:
            user = await get_user(api_key=api_key, db_session=db_session)
        except Exception as e:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(e)}.")

        if not user:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

        request.state.user = user
        request.state.api_key = api_key

    return await call_next(request)


async def catch_exception(request: Request, call_next: RequestResponseEndpoint) -> JSONResponse:
    try:
        response = await call_next(request)
    except ValidationError as e:
        log.exception(e)
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": e.errors()}
        )
    except HTTPException as e:
        log.exception(e)
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(e)}
        )
    except ValueError as e:
        log.exception(e)
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": [{
                    "msg": str(e),
                    "loc": ["Unknown"],
                    "type": "value_error"
                }]
            },
        )
    except Exception as e:
        log.exception(e)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": [{
                    "msg": "An unexpected service error occurred",
                    "loc": ["Unknown"],
                    "type": "server_error"
                }]
            },
        )

    return response