from typing import Literal

from pydantic import BaseModel


class Ok(BaseModel):
    success: Literal[True] = True