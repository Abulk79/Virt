from datetime import datetime

from pydantic import BaseModel


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime