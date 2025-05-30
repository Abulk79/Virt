from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import ApiTags
from src.dependencies import get_session
from src.transaction import service
from src.transaction.schemas import Transaction

router = APIRouter()


@router.get("/public/transactions/{ticker}", tags=[ApiTags.PUBLIC], response_model=List[Transaction])
async def get_transaction_history(ticker: str, limit: int = 0, db_session: AsyncSession = Depends(get_session)):
    return await service.get_transaction_history(ticker=ticker, limit=limit, db_session=db_session)