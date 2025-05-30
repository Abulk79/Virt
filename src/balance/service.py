from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.requests import Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from fastapi import HTTPException, status


from src.balance.schemas import BalanceResponse, BalanceUpdateBody
from src.core.schemas import Ok
from src.dependencies import get_session
from src.instrument.models import Instrument
from src.balance.models import Balance


async def get_balances(*, request: Request, db_session: AsyncSession = Depends(get_session)) -> BalanceResponse:
    pass

async def create_deposit(*, operation_info: BalanceUpdateBody, request: Request, db_session: AsyncSession = Depends(get_session)) -> Ok:
    try:
        instrument = await db_session.execute(
            select(Instrument.id).where(Instrument.ticker == operation_info.ticker)
        )
        instrument_id = instrument.scalar_one()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument with ticker {operation_info.ticker} not found"
        )

    balance = await db_session.execute(
        select(Balance).where(
            Balance.user_id == operation_info.user_id,
            Balance.instrument_id == instrument_id
        )
    )
    balance = balance.scalar_one_or_none()

    if balance is None:
        new_balance = Balance(
            user_id=operation_info.user_id,
            instrument_id=instrument_id,
            amount=operation_info.amount
        )
        db_session.add(new_balance)
    else:
        await db_session.execute(
            update(Balance)
            .where(
                Balance.user_id == operation_info.user_id,
                Balance.instrument_id == instrument_id
            )
            .values(amount=Balance.amount + operation_info.amount)
        )

    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update balance"
        )

    return Ok(success=True)

async def create_withdraw(*, operation_info: BalanceUpdateBody, request: Request, db_session: AsyncSession = Depends(get_session)) -> Ok:
    try:
        instrument = await db_session.execute(
            select(Instrument.id).where(Instrument.ticker == operation_info.ticker)
        )
        instrument_id = instrument.scalar_one()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument with ticker {operation_info.ticker} not found"
        )

    balance = await db_session.execute(
        select(Balance).where(
            Balance.user_id == operation_info.user_id,
            Balance.instrument_id == instrument_id
        )
    )
    balance = balance.scalar_one_or_none()

    if balance is None or balance.amount < operation_info.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds"
        )

    await db_session.execute(
        update(Balance)
        .where(
            Balance.user_id == operation_info.user_id,
            Balance.instrument_id == instrument_id
        )
        .values(amount=Balance.amount - operation_info.amount)
    )

    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update balance"
        )

    return Ok(success=True)