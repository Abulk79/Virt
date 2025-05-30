from typing import List

from fastapi import APIRouter, Depends
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.core.enums import ApiTags
from src.core.schemas import Ok
from src.dependencies import get_session
from src.order import service
from src.order.schemas import CreateOrderResponse, LimitOrderBody, LimitOrder, MarketOrder, L2OrderBook, MarketOrderBody

router = APIRouter()


@router.post("/order", tags=[ApiTags.ORDER], response_model=CreateOrderResponse)
async def create_order(body: LimitOrderBody | MarketOrderBody, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.create_order(body=body, request=request, db_session=db_session)


@router.get("/order", tags=[ApiTags.ORDER], response_model=List[LimitOrder | MarketOrder])
async def list_orders(request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.get_orders(request=request, db_session=db_session)


@router.get("/public/orderbook/{ticker}", tags=[ApiTags.PUBLIC], response_model=L2OrderBook)
async def get_orderbook(ticker: str, limit: int = 0, db_session: AsyncSession = Depends(get_session)):
    return await service.get_orderbook(ticker=ticker, limit=limit, db_session=db_session)


@router.get("/order/{order_id}", tags=[ApiTags.ORDER], response_model=LimitOrder | MarketOrder)
async def get_order(order_id: UUID4, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.get_order(order_id=order_id, request=request, db_session=db_session)


@router.delete("/order/{order_id}", tags=[ApiTags.ORDER], response_model=Ok)
async def cancel_order(order_id: UUID4, request: Request = None, db_session: AsyncSession = Depends(get_session)):
    return await service.cancel_order(order_id=order_id, request=request, db_session=db_session)