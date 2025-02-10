import re
from typing import List, Union

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


class Vertex(NGraphElement, validate_assignment=True):
    """Template for generic Vertex, IP Vertex and Codec Vertex"""

    active: bool = True
    configPriority: ConfigPriority = "off"
    control: Control = "off"
    custom: dict[str, Union[str, int, bool]] = Field(default_factory=dict)
    deviceId: str
    extraAlertFilters: list[str] = Field(default_factory=list)
    gpid: Gpid
    imgUrl: str = ""
    isVirtual: bool = False
    maps: Union[List[MapsElement], List] = Field(default_factory=List)  # TODO Prüfen!
    sipsMode: SipsMode = "NONE"
    useAsEndpoint: bool = False
    vertexType: VertexType = "Undecided"

    @field_validator("extraAlertFilters", mode="before")
    @classmethod
    def validate_extra_alert_filters(cls, value) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("extraAlertFilters must be a list.")

        pattern = r"^\d+:([a-zA-Z0-9\-\.]+|\*\*|\*):([a-zA-Z0-9\-\s\[\]/]+|/[^/]+/|[\w\-,]+):(\*|[1-6])$"
        # Regular expression pattern explanation:
        # ^\d+:                     - The filter starts with a numeric scFilter (one or more digits) followed by a colon (:).
        # ([a-zA-Z0-9\-\.]+|\*\*|\*) - pointIdFilter: Matches:
        #                              - Alphanumeric strings with dots (.), dashes (-),
        #                              - '**' as a wildcard for all remaining depth,
        #                              - '*' as a wildcard for a single element.
        # :                          - Separator between pointIdFilter and alarmIdFilter.
        # ([a-zA-Z0-9\-\s\[\]/]+|/[^/]+/|[\w\-,]+) - alarmIdFilter: Matches:
        #                              - Alphanumeric strings with dashes (-), spaces, square brackets ([]), and slashes (/),
        #                              - Regular expressions enclosed in slashes (/regex/),
        #                              - Or comma-separated values.
        # :                          - Separator between alarmIdFilter and severityFilter.
        # (\*|[1-6])                 - severityFilter: Matches:
        #                              - '*' as a wildcard for any severity,
        #                              - Or a numeric severity level between 1 and 6.
        # $                          - Ensures the string ends at this point (no extra characters allowed).

        for filter_str in value:
            if not isinstance(filter_str, str):
                raise ValueError(f"Each alarm filter must be a string. Invalid filter: {filter_str}")
            if not re.match(pattern, filter_str):
                raise ValueError(
                    f"Invalid alarm filter syntax: '{filter_str}'. The expected format is: "
                    "scFilter:pointIdFilter:alarmIdFilter:severityFilter."
                )

            # Additional logic for severity validation
            parts = filter_str.split(":")
            if len(parts) != 4:
                raise ValueError(
                    f"Invalid filter structure: '{filter_str}'. It must contain exactly three colons (':')."
                )

            severity_filter = parts[3]
            if severity_filter != "*" and not severity_filter.isdigit():
                raise ValueError(
                    f"Invalid severity filter in '{filter_str}'. It must be '*' or a number between 1 and 6."
                )
            if severity_filter.isdigit():
                severity_value = int(severity_filter)
                if not 1 <= severity_value <= 6:
                    raise ValueError(
                        f"Severity filter out of range in '{filter_str}'. It must be a number between 1 and 6."
                    )

        return value
