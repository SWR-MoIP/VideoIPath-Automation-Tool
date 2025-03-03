from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---- General ----
class ErrorDetails(BaseModel):
    msg: str
    type: str


class ResponseHeaderV2(BaseModel):
    """REST API v2 Response Header"""

    auth: bool
    caption: str  # Literal["Operation Successful", "Other Error"]
    code: Literal["OK", "OTHER_ERROR", "INVALID_REQUEST"]
    errorDetails: Optional[List[ErrorDetails]]
    id: str
    msg: Optional[List[str]]
    ok: bool
    user: str


# ---- Base ----
class ResponseV2(BaseModel, extra="forbid"):
    """REST API v2 Response Header"""

    header: ResponseHeaderV2


# ---- GET ----
class ResponseV2Get(ResponseV2):
    """REST API v2 GET Response"""

    data: dict


# ---- PATCH ----
class ResponseV2PatchDataItem(BaseModel):
    clientId: str = Field(alias="_clientId")
    id: str = Field(alias="_id")
    id_s: str = Field(alias="_id_s")
    rev: str = Field(alias="_rev")
    actionRef: dict
    msg: str
    res: str


class ResponseV2PatchDataStats(BaseModel):
    added: int
    ignored: int
    removed: int
    updated: int


class ResponseV2PatchData(BaseModel):
    items: List[ResponseV2PatchDataItem]
    mode: str
    stats: ResponseV2PatchDataStats
    validateOnly: bool


class ResponseV2Patch(ResponseV2):
    """REST API v2 PATCH Response"""

    result: ResponseV2PatchData


# --- POST ---
class ResponseV2Post(ResponseV2):
    """REST API v2 POST Response"""

    data: dict
