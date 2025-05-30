from enum import Enum


class Direction(str, Enum):
    buy = "BUY"
    sell = "SELL"


class OrderStatus(str, Enum):
    new = "NEW"
    executed = "EXECUTED"
    partially_filled = "PARTIALLY_FILLED"
    canceled = "CANCELED"


class OrderType(str, Enum):
    market = "MARKET"
    limit = "LIMIT"
