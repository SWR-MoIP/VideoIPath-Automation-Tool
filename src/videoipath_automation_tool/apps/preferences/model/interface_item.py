from typing import Optional

from pydantic import BaseModel, IPvAnyAddress
from pydantic_extra_types.mac_address import MacAddress


class InterfaceItem(BaseModel):
    name: str
    address: IPvAnyAddress
    broadcast: str
    gwAddress: str
    gwFlags: int
    inet: str
    mac: MacAddress
    netmask: Optional[IPvAnyAddress]
    network: Optional[IPvAnyAddress]
