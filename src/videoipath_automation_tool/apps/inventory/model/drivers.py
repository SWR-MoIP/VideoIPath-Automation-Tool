from typing import Literal, Union

from pydantic import BaseModel, Field

# Important:
# - The name of the custom settings model follows the naming convention: CustomSettings_<driver_organization>_<driver_name>_<driver_version> => "." and "-" are replaced by "_"!
# - driver_schema.json is used as reference to define the custom settings model!
# - The "driver_id" field is necessary for the discriminator, which is used to determine the correct model for the custom settings in DeviceConfiguration!
# - The "alias" field is used to map the field to the correct key (with driver organization & name) in the JSON payload for the API!


class CustomSettings_com_nevion_NMOS_multidevice_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.NMOS_multidevice-0.1.0"] = "com.nevion.NMOS_multidevice-0.1.0"
    always_enable_rtp: bool = Field(
        default=False,
        alias="com.nevion.NMOS_multidevice.always_enable_rtp",
        description='The "rtp_enabled" field in "transport_params" will always be set to true',
        title="Always enable RTP",
    )
    disable_rx_sdp: bool = Field(
        default=False,
        alias="com.nevion.NMOS_multidevice.disable_rx_sdp",
        description="Configure this unit's receivers with regular transport parameters only",
        title="Disable Rx SDP",
    )
    disable_rx_sdp_with_null: bool = Field(
        default=True,
        alias="com.nevion.NMOS_multidevice.disable_rx_sdp_with_null",
        description="Configures how RX SDPs are disabled. If unchecked, an empty string is used",
        title="Disable Rx SDP with null",
    )
    enable_bulk_config: bool = Field(
        default=False,
        alias="com.nevion.NMOS_multidevice.enable_bulk_config",
        description="Configure this unit using bulk API",
        title="Enable bulk config",
    )
    enable_experimental_alarm: bool = Field(
        default=False,
        alias="com.nevion.NMOS_multidevice.enable_experimental_alarm",
        description="Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled",
        title="Enable experimental alarms using IS-07",
    )
    experimental_alarm_port: None | int = Field(
        default=0,
        ge=0,  # Corrected from 1 to 0 => neccecary for the default value!
        le=65535,
        alias="com.nevion.NMOS_multidevice.experimental_alarm_port",
        description="HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead",
        title="Experimental alarm port",
    )
    indices_in_ids: bool = Field(
        default=True,
        alias="com.nevion.NMOS_multidevice.indices_in_ids",
        description="Enable if device reports static streams to get sortable ids",
        title="Use indices in IDs",
    )
    port: int = Field(
        default=80,
        ge=1,
        le=65535,
        alias="com.nevion.NMOS_multidevice.port",
        description="The HTTP port used to reach the Node directly",
        title="Port",
    )


class CustomSettings_com_nevion_NMOS_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.NMOS-0.1.0"] = "com.nevion.NMOS-0.1.0"
    always_enable_rtp: bool = Field(
        default=False,
        alias="com.nevion.NMOS.always_enable_rtp",
        description='The "rtp_enabled" field in "transport_params" will always be set to true',
        title="Always enable RTP",
    )
    disable_rx_sdp: bool = Field(
        default=False,
        alias="com.nevion.NMOS.disable_rx_sdp",
        description="Configure this unit's receivers with regular transport parameters only",
        title="Disable Rx SDP",
    )
    disable_rx_sdp_with_null: bool = Field(
        default=True,
        alias="com.nevion.NMOS.disable_rx_sdp_with_null",
        description="Configures how RX SDPs are disabled. If unchecked, an empty string is used",
        title="Disable Rx SDP with null",
    )
    enable_bulk_config: bool = Field(
        default=False,
        alias="com.nevion.NMOS.enable_bulk_config",
        description="Configure this unit using bulk API",
        title="Enable bulk config",
    )
    enable_experimental_alarm: bool = Field(
        default=False,
        alias="com.nevion.NMOS.enable_experimental_alarm",
        description="Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled",
        title="Enable experimental alarms using IS-07",
    )
    experimental_alarm_port: None | int = Field(
        default=0,
        ge=0,  # Corrected from 1 to 0 => neccecary for the default value!
        le=65535,
        alias="com.nevion.NMOS.experimental_alarm_port",
        description="HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead",
        title="Experimental alarm port",
    )
    port: int = Field(
        default=80,
        ge=1,
        le=65535,
        alias="com.nevion.NMOS.port",
        description="The HTTP port used to reach the Node directly",
        title="Port",
    )


class CustomSettings_com_nevion_selenio_13p_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.selenio_13p-0.1.0"] = "com.nevion.selenio_13p-0.1.0"
    assume_success_after: int = Field(
        default=0,
        ge=0,
        le=252635728,
        alias="com.nevion.selenio_13p.assume_success_after",
        description="Assume a configuration was successfully applied after time given in milliseconds, only use if slow response time from Selenio is a problem. Use with care.",
        title="Assume successful response after [ms]",
    )
    cache_alarm_config_timeout: int = Field(
        default=1800,
        ge=0,
        le=252635728,
        alias="com.nevion.selenio_13p.cache_alarm_config_timeout",
        description="Alarm config cache timeout in seconds. The alarm config is used to fetch severity level for each alarm",
        title="Alarm config cache timeout [s]",
    )
    cache_timeout: int = Field(
        default=60,
        ge=0,
        le=600,
        alias="com.nevion.selenio_13p.cache_timeout",
        description="Driver cache timeout in seconds",
        title="Cache timeout [s]",
    )
    manager_ip: str = Field(
        default="",
        alias="com.nevion.selenio_13p.manager_ip",
        description="Network address of the manager controlling this element",
        title="Manager Address",
    )
    nmos_port: int = Field(
        default=8100,
        ge=1,
        le=65535,
        alias="com.nevion.selenio_13p.nmos_port",
        description="The HTTP port used to reach the Node directly",
        title="Port",
    )


class CustomSettings_com_nevion_arista_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.arista-0.1.0"] = "com.nevion.arista-0.1.0"
    multicast_route_ignore: str = Field(
        default="",
        alias="com.nevion.arista.multicast_route_ignore",
        description="Multicast routes ignore list, comma separated",
        title="Multicast routes ignore list",
    )
    use_multi_vrf: bool = Field(
        default=False,
        alias="com.nevion.arista.use_multi_vrf",
        description="Enable multi-VRF functionality",
        title="Enable multi-VRF functionality",
    )
    use_tls: bool = Field(
        default=True,
        alias="com.nevion.arista.use_tls",
        description="Use TLS (no certificate checks)",
        title="Use TLS (no certificate checks)",
    )
    use_twice_nat: bool = Field(
        default=False,
        alias="com.nevion.arista.use_twice_nat",
        description="Enable twice NAT functionality",
        title="Enable twice NAT functionality",
    )
    enable_cache: bool = Field(
        default=True,
        alias="com.nevion.arista.enable_cache",
        description="Enable config related cache",
        title="Enable config related cache",
    )


class CustomSettings_com_nevion_r3lay_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.r3lay-0.1.0"] = "com.nevion.r3lay-0.1.0"
    port: int = Field(
        default=9998,
        ge=0,
        le=65535,
        alias="com.nevion.r3lay.port",
        description="Port",
        title="Port",
    )


class CustomSettings_com_nevion_powercore_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.powercore-0.1.0"] = "com.nevion.powercore-0.1.0"
    keepalives: bool = Field(
        default=True,
        alias="com.nevion.emberplus.keepalives",
        description="If selected, keep-alives will be used to determine reachability",
        title="Send keep-alives",
    )
    port: int = Field(
        default=9000,
        ge=0,
        le=65535,
        alias="com.nevion.emberplus.port",
        description="Port",
        title="Port",
    )
    queue: bool = Field(
        default=True,
        alias="com.nevion.emberplus.queue",
        description="",
        title="Request queueing",
    )
    suppress_illegal: bool = Field(
        default=False,
        alias="com.nevion.emberplus.suppress_illegal",
        description="",
        title="Suppress illegal update warnings",
    )
    trace: bool = Field(
        default=False,
        alias="com.nevion.emberplus.trace",
        description="",
        title="Tracing (logging intensive)",
    )


class CustomSettings_com_nevion_nodectrl_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.nodectrl-0.1.0"] = "com.nevion.nodectrl-0.1.0"
    keepalives: bool = Field(
        default=True,
        alias="com.nevion.emberplus.keepalives",
        description="If selected, keep-alives will be used to determine reachability",
        title="Send keep-alives",
    )
    port: int = Field(
        default=9000,
        ge=0,
        le=65535,
        alias="com.nevion.emberplus.port",
        description="Port",
        title="Port",
    )
    queue: bool = Field(
        default=True,
        alias="com.nevion.emberplus.queue",
        description="",
        title="Request queueing",
    )
    suppress_illegal: bool = Field(
        default=False,
        alias="com.nevion.emberplus.suppress_illegal",
        description="",
        title="Suppress illegal update warnings",
    )
    trace: bool = Field(
        default=False,
        alias="com.nevion.emberplus.trace",
        description="",
        title="Tracing (logging intensive)",
    )


class CustomSettings_com_sony_MLS_X1_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.sony.MLS-X1-1.0"] = "com.sony.MLS-X1-1.0"
    nsbus_device_id: str = Field(
        default="",
        alias="com.nevion.nsbus.deviceId",
        description="Device ID for primary management address usually auto-populated by device discovery",
        title="NS-BUS Device ID",
    )
    nsbus_router_force_tcp: bool = Field(
        default=False,
        alias="com.nevion.nsbus.router.force_tcp",
        description="Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this.",
        title="NS-BUS Router Matrix Protocol: Force TCP",
    )
    nsbus_secondary_device_id: str = Field(
        default="",
        alias="com.nevion.nsbus.secondary_deviceId",
        description="Device ID for the alternative management address",
        title="Secondary NS-BUS Device ID",
    )
    nsbus_tally_type: Literal[
        "NOT_USE_TALLY",
        "TALLY_MASTER_DEVICE",
        "TALLY_DISPLAY_DEVICE",
        "MASTER_AND_DISPLAY_DEVICE",
    ] = Field(
        default="NOT_USE_TALLY",
        alias="com.nevion.nsbus.tallyType",
        description="Tally type usually auto-populated by device discovery",
        title="NS-BUS Tally Type",
    )


class CustomSettings_com_nevion_dhd_series52_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.dhd_series52-0.1.0"] = "com.nevion.dhd_series52-0.1.0"
    keepalives: bool = Field(
        default=True,
        alias="com.nevion.emberplus.keepalives",
        description="If selected, keep-alives will be used to determine reachability",
        title="Send keep-alives",
    )
    port: int = Field(
        default=9000,
        ge=0,
        le=65535,
        alias="com.nevion.emberplus.port",
        description="Port",
        title="Port",
    )
    queue: bool = Field(
        default=True,
        alias="com.nevion.emberplus.queue",
        description="",
        title="Request queueing",
    )
    suppress_illegal: bool = Field(
        default=False,
        alias="com.nevion.emberplus.suppress_illegal",
        description="",
        title="Suppress illegal update warnings",
    )
    trace: bool = Field(
        default=False,
        alias="com.nevion.emberplus.trace",
        description="",
        title="Tracing (logging intensive)",
    )


class CustomSettings_com_nevion_virtuoso_mi_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.virtuoso_mi-0.1.0"] = "com.nevion.virtuoso_mi-0.1.0"
    enable_advanced_communication_check: bool = Field(
        default=True,
        alias="com.nevion.virtuoso_mi.AdvancedReachabilityCheck",
        description="Use a more thorough communication check, this will report an IP address as down if all HBR cards have a status of 'Booting'",
        title="Enable advanced communication check",
    )
    enable_bulk_config: bool = Field(
        default=False,
        alias="com.nevion.virtuoso_mi.enable_bulk_config",
        description="Configure this unit's audio elements using bulk API",
        title="Enable bulk config",
    )
    linear_uplink_support: bool = Field(
        default=False,
        alias="com.nevion.virtuoso_mi.linear_uplink_support",
        description="Support backplane routing to Uplink cards for Linear cards",
        title="Support uplink routing for Linear cards",
    )
    madi_uplink_support: bool = Field(
        default=False,
        alias="com.nevion.virtuoso_mi.madi_uplink_support",
        description="Support backplane routing to Uplink cards for MADI cards",
        title="Support uplink routing for MADI cards",
    )


class CustomSettings_com_nevion_openflow_0_0_1(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.openflow-0.0.1"] = "com.nevion.openflow-0.0.1"
    com_nevion_api_sample_flows_interval: int = Field(
        default=0,
        ge=0,
        le=3600,
        alias="com.nevion.api.sample_flows_interval",
        description="Interval at which to poll flow stats. 0 to disable.",
        title="Flow stats interval [s]",
    )
    com_nevion_openflow_allow_groups: bool = Field(
        default=True,
        alias="com.nevion.openflow_allow_groups",
        description="Allow use of group actions in flows",
        title="Allow groups",
    )
    com_nevion_openflow_flow_priority: int = Field(
        default=60000,
        ge=2,
        le=65535,
        alias="com.nevion.openflow_flow_priority",
        description="Flow priority used by videoipath",
        title="Flow Priority",
    )
    com_nevion_openflow_interface_shutdown_alarms: bool = Field(
        default=False,
        alias="com.nevion.openflow_interface_shutdown_alarms",
        description="Allow service correlated alarms when admin shuts down an interface",
        title="Interface shutdown alarms",
    )
    com_nevion_openflow_max_buckets: int = Field(
        default=65535,
        ge=2,
        le=65535,
        alias="com.nevion.openflow_max_buckets",
        description="Max number of buckets in an openflow group",
        title="Max buckets",
    )
    com_nevion_openflow_max_groups: int = Field(
        default=65535,
        ge=1,
        le=65535,
        alias="com.nevion.openflow_max_groups",
        description="Max number of groups on the switch",
        title="Max groups",
    )
    com_nevion_openflow_max_meters: int = Field(
        default=65535,
        ge=2,
        le=65535,
        alias="com.nevion.openflow_max_meters",
        description="Max number of meters on the switch",
        title="Max meters",
    )
    com_nevion_openflow_table_id: int = Field(
        default=0,
        ge=0,
        le=255,
        alias="com.nevion.openflow_table_id",
        description="Table ID to use for videoipath flows",
        title="Table ID",
    )


class CustomSettings_com_nevion_lawo_ravenna_0_1_0(BaseModel, validate_assignment=True):
    driver_id: Literal["com.nevion.lawo_ravenna-0.1.0"] = "com.nevion.lawo_ravenna-0.1.0"
    keepalives: bool = Field(
        default=True,
        alias="com.nevion.emberplus.keepalives",
        description="If selected, keep-alives will be used to determine reachability",
        title="Send keep-alives",
    )
    port: int = Field(
        default=9000,
        ge=0,
        le=65535,
        alias="com.nevion.emberplus.port",
        description="Port",
        title="Port",
    )
    queue: bool = Field(
        default=True,
        alias="com.nevion.emberplus.queue",
        description="",
        title="Request queueing",
    )
    request_separation: int = Field(
        default=0,
        ge=0,
        le=250,
        alias="com.nevion.emberplus.request_separation",
        description="Set to zero to disable.",
        title="Request Separation [ms]",
    )
    suppress_illegal: bool = Field(
        default=True,
        alias="com.nevion.emberplus.suppress_illegal",
        description="",
        title="Suppress illegal update warnings",
    )
    trace: bool = Field(
        default=False,
        alias="com.nevion.emberplus.trace",
        description="",
        title="Tracing (logging intensive)",
    )
    ctrl_local_addr: bool = Field(
        default=False,
        alias="com.nevion.lawo_ravenna.ctrl_local_addr",
        description="",
        title="Control Local Addresses",
    )


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
    CustomSettings_com_nevion_openflow_0_0_1,
    CustomSettings_com_nevion_lawo_ravenna_0_1_0,
]

driver_literals = Literal[
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
    "com.nevion.openflow-0.0.1",
    "com.nevion.lawo_ravenna-0.1.0",
]
