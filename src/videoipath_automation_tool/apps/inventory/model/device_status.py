from typing import List

from pydantic import BaseModel, Field


class PortsEntry(BaseModel):
    id: str
    label: str


class Hw(BaseModel):
    revision: str
    serial: str


class ModulesEntry(BaseModel):
    hw: Hw
    id: str
    label: str
    ports: List[PortsEntry]
    product: dict
    state: str


class ReportField(BaseModel):
    type: str
    value: str


class ReportMeta(BaseModel):
    bookingId: str | None
    pid: str | None
    status: str | None


class ReportEntry(BaseModel):
    field: ReportField
    label: str
    meta: ReportMeta


class Product(BaseModel):
    name: str
    swBuildTime: str | None
    swVersion: str | None


class DeviceInfo(BaseModel):
    accessUrlOpt: str | None
    hw: Hw
    label: str
    product: Product
    report: List[ReportEntry]


class DeviceStatus(BaseModel):
    """DeviceStatus class is used to represent a device status for VideoIPath inventory."""

    id: str = Field(alias="_id")
    vid: str = Field(alias="_vid")
    canonicalLabel: str
    deviceInfo: DeviceInfo
    dynamicFn: dict
    modules: List[ModulesEntry]
    reachable: bool
    softwareInfo: dict
    url: str
