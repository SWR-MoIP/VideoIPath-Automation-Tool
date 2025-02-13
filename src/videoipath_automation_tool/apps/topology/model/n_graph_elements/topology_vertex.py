from typing import Union

from pydantic import Field, field_validator

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    ConfigPriority,
    Control,
    Gpid,
    MapsElement,
    NGraphElement,
    SipsMode,
    VertexType,
)
from videoipath_automation_tool.validators.alarm_filter import validate_alarm_filter
from videoipath_automation_tool.validators.device_id import validate_device_id
from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


class Vertex(NGraphElement, validate_assignment=True):
    """Base class for all vertex types (generic, codec, ip)"""

    active: bool = True
    configPriority: ConfigPriority = "off"
    control: Control = "off"
    custom: dict[str, Union[str, int, bool]] = Field(default_factory=dict)
    deviceId: str
    extraAlertFilters: list[str] = Field(default_factory=list)
    gpid: Gpid
    imgUrl: str = ""
    isVirtual: bool = False
    maps: list[MapsElement] = Field(default_factory=list)
    sipsMode: SipsMode = "NONE"
    useAsEndpoint: bool = False
    vertexType: VertexType = "Undecided"

    # --- Validators ---
    @field_validator("deviceId", mode="before")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        errors = []

        for validator in [validate_device_id, validate_virtual_device_id]:
            try:
                return validator(value)
            except ValueError as e:
                errors.append(str(e))

        raise ValueError("\n".join(errors))

    @field_validator("extraAlertFilters", mode="before")
    @classmethod
    def validate_extra_alert_filters(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("extraAlertFilters must be a list.")

        return [validate_alarm_filter(filter_element) for filter_element in value]

    # --- Getters and Setters ---

    @property
    def config_priority(self) -> ConfigPriority:
        """Config priority level"""
        return self.configPriority

    @config_priority.setter
    def config_priority(self, value: ConfigPriority):
        """Config priority level"""
        self.configPriority = value

    @property
    def extra_alert_filters(self) -> list[str]:
        """Extra Alert Filters"""
        return self.extraAlertFilters

    @extra_alert_filters.setter
    def extra_alert_filters(self, value: list[str]):
        """Extra Alert Filters"""
        self.extraAlertFilters = value

    @property
    def sips_mode(self) -> SipsMode:
        """SIPS mode type"""
        return self.sipsMode

    @sips_mode.setter
    def sips_mode(self, value: SipsMode):
        """SIPS mode type"""
        self.sipsMode = value

    @property
    def use_as_endpoint(self) -> bool:
        """Use as Endpoint"""
        return self.useAsEndpoint

    @use_as_endpoint.setter
    def use_as_endpoint(self, value: bool):
        """Use as Endpoint"""
        self.useAsEndpoint = value

    @property
    def device_id(self) -> str:
        """ID of the corresponding base device"""
        return self.deviceId

    @property
    def is_virtual(self) -> bool:
        """Indicates if the vertex is virtual"""
        return self.isVirtual

    @property
    def vertex_type(self) -> VertexType:
        """Type of the vertex"""
        return self.vertexType
