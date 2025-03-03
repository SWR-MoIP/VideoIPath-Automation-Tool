from pydantic import BaseModel


class PackageItem(BaseModel):
    _id: str
    _vid: str
    active: bool
    package: str
    packageTool: str
    registry: str
    status: str
    version: str
