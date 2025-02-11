from abc import ABC
from typing import Literal, TypeVar, Union

from pydantic import BaseModel, Field

# Important:
# - The name of the custom settings model follows the naming convention: CustomSettings_<driver_organization>_<driver_name>_<driver_version> => "." and "-" are replaced by "_"!
# - driver_schema.json is used as reference to define the custom settings model!
# - The "driver_id" field is necessary for the discriminator, which is used to determine the correct model for the custom settings in DeviceConfiguration!
# - The "alias" field is used to map the field to the correct key (with driver organization & name) in the JSON payload for the API!

DriverLiteral = Literal[
    "com.nevion.NMOS_multidevice-0.1.0",
    "com.nevion.NMOS-0.1.0",
    "com.nevion.selenio_13p-0.1.0",
    "com.nevion.arista-0.1.0",
    "com.nevion.r3lay-0.1.0",
    "com.nevion.powercore-0.1.0",
    "com.nevion.nodectrl-0.1.0",
    "com.sony.MLS-X1-1.0",
    "com.nevion.dhd_series52-0.1.0",
    "com.nevion.virtuoso_mi-0.1.0",
    "com.nevion.virtuoso_re-0.1.0",
    "com.nevion.openflow-0.0.1",
    "com.nevion.lawo_ravenna-0.1.0",
]


class DriverCustomSettings(ABC, BaseModel, validate_assignment=True):
    driver_id: DriverLiteral


class CustomSettings_com_nevion_NMOS_multidevice_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.NMOS_multidevice-0.1.0"] = "com.nevion.NMOS_multidevice-0.1.0"
    always_enable_rtp: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.always_enable_rtp")
    """
    Always enable RTP.\n
    The 'rtp_enabled' field in 'transport_params' will always be set to true.
    """
    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.disable_rx_sdp")
    """
    Disable Rx SDP.\n
    Configure this unit's receivers with regular transport parameters only."""
    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.NMOS_multidevice.disable_rx_sdp_with_null")
    """
    Disable Rx SDP with null.\n
    Configures how RX SDPs are disabled. If unchecked, an empty string is used."""
    enable_bulk_config: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.enable_bulk_config")
    """
    Enable bulk config.\n
    Configure this unit using bulk API."""
    enable_experimental_alarm: bool = Field(
        default=False, alias="com.nevion.NMOS_multidevice.enable_experimental_alarm"
    )
    """
    Enable experimental alarms using IS-07.\n
    Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled.
    """
    experimental_alarm_port: None | int = Field(
        default=0, ge=0, le=65535, alias="com.nevion.NMOS_multidevice.experimental_alarm_port"
    )  # ge corrected from 1 to 0 => neccecary to allow the default value!
    """
    Experimental alarm port.\n
    HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead.
    """
    indices_in_ids: bool = Field(default=True, alias="com.nevion.NMOS_multidevice.indices_in_ids")
    """
    Use indices in IDs.\n
    Enable if device reports static streams to get sortable ids."""
    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.NMOS_multidevice.port")
    """
    Port.\n
    The HTTP port used to reach the Node directly."""


class CustomSettings_com_nevion_NMOS_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.NMOS-0.1.0"] = "com.nevion.NMOS-0.1.0"
    always_enable_rtp: bool = Field(default=False, alias="com.nevion.NMOS.always_enable_rtp")
    """
    Always enable RTP.\n
    The 'rtp_enabled' field in 'transport_params' will always be set to true."""
    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.NMOS.disable_rx_sdp")
    """
    Disable Rx SDP.\n
    Configure this unit's receivers with regular transport parameters only."""
    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.NMOS.disable_rx_sdp_with_null")
    """
    Disable Rx SDP with null.\n
    Configures how RX SDPs are disabled. If unchecked, an empty string is used."""
    enable_bulk_config: bool = Field(default=False, alias="com.nevion.NMOS.enable_bulk_config")
    """
    Enable bulk config.\n
    Configure this unit using bulk API."""
    enable_experimental_alarm: bool = Field(default=False, alias="com.nevion.NMOS.enable_experimental_alarm")
    """
    Enable experimental alarms using IS-07.\n
    Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled."""
    experimental_alarm_port: None | int = Field(
        default=0, ge=0, le=65535, alias="com.nevion.NMOS.experimental_alarm_port"
    )  # ge corrected from 1 to 0 => neccecary to allow the default value!
    """
    Experimental alarm port.\n
    HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead."""
    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.NMOS.port")
    """
    Port.\n
    The HTTP port used to reach the Node directly."""


class CustomSettings_com_nevion_selenio_13p_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.selenio_13p-0.1.0"] = "com.nevion.selenio_13p-0.1.0"
    assume_success_after: int = Field(
        default=0, ge=0, le=252635728, alias="com.nevion.selenio_13p.assume_success_after"
    )
    """
    Assume successfull response after [ms].\n
    Assume a configuration was successfully applied after time given in milliseconds, only use if slow response time from Selenio is a problem. Use with care.
    """
    cache_alarm_config_timeout: int = Field(
        default=1800, ge=0, le=252635728, alias="com.nevion.selenio_13p.cache_alarm_config_timeout"
    )
    """
    Alarm config cache timeout [s].\n
    Alarm config cache timeout in seconds. The alarm config is used to fetch severity level for each alarm."""
    cache_timeout: int = Field(default=60, ge=0, le=600, alias="com.nevion.selenio_13p.cache_timeout")
    """
    Cache timeout [s].\n
    Driver cache timeout in seconds."""
    manager_ip: str = Field(default="", alias="com.nevion.selenio_13p.manager_ip")
    """
    Manager Address.\n
    Network address of the manager controlling this element."""
    nmos_port: int = Field(default=8100, ge=1, le=65535, alias="com.nevion.selenio_13p.nmos_port")
    """
    Port.\n
    The HTTP port used to reach the Node directly."""


class CustomSettings_com_nevion_arista_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.arista-0.1.0"] = "com.nevion.arista-0.1.0"
    multicast_route_ignore: str = Field(default="", alias="com.nevion.arista.multicast_route_ignore")
    """Multicast routes ignore list, comma separated."""
    use_multi_vrf: bool = Field(default=False, alias="com.nevion.arista.use_multi_vrf")
    """Enable multi-VRF functionality."""
    use_tls: bool = Field(default=True, alias="com.nevion.arista.use_tls")
    """Use TLS (no certificate checks)."""
    use_twice_nat: bool = Field(default=False, alias="com.nevion.arista.use_twice_nat")
    """Enable twice NAT functionality."""
    enable_cache: bool = Field(default=True, alias="com.nevion.arista.enable_cache")
    """Enable config related cache."""


class CustomSettings_com_nevion_r3lay_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.r3lay-0.1.0"] = "com.nevion.r3lay-0.1.0"
    port: int = Field(default=9998, ge=0, le=65535, alias="com.nevion.r3lay.port")
    """Port."""


class CustomSettings_com_nevion_powercore_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.powercore-0.1.0"] = "com.nevion.powercore-0.1.0"
    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """Send keep-alives.\n
    If selected, keep-alives will be used to determine reachability."""
    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """Port."""
    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """Request queueing."""
    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """Suppress illegal update warnings."""
    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """Tracing (logging intensive)."""


class CustomSettings_com_nevion_nodectrl_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nodectrl-0.1.0"] = "com.nevion.nodectrl-0.1.0"
    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
    Send keep-alives.\n
    If selected, keep-alives will be used to determine reachability."""
    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """Port."""
    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """Request queueing."""
    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """Suppress illegal update warnings."""
    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """Tracing (logging intensive)."""


class CustomSettings_com_sony_MLS_X1_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.MLS-X1-1.0"] = "com.sony.MLS-X1-1.0"
    nsbus_device_id: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
    NS-BUS Device ID.\n
    Device ID for primary management address usually auto-populated by device discovery."""
    nsbus_router_force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.router.force_tcp")
    """
    NS-BUS Router Matrix Protocol: Force TCP.\n
    Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this."""
    nsbus_secondary_device_id: str = Field(default="", alias="com.nevion.nsbus.secondary_deviceId")
    """
    Secondary NS-BUS Device ID.\n
    Device ID for the alternative management address."""
    nsbus_tally_type: Literal[
        "NOT_USE_TALLY",
        "TALLY_MASTER_DEVICE",
        "TALLY_DISPLAY_DEVICE",
        "MASTER_AND_DISPLAY_DEVICE",
    ] = Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    """
    NS-BUS Tally Type.\n
    Tally type usually auto-populated by device discovery."""


class CustomSettings_com_nevion_dhd_series52_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.dhd_series52-0.1.0"] = "com.nevion.dhd_series52-0.1.0"
    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
    Send keep-alives.\n
    If selected, keep-alives will be used to determine reachability."""
    port: int = Field(default=666, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """Port."""
    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """Request queueing."""
    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """Suppress illegal update warnings."""
    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """Tracing (logging intensive)."""


class CustomSettings_com_nevion_virtuoso_mi_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso_mi-0.1.0"] = "com.nevion.virtuoso_mi-0.1.0"
    enable_advanced_communication_check: bool = Field(
        default=True, alias="com.nevion.virtuoso_mi.AdvancedReachabilityCheck"
    )
    """
    Enable advanced communication check.\n
    Use a more thorough communication check, this will report an IP address as down if all HBR cards have a status of 'Booting'.
    """
    enable_bulk_config: bool = Field(default=False, alias="com.nevion.virtuoso_mi.enable_bulk_config")
    """
    Enable bulk config.\n
    Configure this unit's audio elements using bulk API.
    """
    linear_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_mi.linear_uplink_support")
    """Support uplink routing for Linear cards.\n
    Support backplane routing to Uplink cards for Linear cards.
    """

    madi_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_mi.madi_uplink_support")
    """Support uplink routing for MADI cards.\n
    Support backplane routing to Uplink cards for MADI cards.
    """


class CustomSettings_com_nevion_virtuoso_re_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso_re-0.1.0"] = "com.nevion.virtuoso_re-0.1.0"
    enable_advanced_communication_check: bool = Field(
        default=True, alias="com.nevion.virtuoso_re.AdvancedReachabilityCheck"
    )
    """
    Enable advanced communication check.\n
    Use a more thorough communication check, this will report an IP address as down if all HBR cards have a status of 'Booting'."""
    enable_bulk_config: bool = Field(default=False, alias="com.nevion.virtuoso_re.enable_bulk_config")
    """
    Enable bulk config.\n
    Configure this unit's audio elements using bulk API."""
    linear_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_re.linear_uplink_support")
    """
    Support uplink routing for Linear cards.\n
    Support backplane routing to Uplink cards for Linear cards."""
    madi_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_re.madi_uplink_support")
    """
    Support uplink routing for MADI cards.\n
    Support backplane routing to Uplink cards for MADI cards."""


class CustomSettings_com_nevion_openflow_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.openflow-0.0.1"] = "com.nevion.openflow-0.0.1"
    com_nevion_api_sample_flows_interval: int = Field(
        default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval"
    )
    """
    Flow stats interval [s].\n
    Interval at which to poll flow stats. 0 to disable."""
    com_nevion_openflow_allow_groups: bool = Field(default=True, alias="com.nevion.openflow_allow_groups")
    """
    Allow groups.\n
    Allow use of group actions in flows."""
    com_nevion_openflow_flow_priority: int = Field(
        default=60000, ge=2, le=65535, alias="com.nevion.openflow_flow_priority"
    )
    """
    Flow priority.\n
    Flow priority used by videoipath."""
    com_nevion_openflow_interface_shutdown_alarms: bool = Field(
        default=False, alias="com.nevion.openflow_interface_shutdown_alarms"
    )
    """
    Interface shutdown alarms.\n
    Allow service correlated alarms when admin shuts down an interface."""
    com_nevion_openflow_max_buckets: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_buckets")
    """
    Max buckets.\n
    Max number of buckets in an openflow group."""
    com_nevion_openflow_max_groups: int = Field(default=65535, ge=1, le=65535, alias="com.nevion.openflow_max_groups")
    """
    Max groups.\n
    Max number of groups on the switch."""
    com_nevion_openflow_max_meters: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_meters")
    """
    Max meters.\n
    Max number of meters on the switch."""
    com_nevion_openflow_table_id: int = Field(default=0, ge=0, le=255, alias="com.nevion.openflow_table_id")
    """
    Table ID.\n
    Table ID to use for videoipath flows."""


class CustomSettings_com_nevion_lawo_ravenna_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.lawo_ravenna-0.1.0"] = "com.nevion.lawo_ravenna-0.1.0"
    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
    Send keep-alives.\n
    If selected, keep-alives will be used to determine reachability."""
    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """Port."""
    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
    Request queueing."""
    request_separation: int = Field(default=0, ge=0, le=250, alias="com.nevion.emberplus.request_separation")
    """
    Request separation [ms].\n
    Set to zero to disable."""
    suppress_illegal: bool = Field(default=True, alias="com.nevion.emberplus.suppress_illegal")
    """
    Suppress illegal update warnings."""
    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
    Tracing (logging intensive)."""
    ctrl_local_addr: bool = Field(default=False, alias="com.nevion.lawo_ravenna.ctrl_local_addr")
    """
    Control Local Addresses."""


# Important:
# To make the discriminator work properly, the custom settings model must be included in the Union type!
CustomSettings = Union[
    CustomSettings_com_nevion_NMOS_multidevice_0_1_0,
    CustomSettings_com_nevion_NMOS_0_1_0,
    CustomSettings_com_nevion_selenio_13p_0_1_0,
    CustomSettings_com_nevion_arista_0_1_0,
    CustomSettings_com_nevion_r3lay_0_1_0,
    CustomSettings_com_nevion_powercore_0_1_0,
    CustomSettings_com_nevion_nodectrl_0_1_0,
    CustomSettings_com_sony_MLS_X1_1_0,
    CustomSettings_com_nevion_dhd_series52_0_1_0,
    CustomSettings_com_nevion_virtuoso_mi_0_1_0,
    CustomSettings_com_nevion_virtuoso_re_0_1_0,
    CustomSettings_com_nevion_openflow_0_0_1,
    CustomSettings_com_nevion_lawo_ravenna_0_1_0,
]

# used for generic typing to ensure intellisense and correct typing
CustomSettingsType = TypeVar("CustomSettingsType", bound=CustomSettings)
