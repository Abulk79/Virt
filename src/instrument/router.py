from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core.enums import ApiTags
from src.core.schemas import Ok
from src.dependencies import get_session
from src.instrument import service
from src.instrument.schemas import Instrument

router = APIRouter()


@router.post("/admin/instrument", tags=[ApiTags.ADMIN], response_model=Ok)
async def add_instrument(add_instrument_request: Instrument, db_session: AsyncSession = Depends(get_session)):
    return await service.add_instrument(add_instrument_request=add_instrument_request, db_session=db_session)


@router.get("/public/instrument", tags=[ApiTags.PUBLIC], response_model=List[Instrument])
async def get_instruments(db_session: AsyncSession = Depends(get_session)):
    return await service.get_instruments(db_session=db_session)


@router.delete("/admin/instrument/{ticker}", tags=[ApiTags.ADMIN], response_model=Ok)
async def delete_instrument(ticker: str, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.delete_instrument(ticker=ticker, request=request, db_session=db_session)