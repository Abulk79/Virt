from typing import Dict
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


class BalanceResponse(RootModel[Dict[str, int]]):
    pass


class BalanceUpdateBody(BaseModel):
    user_id: UUID
    ticker: str = Field(example="MEMECOIN")
    amount: int = Field(gt=0)