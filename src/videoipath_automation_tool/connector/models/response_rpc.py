from typing import List, Optional

from pydantic import BaseModel


class Header(BaseModel):
    """RPC Response Header"""

    caption: str  # Literal["Operation Successful", "Other Error"]
    id: int
    msg: List[str]
    ok: bool
    status: str  # Literal["OK", "ERROR", "INVALID_REQUEST"]


class ResponseRPC(BaseModel, extra="forbid"):
    """RPC Response"""

    header: Header
    data: Optional[dict | bool] = None
