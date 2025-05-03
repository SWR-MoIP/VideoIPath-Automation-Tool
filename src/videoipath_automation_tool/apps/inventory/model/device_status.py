from typing import List, Optional

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

    def list_modules_label(self) -> List[str]:
        """List all modules label."""
        return [module.label for module in self.modules]

    def list_modules_id(self) -> List[str]:
        """List all modules id."""
        return [module.id for module in self.modules]

    def get_module_by_id(self, module_id: str) -> Optional[ModulesEntry]:
        """Get module by id."""
        for module in self.modules:
            if module.id == module_id:
                return module
        return None

    def get_module_by_label(self, module_label: str) -> Optional[ModulesEntry]:
        """Returns the module with the specified label, or None if not found.

        Raises:
            ValueError: If multiple modules with the same label are found.
        """
        matches = [module for module in self.modules if module.label == module_label]

        if len(matches) > 1:
            raise ValueError(f"Multiple modules found with label '{module_label}'")
        return matches[0] if matches else None
