from datetime import datetime
from typing import List

from pydantic import BaseModel, UUID4, Field

from src.order.enums import Direction, OrderStatus


class LimitOrderBody(BaseModel):
    user_id: UUID4
    direction: Direction
    ticker: str
    qty: int = Field(ge=1)
    price: float = Field(gt=0)


class LimitOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0


class Level(BaseModel):
    price: int
    qty: int


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]


class MarketOrderBody(BaseModel):
    user_id: UUID4
    direction: Direction
    ticker: str
    qty: int = Field(ge=1)


class MarketOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody


class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: UUID4