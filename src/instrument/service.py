from typing import List
import re
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.status import HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from src.core.schemas import Ok
from src.dependencies import get_session
from src.instrument.schemas import Instrument
from src.instrument.models import Instrument as InstrumentDAL
from src.order.models import Order as OrderDAL
from src.balance.models import Balance as BalanceDAL
from src.transaction.models import Transaction as TransactionDAL


async def add_instrument(*, add_instrument_request: Instrument, db_session: AsyncSession = Depends(get_session)) -> Ok:
    existing_instrument = (
        await db_session.execute(select(InstrumentDAL)
        .where(InstrumentDAL.name == add_instrument_request.name))
        ).scalar_one_or_none()

    if existing_instrument:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail=[{
                "loc": ["body", "name"],
                "msg": f"Instrument with name '{add_instrument_request.name}' already exists.",
                "type": "value_error"
            }]
        )

    ticker_pattern = r'^[A-Z]{2,10}$'
    if not re.match(ticker_pattern, add_instrument_request.ticker):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{
                "loc": ["body", "ticker"],
                "msg": "Ticker must be 2-10 uppercase letters",
                "type": "value_error"
            }]
        )

    new_instrument = InstrumentDAL(
        id=uuid.uuid4(),
        name=add_instrument_request.name,
        ticker=add_instrument_request.ticker,
        delisted=False
    )

    db_session.add(new_instrument)
    await db_session.commit()

    return Ok(success=True)

async def get_instruments(db_session: AsyncSession = Depends(get_session)) -> List[Instrument]:
    result = await db_session.execute(select(InstrumentDAL))
    instruments = result.scalars().all()

    return [
        Instrument(
            name=instrument.name,
            ticker=instrument.ticker
        )
        for instrument in instruments
    ]


async def delete_instrument(*, ticker: str, request: Request, db_session: AsyncSession = Depends(get_session)) -> Ok:
    async with db_session.begin():
        existing_instrument = (
            await db_session.execute(
                select(InstrumentDAL).where(InstrumentDAL.ticker == ticker)
            )
        ).scalar_one_or_none()

        if existing_instrument is None:
            raise HTTPException(
                status_code=request.status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Instrument not found",
                    "message": f"Instrument with ticker '{ticker}' does not exist."
                }
            )

        await db_session.execute(
            delete(OrderDAL).where(OrderDAL.instrument_id == existing_instrument.id)
        )

        await db_session.execute(
            delete(BalanceDAL).where(BalanceDAL.instrument_id == existing_instrument.id)
        )

        await db_session.execute(
            delete(TransactionDAL).where(TransactionDAL.instrument_id == existing_instrument.id)
        )

        await db_session.delete(existing_instrument)

    return Ok(success=True)