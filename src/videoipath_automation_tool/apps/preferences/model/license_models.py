from pydantic import BaseModel, Field


class LicenseFile(BaseModel):
    """Model for License File"""

    TimeStamp: str
    VIP_PLAN: str = Field(..., alias="VIP-PLAN")
    VIP_OPTION_ALARM: bool = Field(..., alias="VIP-OPTION-ALARM")
    VIP_OPTION_MONITOR: bool = Field(..., alias="VIP-OPTION-MONITOR")
    VIP_OPTION_NMOS_RDS: int = Field(..., alias="VIP-OPTION-NMOS-RDS")
    VIP_OPTION_REDUNDANCY: bool = Field(..., alias="VIP-OPTION-REDUNDANCY")
    VIP_OPTION_SCHEDULED: bool = Field(..., alias="VIP-OPTION-SCHEDULED")
    VIP_OPTION_SDN: bool = Field(..., alias="VIP-OPTION-SDN")
    VIP_OPTION_TALLY: int = Field(..., alias="VIP-OPTION-TALLY")
    # pretty sure there are a lot more options... model is incomplete, so extra is allowed to not break the model
    STARTTIME: int
    ENDTIME: int
    Name: str
    Customer: str
    ID: str
    User: str
    Signature: str

    class Config:
        extra = "allow"
