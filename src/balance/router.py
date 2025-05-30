from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.balance import service
from src.balance.schemas import BalanceResponse, BalanceUpdateBody
from src.core.enums import ApiTags
from src.core.schemas import Ok
from src.dependencies import get_session

router = APIRouter()


@router.get("/balance", tags=[ApiTags.BALANCE], response_model=BalanceResponse)
async def get_balances(request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.get_balances(request=request, db_session=db_session)


@router.post("/admin/balance/deposit", tags=[ApiTags.ADMIN, ApiTags.BALANCE], response_model=Ok)
async def process_deposit(balance_update_request: BalanceUpdateBody, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.create_deposit(operation_info=balance_update_request, request=request, db_session=db_session)


@router.post("/admin/balance/withdraw", tags=[ApiTags.ADMIN, ApiTags.BALANCE], response_model=Ok)
async def process_withdraw(balance_update_request: BalanceUpdateBody, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.create_withdraw(operation_info=balance_update_request, request=request, db_session=db_session)