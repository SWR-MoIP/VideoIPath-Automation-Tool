from abc import ABC
from typing import Dict, Literal, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field

# Notes:
# - The name of the custom settings model follows the naming convention: CustomSettings_<driver_organization>_<driver_name>_<driver_version> => "." and "-" are replaced by "_"!
# - Schema 2024.4.14.json is used as reference to define the custom settings model!
# - The "driver_id" attribute is necessary for the discriminator, which is used to determine the correct model for the custom settings in DeviceConfiguration!
# - The "alias" attribute is used to map the attribute to the correct key (with driver organization & name) in the JSON payload for the API!
# - "DriverLiteral" is used to provide a list of all possible drivers in the IDEs IntelliSense!

SELECTED_SCHEMA_VERSION = "2024.4.14"
AVAILABLE_SCHEMA_VERSIONS = [
    "2023.4.2",
    "2023.4.35",
    "2023.4.37",
    "2024.1.4",
    "2024.2.6",
    "2024.3.3",
    "2024.4.11",
    "2024.4.12",
    "2024.4.14",
    "2025.2.0",
]


class DriverCustomSettings(ABC, BaseModel, validate_assignment=True): ...


class CustomSettings_com_nevion_NMOS_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.NMOS-0.1.0"] = "com.nevion.NMOS-0.1.0"

    always_enable_rtp: bool = Field(default=False, alias="com.nevion.NMOS.always_enable_rtp")
    """
Always enable RTP\n
The "rtp_enabled" field in "transport_params" will always be set to true\n
	"""

    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.NMOS.disable_rx_sdp")
    """
Disable Rx SDP\n
Configure this unit's receivers with regular transport parameters only\n
	"""

    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.NMOS.disable_rx_sdp_with_null")
    """
Disable Rx SDP with null\n
Configures how RX SDPs are disabled. If unchecked, an empty string is used\n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.NMOS.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""

    enable_experimental_alarm: bool = Field(default=False, alias="com.nevion.NMOS.enable_experimental_alarm")
    """
Enable experimental alarms using IS-07\n
Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled\n
	"""

    experimental_alarm_port: Optional[int] = Field(
        default=0, ge=0, le=65535, alias="com.nevion.NMOS.experimental_alarm_port"
    )
    """
Experimental alarm port\n
HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead\n
	"""

    is05_api_version: bool = Field(default=False, alias="com.nevion.NMOS.is05_api_version")
    """
Enable Max IS05 API version\n
Configure IS05 API version to use max\n
	"""

    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.NMOS.port")
    """
Port\n
The HTTP port used to reach the Node directly\n
	"""


class CustomSettings_com_nevion_NMOS_multidevice_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.NMOS_multidevice-0.1.0"] = "com.nevion.NMOS_multidevice-0.1.0"

    always_enable_rtp: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.always_enable_rtp")
    """
Always enable RTP\n
The "rtp_enabled" field in "transport_params" will always be set to true\n
	"""

    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.disable_rx_sdp")
    """
Disable Rx SDP\n
Configure this unit's receivers with regular transport parameters only\n
	"""

    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.NMOS_multidevice.disable_rx_sdp_with_null")
    """
Disable Rx SDP with null\n
Configures how RX SDPs are disabled. If unchecked, an empty string is used\n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""

    enable_experimental_alarm: bool = Field(
        default=False, alias="com.nevion.NMOS_multidevice.enable_experimental_alarm"
    )
    """
Enable experimental alarms using IS-07\n
Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled\n
	"""

    experimental_alarm_port: Optional[int] = Field(
        default=0, ge=0, le=65535, alias="com.nevion.NMOS_multidevice.experimental_alarm_port"
    )
    """
Experimental alarm port\n
HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead\n
	"""

    indices_in_ids: bool = Field(default=True, alias="com.nevion.NMOS_multidevice.indices_in_ids")
    """
Use indices in IDs\n
Enable if device reports static streams to get sortable ids\n
	"""

    is05_api_version: bool = Field(default=False, alias="com.nevion.NMOS_multidevice.is05_api_version")
    """
Enable Max IS05 API version\n
Configure IS05 API version to use max\n
	"""

    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.NMOS_multidevice.port")
    """
Port\n
The HTTP port used to reach the Node directly\n
	"""


class CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.abb_dpa_upscale_st-0.1.0"] = "com.nevion.abb_dpa_upscale_st-0.1.0"


class CustomSettings_com_nevion_adva_fsp150_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.adva_fsp150-0.1.0"] = "com.nevion.adva_fsp150-0.1.0"


class CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.adva_fsp150_xg400_series-0.1.0"] = "com.nevion.adva_fsp150_xg400_series-0.1.0"


class CustomSettings_com_nevion_agama_analyzer_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.agama_analyzer-0.1.0"] = "com.nevion.agama_analyzer-0.1.0"


class CustomSettings_com_nevion_altum_xavic_decoder_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.altum_xavic_decoder-0.1.0"] = "com.nevion.altum_xavic_decoder-0.1.0"


class CustomSettings_com_nevion_altum_xavic_encoder_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.altum_xavic_encoder-0.1.0"] = "com.nevion.altum_xavic_encoder-0.1.0"


class CustomSettings_com_nevion_amagi_cloudport_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.amagi_cloudport-0.1.0"] = "com.nevion.amagi_cloudport-0.1.0"

    port: int = Field(default=4999, ge=0, le=65535, alias="com.nevion.amagi_cloudport.port")
    """
Port\n
	"""


class CustomSettings_com_nevion_amethyst3_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.amethyst3-0.1.0"] = "com.nevion.amethyst3-0.1.0"


class CustomSettings_com_nevion_anubis_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.anubis-0.1.0"] = "com.nevion.anubis-0.1.0"


class CustomSettings_com_nevion_appeartv_x_platform_0_2_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.appeartv_x_platform-0.2.0"] = "com.nevion.appeartv_x_platform-0.2.0"

    coder_ip_mapping: str = Field(default="", alias="com.nevion.appeartv_x_platform.coder_ip_mapping")
    """
Coder-IP mapping\n
Coder module - IP module association map\n
	"""

    lan_wan_mapping: str = Field(default="", alias="com.nevion.appeartv_x_platform.lan_wan_mapping")
    """
LAN-WAN mapping\n
LAN/WAN module association map\n
	"""


class CustomSettings_com_nevion_appeartv_x_platform_legacy_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.appeartv_x_platform_legacy-0.1.0"] = "com.nevion.appeartv_x_platform_legacy-0.1.0"


class CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.appeartv_x_platform_static-0.1.0"] = "com.nevion.appeartv_x_platform_static-0.1.0"

    implicit_interface_selection: bool = Field(
        default=False, alias="com.nevion.appeartv_x_platform_static.implicit_interface_selection"
    )
    """
Implicit Interface Selection\n
Select vlan subinterfaces based on vlan in port configuration.\n
	"""


class CustomSettings_com_nevion_archwave_unet_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.archwave_unet-0.1.0"] = "com.nevion.archwave_unet-0.1.0"

    channel_mode: Literal["Dual Mono", "Stereo"] = Field(
        default="Stereo", alias="com.nevion.archwave_unet.channel_mode"
    )
    """
Stream consumer channel mode\n
In Stereo mode the driver will only report one stream consumer (output) to the topology. The driver will automatically configure the second stream consumer based on the received SDP to the former consumer stream\n
In Dual Mono mode both stream consumers will be reported to the topology and handled as individual streams\n
Possible values:\n
	`Dual Mono`: Dual Mono\n
	`Stereo`: Stereo (default)
	"""


class CustomSettings_com_nevion_arista_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.arista-0.1.0"] = "com.nevion.arista-0.1.0"

    enable_cache: bool = Field(default=True, alias="com.nevion.arista.enable_cache")
    """
Enable config related cache\n
	"""

    multicast_route_ignore: str = Field(default="", alias="com.nevion.arista.multicast_route_ignore")
    """
Multicast routes ignore list, comma separated\n
	"""

    use_multi_vrf: bool = Field(default=False, alias="com.nevion.arista.use_multi_vrf")
    """
Enable multi-VRF functionality\n
	"""

    use_tls: bool = Field(default=True, alias="com.nevion.arista.use_tls")
    """
Use TLS (no certificate checks)\n
	"""

    use_twice_nat: bool = Field(default=False, alias="com.nevion.arista.use_twice_nat")
    """
Enable twice NAT functionality\n
	"""


class CustomSettings_com_nevion_ateme_cm4101_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ateme_cm4101-0.1.0"] = "com.nevion.ateme_cm4101-0.1.0"


class CustomSettings_com_nevion_ateme_cm5000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ateme_cm5000-0.1.0"] = "com.nevion.ateme_cm5000-0.1.0"


class CustomSettings_com_nevion_ateme_dr5000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ateme_dr5000-0.1.0"] = "com.nevion.ateme_dr5000-0.1.0"


class CustomSettings_com_nevion_ateme_dr8400_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ateme_dr8400-0.1.0"] = "com.nevion.ateme_dr8400-0.1.0"


class CustomSettings_com_nevion_avnpxh12_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.avnpxh12-0.1.0"] = "com.nevion.avnpxh12-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


class CustomSettings_com_nevion_aws_media_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.aws_media-0.1.0"] = "com.nevion.aws_media-0.1.0"

    n_flows: int = Field(default=10, ge=0, le=1000, alias="com.nevion.aws_media.n_flows")
    """
Max #Flows\n
Number of MediaConnect flows\n
	"""

    n_outputs_per_fow: int = Field(default=2, ge=0, le=50, alias="com.nevion.aws_media.n_outputs_per_fow")
    """
Max #Outputs/Flow\n
Number of outputs per MediaConnect flow\n
	"""


class CustomSettings_com_nevion_blade_runner_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.blade_runner-0.1.0"] = "com.nevion.blade_runner-0.1.0"


class CustomSettings_com_nevion_cisco_7600_series_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_7600_series-0.1.0"] = "com.nevion.cisco_7600_series-0.1.0"


class CustomSettings_com_nevion_cisco_asr_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_asr-0.1.0"] = "com.nevion.cisco_asr-0.1.0"


class CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_catalyst_3850-0.1.0"] = "com.nevion.cisco_catalyst_3850-0.1.0"

    sample_flows_interval: int = Field(default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval")
    """
Flow stats interval [s]\n
Interval at which to poll flow stats. 0 to disable.\n
	"""


class CustomSettings_com_nevion_cisco_me_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_me-0.1.0"] = "com.nevion.cisco_me-0.1.0"


class CustomSettings_com_nevion_cisco_ncs540_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_ncs540-0.1.0"] = "com.nevion.cisco_ncs540-0.1.0"


class CustomSettings_com_nevion_cisco_nexus_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_nexus-0.1.0"] = "com.nevion.cisco_nexus-0.1.0"

    controlled_vrfs: str = Field(default="", alias="com.nevion.nexus.controlled_vrfs")
    """
Controlled VRFs\n
Comma-separated lists of VRFs to control. Empty list = all VRFs.\n
	"""

    full_vrf_control: bool = Field(default=False, alias="com.nevion.nexus.full_vrf_control")
    """
Full VRF Control\n
True = configure RPF for all/specified VRFs. False = only configure RPF for known source IP adresses.\n
	"""

    layer2_netmask_mode: bool = Field(default=False, alias="com.nevion.nexus.layer2_netmask_mode")
    """
Use /31 mroute netmask for layer 2\n
Use /31 mroute source address netmask for layer 2 mroutes, i.e. when source address and next-hop are identical.\n
	"""

    periodic_netconf_restart: int = Field(
        default=0, ge=0, le=2147483647, alias="com.nevion.nexus.periodic_netconf_restart"
    )
    """
Restart netconf every (s)\n
Interval in seconds for periodic netconf connection restart. If 0, no restart is performed.\n
	"""


class CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cisco_nexus_nbm-0.1.0"] = "com.nevion.cisco_nexus_nbm-0.1.0"

    sample_flows_interval: int = Field(default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval")
    """
Flow stats interval [s]\n
Interval at which to poll flow stats. 0 to disable.\n
	"""

    use_nat: bool = Field(default=False, alias="com.nevion.cisco_nexus_nbm.use_nat")
    """
Enable NAT functionality\n
	"""


class CustomSettings_com_nevion_comprimato_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.comprimato-0.1.0"] = "com.nevion.comprimato-0.1.0"


class CustomSettings_com_nevion_cp330_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp330-0.1.0"] = "com.nevion.cp330-0.1.0"


class CustomSettings_com_nevion_cp4400_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp4400-0.1.0"] = "com.nevion.cp4400-0.1.0"

    reuse_ts_element: bool = Field(default=False, alias="com.nevion.null.reuse_ts_element")
    """
Enable to activate logic to join existing TS input element for ASI outputs when setting up multicast with identical settings\n
	"""


class CustomSettings_com_nevion_cp505_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp505-0.1.0"] = "com.nevion.cp505-0.1.0"


class CustomSettings_com_nevion_cp511_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp511-0.1.0"] = "com.nevion.cp511-0.1.0"


class CustomSettings_com_nevion_cp515_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp515-0.1.0"] = "com.nevion.cp515-0.1.0"


class CustomSettings_com_nevion_cp524_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp524-0.1.0"] = "com.nevion.cp524-0.1.0"


class CustomSettings_com_nevion_cp525_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp525-0.1.0"] = "com.nevion.cp525-0.1.0"


class CustomSettings_com_nevion_cp540_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp540-0.1.0"] = "com.nevion.cp540-0.1.0"


class CustomSettings_com_nevion_cp560_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.cp560-0.1.0"] = "com.nevion.cp560-0.1.0"


class CustomSettings_com_nevion_demo_tns_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.demo-tns-0.1.0"] = "com.nevion.demo-tns-0.1.0"


class CustomSettings_com_nevion_device_up_driver_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.device_up_driver-0.1.0"] = "com.nevion.device_up_driver-0.1.0"

    retries: int = Field(default=1, ge=1, le=20, alias="com.nevion.device_up_driver.retries")
    """
Number of retries\n
The number of times the device will check reachability.\n
	"""

    timeout: int = Field(default=5, ge=0, le=20, alias="com.nevion.device_up_driver.timeout")
    """
Timeout [s]\n
Timeout in seconds. Upon reaching the timeout, the cache is considered stale and will be invalidated.\n
	"""


class CustomSettings_com_nevion_dhd_series52_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.dhd_series52-0.1.0"] = "com.nevion.dhd_series52-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


class CustomSettings_com_nevion_dse892_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.dse892-0.1.0"] = "com.nevion.dse892-0.1.0"


class CustomSettings_com_nevion_dyvi_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.dyvi-0.1.0"] = "com.nevion.dyvi-0.1.0"


class CustomSettings_com_nevion_electra_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.electra-0.1.0"] = "com.nevion.electra-0.1.0"


class CustomSettings_com_nevion_embrionix_sfp_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.embrionix_sfp-0.1.0"] = "com.nevion.embrionix_sfp-0.1.0"


class CustomSettings_com_nevion_emerge_enterprise_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.emerge_enterprise-0.0.1"] = "com.nevion.emerge_enterprise-0.0.1"


class CustomSettings_com_nevion_emerge_openflow_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.emerge_openflow-0.0.1"] = "com.nevion.emerge_openflow-0.0.1"

    sample_flows_interval: int = Field(default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval")
    """
Flow stats interval [s]\n
Interval at which to poll flow stats. 0 to disable.\n
	"""

    ipv4address: str = Field(default="", alias="com.nevion.emerge_openflow.ipv4address")
    """
IPv4 address\n
Required when using DPID as main address instead of IPv4 (cluster)\n
	"""

    openflow_allow_groups: bool = Field(default=True, alias="com.nevion.openflow_allow_groups")
    """
Allow groups\n
Allow use of group actions in flows\n
	"""

    openflow_flow_priority: int = Field(default=60000, ge=2, le=65535, alias="com.nevion.openflow_flow_priority")
    """
Flow Priority\n
Flow priority used by videoipath\n
	"""

    openflow_interface_shutdown_alarms: bool = Field(
        default=False, alias="com.nevion.openflow_interface_shutdown_alarms"
    )
    """
Interface shutdown alarms\n
Allow service correlated alarms when admin shuts down an interface\n
	"""

    openflow_max_buckets: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_buckets")
    """
Max buckets\n
Max number of buckets in an openflow group\n
	"""

    openflow_max_groups: int = Field(default=65535, ge=1, le=65535, alias="com.nevion.openflow_max_groups")
    """
Max groups\n
Max number of groups on the switch\n
	"""

    openflow_max_meters: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_meters")
    """
Max meters\n
Max number of meters on the switch\n
	"""

    openflow_table_id: int = Field(default=0, ge=0, le=255, alias="com.nevion.openflow_table_id")
    """
Table ID\n
Table ID to use for videoipath flows\n
	"""


class CustomSettings_com_nevion_ericsson_avp2000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ericsson_avp2000-0.1.0"] = "com.nevion.ericsson_avp2000-0.1.0"

    use_alarm_map: bool = Field(default=True, alias="com.nevion.ericsson.use_alarm_map")
    """
Map alarms\n
If enabled, only relevant alerts will be raised.\n
	"""


class CustomSettings_com_nevion_ericsson_ce_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ericsson_ce-0.1.0"] = "com.nevion.ericsson_ce-0.1.0"

    use_alarm_map: bool = Field(default=True, alias="com.nevion.ericsson.use_alarm_map")
    """
Map alarms\n
If enabled, only relevant alerts will be raised.\n
	"""


class CustomSettings_com_nevion_ericsson_rx8200_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ericsson_rx8200-0.1.0"] = "com.nevion.ericsson_rx8200-0.1.0"

    use_alarm_map: bool = Field(default=True, alias="com.nevion.ericsson.use_alarm_map")
    """
Map alarms\n
If enabled, only relevant alerts will be raised.\n
	"""


class CustomSettings_com_nevion_evertz_500fc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_500fc-0.1.0"] = "com.nevion.evertz_500fc-0.1.0"


class CustomSettings_com_nevion_evertz_570fc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570fc-0.1.0"] = "com.nevion.evertz_570fc-0.1.0"


class CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570itxe_hw_p60_udc-0.1.0"] = "com.nevion.evertz_570itxe_hw_p60_udc-0.1.0"


class CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570j2k_x19_12e-0.1.0"] = "com.nevion.evertz_570j2k_x19_12e-0.1.0"


class CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570j2k_x19_6e6d-0.1.0"] = "com.nevion.evertz_570j2k_x19_6e6d-0.1.0"


class CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570j2k_x19_u9d-0.1.0"] = "com.nevion.evertz_570j2k_x19_u9d-0.1.0"


class CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_570j2k_x19_u9e-0.1.0"] = "com.nevion.evertz_570j2k_x19_u9e-0.1.0"


class CustomSettings_com_nevion_evertz_5782dec_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_5782dec-0.1.0"] = "com.nevion.evertz_5782dec-0.1.0"

    enable_frame_controller: bool = Field(default=False, alias="com.nevion.evertz.enable_frame_controller")
    """
Enable Frame Controller\n
Control card through Frame Controller\n
	"""

    frame_controller_slot: int = Field(default=1, ge=1, le=15, alias="com.nevion.evertz.frame_controller_slot")
    """
Frame Controller Slot\n
Defines which slot will be used for communication\n
	"""


class CustomSettings_com_nevion_evertz_5782enc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_5782enc-0.1.0"] = "com.nevion.evertz_5782enc-0.1.0"

    enable_frame_controller: bool = Field(default=False, alias="com.nevion.evertz.enable_frame_controller")
    """
Enable Frame Controller\n
Control card through Frame Controller\n
	"""

    frame_controller_slot: int = Field(default=1, ge=1, le=15, alias="com.nevion.evertz.frame_controller_slot")
    """
Frame Controller Slot\n
Defines which slot will be used for communication\n
	"""


class CustomSettings_com_nevion_evertz_7800fc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_7800fc-0.1.0"] = "com.nevion.evertz_7800fc-0.1.0"


class CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_7880ipg8_10ge2-0.1.0"] = "com.nevion.evertz_7880ipg8_10ge2-0.1.0"


class CustomSettings_com_nevion_evertz_7882dec_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_7882dec-0.1.0"] = "com.nevion.evertz_7882dec-0.1.0"

    enable_frame_controller: bool = Field(default=False, alias="com.nevion.evertz.enable_frame_controller")
    """
Enable Frame Controller\n
Control card through Frame Controller\n
	"""

    frame_controller_slot: int = Field(default=1, ge=1, le=15, alias="com.nevion.evertz.frame_controller_slot")
    """
Frame Controller Slot\n
Defines which slot will be used for communication\n
	"""


class CustomSettings_com_nevion_evertz_7882enc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.evertz_7882enc-0.1.0"] = "com.nevion.evertz_7882enc-0.1.0"

    enable_frame_controller: bool = Field(default=False, alias="com.nevion.evertz.enable_frame_controller")
    """
Enable Frame Controller\n
Control card through Frame Controller\n
	"""

    frame_controller_slot: int = Field(default=1, ge=1, le=15, alias="com.nevion.evertz.frame_controller_slot")
    """
Frame Controller Slot\n
Defines which slot will be used for communication\n
	"""


class CustomSettings_com_nevion_flexAI_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.flexAI-0.1.0"] = "com.nevion.flexAI-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


class CustomSettings_com_nevion_generic_emberplus_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.generic_emberplus-0.1.0"] = "com.nevion.generic_emberplus-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


class CustomSettings_com_nevion_generic_snmp_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.generic_snmp-0.1.0"] = "com.nevion.generic_snmp-0.1.0"


class CustomSettings_com_nevion_gigacaster2_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.gigacaster2-0.1.0"] = "com.nevion.gigacaster2-0.1.0"


class CustomSettings_com_nevion_gredos_02_22_01(DriverCustomSettings):
    driver_id: Literal["com.nevion.gredos-02.22.01"] = "com.nevion.gredos-02.22.01"


class CustomSettings_com_nevion_gv_kahuna_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.gv_kahuna-0.1.0"] = "com.nevion.gv_kahuna-0.1.0"

    port: int = Field(default=2022, ge=0, le=65535, alias="com.nevion.gv_kahuna.port")
    """
Port\n
	"""


class CustomSettings_com_nevion_haivision_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.haivision-0.0.1"] = "com.nevion.haivision-0.0.1"


class CustomSettings_com_nevion_huawei_cloudengine_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.huawei_cloudengine-0.1.0"] = "com.nevion.huawei_cloudengine-0.1.0"


class CustomSettings_com_nevion_huawei_netengine_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.huawei_netengine-0.1.0"] = "com.nevion.huawei_netengine-0.1.0"


class CustomSettings_com_nevion_iothink_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.iothink-0.1.0"] = "com.nevion.iothink-0.1.0"


class CustomSettings_com_nevion_iqoyalink_ic_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.iqoyalink_ic-0.1.0"] = "com.nevion.iqoyalink_ic-0.1.0"


class CustomSettings_com_nevion_iqoyalink_le_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.iqoyalink_le-0.1.0"] = "com.nevion.iqoyalink_le-0.1.0"


class CustomSettings_com_nevion_juniper_ex_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.juniper_ex-0.1.0"] = "com.nevion.juniper_ex-0.1.0"


class CustomSettings_com_nevion_laguna_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.laguna-0.1.0"] = "com.nevion.laguna-0.1.0"


class CustomSettings_com_nevion_lawo_ravenna_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.lawo_ravenna-0.1.0"] = "com.nevion.lawo_ravenna-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    request_separation: int = Field(default=0, ge=0, le=250, alias="com.nevion.emberplus.request_separation")
    """
Request Separation [ms]\n
Set to zero to disable.\n
	"""

    suppress_illegal: bool = Field(default=True, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""

    ctrl_local_addr: bool = Field(default=False, alias="com.nevion.lawo_ravenna.ctrl_local_addr")
    """
Control Local Addresses\n
	"""


class CustomSettings_com_nevion_liebert_nx_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.liebert_nx-0.1.0"] = "com.nevion.liebert_nx-0.1.0"


class CustomSettings_com_nevion_lvb440_1_0_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.lvb440-1.0.0"] = "com.nevion.lvb440-1.0.0"


class CustomSettings_com_nevion_maxiva_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.maxiva-0.1.0"] = "com.nevion.maxiva-0.1.0"


class CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.maxiva_uaxop4p6e-0.1.0"] = "com.nevion.maxiva_uaxop4p6e-0.1.0"


class CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.maxiva_uaxt30uc-0.1.0"] = "com.nevion.maxiva_uaxt30uc-0.1.0"


class CustomSettings_com_nevion_md8000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.md8000-0.1.0"] = "com.nevion.md8000-0.1.0"

    mac_table_cache_timeout: int = Field(default=10, ge=0, le=300, alias="com.nevion.md8000.mac_table_cache_timeout")
    """
MAC table cache timeout\n
Timeout in seconds. Upon reaching the timeout, the cache is considered stale and will be invalidated\n
	"""

    report_alerts: Literal["no", "yes"] = Field(default="yes", alias="com.nevion.md8000.report_alerts")
    """
Report alerts\n
Toggles whether or not the driver reports alerts\n
Possible values:\n
	`no`: No\n
	`yes`: Yes (default)
	"""


class CustomSettings_com_nevion_mediakind_ce1_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.mediakind_ce1-0.1.0"] = "com.nevion.mediakind_ce1-0.1.0"


class CustomSettings_com_nevion_mediakind_rx1_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.mediakind_rx1-0.1.0"] = "com.nevion.mediakind_rx1-0.1.0"


class CustomSettings_com_nevion_mock_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.mock-0.1.0"] = "com.nevion.mock-0.1.0"

    sample_flows_interval: int = Field(default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval")
    """
Flow stats interval [s]\n
Interval at which to poll flow stats. 0 to disable.\n
	"""

    always_compute_rx_sdp: bool = Field(default=False, alias="com.nevion.mock.always_compute_rx_sdp")
    """
Always compute Rx SDP\n
If enabled, VIP will generate a SDP for a receiver even if the sender does not publish a SDP itself\n
	"""

    always_different: bool = Field(default=True, alias="com.nevion.mock.always_different")
    """
Skip config apply checks\n
Skip config apply checks (always different)\n
	"""

    bulk: bool = Field(default=True, alias="com.nevion.mock.bulk")
    """
Bulk config\n
	"""

    delay: int = Field(default=0, ge=0, le=10000, alias="com.nevion.mock.delay")
    """
Delay\n
	"""

    matrix_type: Literal["N:N", "1:N", "1:1"] = Field(default="1:N", alias="com.nevion.mock.matrix_type")
    """
Matrix Type\n
Possible values:\n
	`N:N`: N:N\n
	`1:N`: 1:N (default)\n
	`1:1`: 1:1
	"""

    nmetrics: int = Field(default=0, alias="com.nevion.mock.nmetrics")
    """
Number of ports for metrics (nPorts * 12)\n
Number of metrics per device\n
	"""

    num_codec_modules: int = Field(default=2, ge=0, le=10, alias="com.nevion.mock.num_codec_modules")
    """
#Codecs\n
Number of codec modules\n
	"""

    num_dynamic_resource_modules: int = Field(
        default=0, ge=0, le=10, alias="com.nevion.mock.num_dynamic_resource_modules"
    )
    """
#DynamicResourceMods\n
Number of dynamic resource modules\n
	"""

    num_gpis: int = Field(default=0, ge=0, le=10000, alias="com.nevion.mock.num_gpis")
    """
#GPIs\n
Number of GPIs. Automatically flips every 2.\n
	"""

    num_gpos: int = Field(default=0, ge=0, le=10000, alias="com.nevion.mock.num_gpos")
    """
#GPOs\n
Number of GPOs\n
	"""

    num_resource_modules: int = Field(default=0, ge=0, le=10, alias="com.nevion.mock.num_resource_modules")
    """
#ResourceMods\n
Number of resource modules\n
	"""

    num_router_modules: int = Field(default=0, ge=0, le=10, alias="com.nevion.mock.num_router_modules")
    """
#VRouters\n
Number of router modules\n
	"""

    num_router_ports: int = Field(default=32, ge=0, le=10000, alias="com.nevion.mock.num_router_ports")
    """
#VRouterPorts\n
Number of in/out ports per router module\n
	"""

    num_switch_modules: int = Field(default=0, ge=0, le=10, alias="com.nevion.mock.num_switch_modules")
    """
#Switches\n
Number of switch modules\n
	"""

    persist: bool = Field(default=True, alias="com.nevion.mock.persist")
    """
Persist data\n
If enabled configs, source ips etc. will be persisted to disk\n
	"""

    populate_router_matrix: bool = Field(default=False, alias="com.nevion.mock.populate_router_matrix")
    """
Populate router matrix\n
Populate default router matrix crosspoints\n
	"""

    ptpClockType: int = Field(default=0, alias="com.nevion.mock.ptpClockType")
    """
PTP clock type\n
0: Ordinary, 1: Transparent, 2: Boundary, 3: Grandmaster\n
	"""

    tally_ids: str = Field(default="", alias="com.nevion.mock.tally_ids")
    """
Tally ids\n
Comma separated list of tally ids\n
	"""

    tally_master: str = Field(default="", alias="com.nevion.mock.tally_master")
    """
Tally Master data\n
Comma separated list of 'domain/group/color' triples\n
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_nevion_mock_cloud_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.mock_cloud-0.1.0"] = "com.nevion.mock_cloud-0.1.0"


class CustomSettings_com_nevion_montone42_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.montone42-0.1.0"] = "com.nevion.montone42-0.1.0"


class CustomSettings_com_nevion_multicon_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.multicon-0.1.0"] = "com.nevion.multicon-0.1.0"


class CustomSettings_com_nevion_mwedge_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.mwedge-0.1.0"] = "com.nevion.mwedge-0.1.0"


class CustomSettings_com_nevion_ndi_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ndi-0.1.0"] = "com.nevion.ndi-0.1.0"

    num_virtual_routing_instances: int = Field(
        default=10, ge=0, le=65535, alias="com.nevion.ndi.num_virtual_routing_instances"
    )
    """
Virtual Routing instances\n
The number of Virtual Routing instances (destinations) to create\n
	"""

    port: int = Field(default=8765, ge=0, le=65535, alias="com.nevion.ndi.port")
    """
Port\n
Port used to connect to the NDI router\n
	"""


class CustomSettings_com_nevion_nec_dtl_30_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nec_dtl_30-0.1.0"] = "com.nevion.nec_dtl_30-0.1.0"


class CustomSettings_com_nevion_nec_dtu_70d_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nec_dtu_70d-0.1.0"] = "com.nevion.nec_dtu_70d-0.1.0"


class CustomSettings_com_nevion_nec_dtu_l10_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nec_dtu_l10-0.1.0"] = "com.nevion.nec_dtu_l10-0.1.0"


class CustomSettings_com_nevion_net_vision_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.net_vision-0.1.0"] = "com.nevion.net_vision-0.1.0"


class CustomSettings_com_nevion_nodectrl_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nodectrl-0.1.0"] = "com.nevion.nodectrl-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


class CustomSettings_com_nevion_nokia7210_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nokia7210-0.1.0"] = "com.nevion.nokia7210-0.1.0"


class CustomSettings_com_nevion_nokia7705_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nokia7705-0.1.0"] = "com.nevion.nokia7705-0.1.0"


class CustomSettings_com_nevion_nso_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nso-0.1.0"] = "com.nevion.nso-0.1.0"


class CustomSettings_com_nevion_nx4600_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nx4600-0.1.0"] = "com.nevion.nx4600-0.1.0"

    reuse_ts_element: bool = Field(default=False, alias="com.nevion.null.reuse_ts_element")
    """
Enable to activate logic to join existing TS input element for ASI outputs when setting up multicast with identical settings\n
	"""


class CustomSettings_com_nevion_nxl_me80_1_0_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.nxl_me80-1.0.0"] = "com.nevion.nxl_me80-1.0.0"

    wan1_port_start_number: int = Field(default=0, ge=0, le=65520, alias="com.nevion.nxl_me80.wan1_port_start_number")
    """
WAN 1 Port start number\n
	"""

    wan2_port_start_number: int = Field(default=0, ge=0, le=65520, alias="com.nevion.nxl_me80.wan2_port_start_number")
    """
WAN 2 Port start number\n
	"""


class CustomSettings_com_nevion_openflow_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.openflow-0.0.1"] = "com.nevion.openflow-0.0.1"

    sample_flows_interval: int = Field(default=0, ge=0, le=3600, alias="com.nevion.api.sample_flows_interval")
    """
Flow stats interval [s]\n
Interval at which to poll flow stats. 0 to disable.\n
	"""

    openflow_allow_groups: bool = Field(default=True, alias="com.nevion.openflow_allow_groups")
    """
Allow groups\n
Allow use of group actions in flows\n
	"""

    openflow_flow_priority: int = Field(default=60000, ge=2, le=65535, alias="com.nevion.openflow_flow_priority")
    """
Flow Priority\n
Flow priority used by videoipath\n
	"""

    openflow_interface_shutdown_alarms: bool = Field(
        default=False, alias="com.nevion.openflow_interface_shutdown_alarms"
    )
    """
Interface shutdown alarms\n
Allow service correlated alarms when admin shuts down an interface\n
	"""

    openflow_max_buckets: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_buckets")
    """
Max buckets\n
Max number of buckets in an openflow group\n
	"""

    openflow_max_groups: int = Field(default=65535, ge=1, le=65535, alias="com.nevion.openflow_max_groups")
    """
Max groups\n
Max number of groups on the switch\n
	"""

    openflow_max_meters: int = Field(default=65535, ge=2, le=65535, alias="com.nevion.openflow_max_meters")
    """
Max meters\n
Max number of meters on the switch\n
	"""

    openflow_table_id: int = Field(default=0, ge=0, le=255, alias="com.nevion.openflow_table_id")
    """
Table ID\n
Table ID to use for videoipath flows\n
	"""


class CustomSettings_com_nevion_powercore_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.powercore-0.1.0"] = "com.nevion.powercore-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""

    stream_alerts: bool = Field(default=False, alias="com.nevion.powercore.stream_alerts")
    """
Enable Output(RX) flag notifications\n
	"""


class CustomSettings_com_nevion_prismon_1_0_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.prismon-1.0.0"] = "com.nevion.prismon-1.0.0"


class CustomSettings_com_nevion_probel_sw_p_08_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.probel_sw_p_08-0.1.0"] = "com.nevion.probel_sw_p_08-0.1.0"

    disconnect_source_address: int = Field(
        default=1023, ge=0, le=1023, alias="com.nevion.probel_sw_p_08.disconnect_source_address"
    )
    """
Disconnect Source Address\n
Must match disconnect source address in custom matrix\n
	"""

    matrix_module_index: int = Field(default=0, ge=0, le=16, alias="com.nevion.probel_sw_p_08.matrix_module_index")
    """
Matrix Level\n
This must be one higher than level in custom matrix\n
	"""

    name_length: int = Field(default=32, ge=0, le=32, alias="com.nevion.probel_sw_p_08.name_length")
    """
Length of labels\n
Must be in range [0,2,4,8,16,32]\n
	"""

    num_router_levels: int = Field(default=0, ge=0, le=16, alias="com.nevion.probel_sw_p_08.num_router_levels")
    """
SWP08 Level\n
Support up to 16\n
	"""

    num_router_modules: int = Field(default=1, ge=0, le=15, alias="com.nevion.probel_sw_p_08.num_router_modules")
    """
Number of matrices\n
The number of matrices\n
	"""

    num_router_ports: int = Field(default=32, ge=0, le=1023, alias="com.nevion.probel_sw_p_08.num_router_ports")
    """
Number of router ports\n
This must be the same number of ports as on the device\n
	"""

    park_port: int = Field(default=0, ge=0, le=1023, alias="com.nevion.probel_sw_p_08.park_port")
    """
Custom park port\n
Must match park port in topology\n
	"""

    port: int = Field(default=8910, ge=0, le=65535, alias="com.nevion.probel_sw_p_08.port")
    """
Port\n
	"""


class CustomSettings_com_nevion_r3lay_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.r3lay-0.1.0"] = "com.nevion.r3lay-0.1.0"

    port: int = Field(default=9998, ge=0, le=65535, alias="com.nevion.r3lay.port")
    """
Port\n
	"""


class CustomSettings_com_nevion_selenio_13p_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.selenio_13p-0.1.0"] = "com.nevion.selenio_13p-0.1.0"

    assume_success_after: int = Field(default=0, alias="com.nevion.selenio_13p.assume_success_after")
    """
Assume successful response after [ms]\n
Assume a configuration was successfully applied after time given in milliseconds, only use if slow response time from Selenio is a problem. Use with care.\n
	"""

    cache_alarm_config_timeout: int = Field(
        default=1800, ge=0, le=252635728, alias="com.nevion.selenio_13p.cache_alarm_config_timeout"
    )
    """
Alarm config cache timeout [s]\n
Alarm config cache timeout in seconds. The alarm config is used to fetch severity level for each alarm\n
	"""

    cache_timeout: int = Field(default=60, ge=0, le=600, alias="com.nevion.selenio_13p.cache_timeout")
    """
Cache timeout [s]\n
Driver cache timeout in seconds\n
	"""

    manager_ip: str = Field(default="", alias="com.nevion.selenio_13p.manager_ip")
    """
Manager Address\n
Network address of the manager controlling this element\n
	"""

    nmos_port: int = Field(default=8100, ge=1, le=65535, alias="com.nevion.selenio_13p.nmos_port")
    """
Port\n
The HTTP port used to reach the Node directly\n
	"""


class CustomSettings_com_nevion_sencore_dmg_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.sencore_dmg-0.1.0"] = "com.nevion.sencore_dmg-0.1.0"

    coder_ip_mapping: str = Field(default="", alias="com.nevion.sencore_dmg.coder_ip_mapping")
    """
Coder-IP mapping\n
Coder module - IP module association map\n
	"""

    lan_wan_mapping: str = Field(default="", alias="com.nevion.sencore_dmg.lan_wan_mapping")
    """
LAN-WAN mapping\n
LAN/WAN module association map\n
	"""


class CustomSettings_com_nevion_snell_probelrouter_0_0_1(DriverCustomSettings):
    driver_id: Literal["com.nevion.snell_probelrouter-0.0.1"] = "com.nevion.snell_probelrouter-0.0.1"


class CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.sony_nxlk-ip50y-0.1.0"] = "com.nevion.sony_nxlk-ip50y-0.1.0"

    deviceId: str = Field(default="", alias="com.nevion.ndcp.deviceId")
    """
NDCP device id\n
Device id usually auto-populated by device discovery\n
	"""

    always_enable_rtp: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip50y.always_enable_rtp")
    """
Always enable RTP\n
The "rtp_enabled" field in "transport_params" will always be set to true\n
	"""

    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip50y.disable_rx_sdp")
    """
Disable Rx SDP\n
Configure this unit's receivers with regular transport parameters only\n
	"""

    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.sony_nxlk-ip50y.disable_rx_sdp_with_null")
    """
Disable Rx SDP with null\n
Configures how RX SDPs are disabled. If unchecked, an empty string is used\n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip50y.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""

    enable_experimental_alarm: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip50y.enable_experimental_alarm")
    """
Enable experimental alarms using IS-07\n
Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled\n
	"""

    experimental_alarm_port: Optional[int] = Field(
        default=0, ge=0, le=65535, alias="com.nevion.sony_nxlk-ip50y.experimental_alarm_port"
    )
    """
Experimental alarm port\n
HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead\n
	"""

    is05_api_version: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip50y.is05_api_version")
    """
Enable Max IS05 API version\n
Configure IS05 API version to use max\n
	"""

    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.sony_nxlk-ip50y.port")
    """
Port\n
The HTTP port used to reach the Node directly\n
	"""


class CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.sony_nxlk-ip51y-0.1.0"] = "com.nevion.sony_nxlk-ip51y-0.1.0"

    deviceId: str = Field(default="", alias="com.nevion.ndcp.deviceId")
    """
NDCP device id\n
Device id usually auto-populated by device discovery\n
	"""

    always_enable_rtp: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip51y.always_enable_rtp")
    """
Always enable RTP\n
The "rtp_enabled" field in "transport_params" will always be set to true\n
	"""

    disable_rx_sdp: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip51y.disable_rx_sdp")
    """
Disable Rx SDP\n
Configure this unit's receivers with regular transport parameters only\n
	"""

    disable_rx_sdp_with_null: bool = Field(default=True, alias="com.nevion.sony_nxlk-ip51y.disable_rx_sdp_with_null")
    """
Disable Rx SDP with null\n
Configures how RX SDPs are disabled. If unchecked, an empty string is used\n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip51y.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""

    enable_experimental_alarm: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip51y.enable_experimental_alarm")
    """
Enable experimental alarms using IS-07\n
Enables experimental alarms over websockets using IS-07 on certain Vizrt devices. Disables alarms completely if disabled\n
	"""

    experimental_alarm_port: Optional[int] = Field(
        default=0, ge=0, le=65535, alias="com.nevion.sony_nxlk-ip51y.experimental_alarm_port"
    )
    """
Experimental alarm port\n
HTTP port for location of experimental IS-07 alarm websocket. If empty or 0 it uses Port field instead\n
	"""

    is05_api_version: bool = Field(default=False, alias="com.nevion.sony_nxlk-ip51y.is05_api_version")
    """
Enable Max IS05 API version\n
Configure IS05 API version to use max\n
	"""

    port: int = Field(default=80, ge=1, le=65535, alias="com.nevion.sony_nxlk-ip51y.port")
    """
Port\n
The HTTP port used to reach the Node directly\n
	"""


class CustomSettings_com_nevion_spg9000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.spg9000-0.1.0"] = "com.nevion.spg9000-0.1.0"

    x_api_key: str = Field(default="apikey", alias="com.nevion.spg9000.x_api_key")
    """
x-api-key\n
x-api-key (configurable in SPG9000's System tab)\n
	"""


class CustomSettings_com_nevion_starfish_splicer_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.starfish_splicer-0.1.0"] = "com.nevion.starfish_splicer-0.1.0"

    api_port: int = Field(default=8080, ge=1, le=65535, alias="com.nevion.starfish_splicer.api_port")
    """
API Port\n
The HTTP port used to reach the API of the device directly\n
	"""


class CustomSettings_com_nevion_sublime_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.sublime-0.1.0"] = "com.nevion.sublime-0.1.0"


class CustomSettings_com_nevion_tag_mcm9000_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tag_mcm9000-0.1.0"] = "com.nevion.tag_mcm9000-0.1.0"

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.tag_mcm9000.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""

    enable_legacy_uuid_api: bool = Field(default=False, alias="com.nevion.tag_mcm9000.enable_legacy_uuid_api")
    """
Enable 4.1 API (legacy UUIDs)\n
Uses legacy uppercase UUIDs in API to match previously synced topologies\n
	"""


class CustomSettings_com_nevion_tag_mcs_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tag_mcs-0.1.0"] = "com.nevion.tag_mcs-0.1.0"

    enable_bulk_config: bool = Field(default=True, alias="com.nevion.tag_mcs.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit using bulk API\n
	"""


class CustomSettings_com_nevion_tally_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tally-0.1.0"] = "com.nevion.tally-0.1.0"

    primary_port: int = Field(default=8900, ge=1, le=65535, alias="com.nevion.tally.primary_port")
    """
Primary Port\n
	"""

    screen_id: int = Field(default=0, ge=0, le=65535, alias="com.nevion.tally.screen_id")
    """
Static Screen ID\n
Screen ID\n
	"""

    secondary_port: int = Field(default=8900, ge=1, le=65535, alias="com.nevion.tally.secondary_port")
    """
Secondary Port\n
	"""

    tally_brightness: Literal[3, 2, 1, 0] = Field(default=3, alias="com.nevion.tally.tally_brightness")
    """
Static Tally Brightness\n
Tally Brightness\n
Possible values:\n
	`3`: Full (default)\n
	`2`: Half\n
	`1`: 1/7th\n
	`0`: Zero
	"""

    x_number_of_umd: int = Field(default=32, ge=1, le=256, alias="com.nevion.tally.x_number_of_umd")
    """
Number of UMDs\n
	"""


class CustomSettings_com_nevion_telestream_surveyor_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.telestream_surveyor-0.1.0"] = "com.nevion.telestream_surveyor-0.1.0"


class CustomSettings_com_nevion_thomson_mxs_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.thomson_mxs-0.1.0"] = "com.nevion.thomson_mxs-0.1.0"


class CustomSettings_com_nevion_thomson_vibe_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.thomson_vibe-0.1.0"] = "com.nevion.thomson_vibe-0.1.0"


class CustomSettings_com_nevion_tns4200_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns4200-0.1.0"] = "com.nevion.tns4200-0.1.0"

    reuse_ts_element: bool = Field(default=False, alias="com.nevion.null.reuse_ts_element")
    """
Enable to activate logic to join existing TS input element for ASI outputs when setting up multicast with identical settings\n
	"""


class CustomSettings_com_nevion_tns460_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns460-0.1.0"] = "com.nevion.tns460-0.1.0"


class CustomSettings_com_nevion_tns541_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns541-0.1.0"] = "com.nevion.tns541-0.1.0"


class CustomSettings_com_nevion_tns544_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns544-0.1.0"] = "com.nevion.tns544-0.1.0"


class CustomSettings_com_nevion_tns546_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns546-0.1.0"] = "com.nevion.tns546-0.1.0"


class CustomSettings_com_nevion_tns547_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tns547-0.1.0"] = "com.nevion.tns547-0.1.0"


class CustomSettings_com_nevion_tvg420_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tvg420-0.1.0"] = "com.nevion.tvg420-0.1.0"


class CustomSettings_com_nevion_tvg425_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tvg425-0.1.0"] = "com.nevion.tvg425-0.1.0"


class CustomSettings_com_nevion_tvg430_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tvg430-0.1.0"] = "com.nevion.tvg430-0.1.0"


class CustomSettings_com_nevion_tvg450_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tvg450-0.1.0"] = "com.nevion.tvg450-0.1.0"


class CustomSettings_com_nevion_tvg480_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tvg480-0.1.0"] = "com.nevion.tvg480-0.1.0"

    control_mode: Literal["full_control", "partial_control_with_config_restore"] = Field(
        default="full_control", alias="com.nevion.tvg480.control_mode"
    )
    """
Control Mode\n
Which control mode has Videoipath over the device.\n
Possible values:\n
	`full_control`: Full control (default)\n
	`partial_control_with_config_restore`: Partial control with config restore
	"""

    partial_control_config_slot: int = Field(
        default=0, ge=0, le=7, alias="com.nevion.tvg480.partial_control_config_slot"
    )
    """
Partial control config slot\n
Config slot to use when partial control with config restore is used.\n
	"""


class CustomSettings_com_nevion_tx9_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.tx9-0.1.0"] = "com.nevion.tx9-0.1.0"


class CustomSettings_com_nevion_txdarwin_dynamic_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.txdarwin_dynamic-0.1.0"] = "com.nevion.txdarwin_dynamic-0.1.0"

    port: int = Field(default=9000, ge=1, le=65535, alias="com.nevion.txdarwin_dynamic.port")
    """
GraphQL port\n
The HTTP port used to reach the GraphQL API\n
	"""


class CustomSettings_com_nevion_txdarwin_static_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.txdarwin_static-0.1.0"] = "com.nevion.txdarwin_static-0.1.0"

    port: int = Field(default=9000, ge=1, le=65535, alias="com.nevion.txdarwin_static.port")
    """
GraphQL port\n
The HTTP port used to reach the GraphQL API\n
	"""


class CustomSettings_com_nevion_txedge_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.txedge-0.1.0"] = "com.nevion.txedge-0.1.0"

    selected_edge: str = Field(default="", alias="com.nevion.txedge.selected_edge")
    """
Choose tx edge\n
Write down the name of the edge you want to use\n
	"""


class CustomSettings_com_nevion_v__matrix_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.v__matrix-0.1.0"] = "com.nevion.v__matrix-0.1.0"


class CustomSettings_com_nevion_v__matrix_smv_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.v__matrix_smv-0.1.0"] = "com.nevion.v__matrix_smv-0.1.0"


class CustomSettings_com_nevion_ventura_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.ventura-0.1.0"] = "com.nevion.ventura-0.1.0"


class CustomSettings_com_nevion_virtuoso_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso-0.1.0"] = "com.nevion.virtuoso-0.1.0"

    reuse_ts_element: bool = Field(default=False, alias="com.nevion.null.reuse_ts_element")
    """
Enable to activate logic to join existing TS input element for ASI outputs when setting up multicast with identical settings\n
	"""


class CustomSettings_com_nevion_virtuoso_fa_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso_fa-0.1.0"] = "com.nevion.virtuoso_fa-0.1.0"

    enable_hibernation: bool = Field(default=False, alias="com.nevion.virtuoso_fa.enable_hibernation")
    """
Enable hibernation & wake up(supported for v.3.2.14 and above)\n
Automatically put modules not involved in any connection into hibernation. Automatically wake up hibernating modules when setting up a connection involving them.\n
	"""


class CustomSettings_com_nevion_virtuoso_mi_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso_mi-0.1.0"] = "com.nevion.virtuoso_mi-0.1.0"

    AdvancedReachabilityCheck: bool = Field(default=True, alias="com.nevion.virtuoso_mi.AdvancedReachabilityCheck")
    """
Enable advanced communication check\n
Use a more thorough communication check, this will report an IP address as down if all HBR cards have a status of 'Booting' \n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.virtuoso_mi.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit's audio elements using bulk API\n
	"""

    enable_hibernation: bool = Field(default=False, alias="com.nevion.virtuoso_mi.enable_hibernation")
    """
Enable hibernation & wake up(supported for v.1.8.8 and above)\n
Automatically put modules not involved in any connection into hibernation. Automatically wake up hibernating modules when setting up a connection involving them.\n
	"""

    linear_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_mi.linear_uplink_support")
    """
Support uplink routing for Linear cards\n
Support backplane routing to Uplink cards for Linear cards\n
	"""

    madi_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_mi.madi_uplink_support")
    """
Support uplink routing for MADI cards\n
Support backplane routing to Uplink cards for MADI cards\n
	"""


class CustomSettings_com_nevion_virtuoso_re_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.virtuoso_re-0.1.0"] = "com.nevion.virtuoso_re-0.1.0"

    AdvancedReachabilityCheck: bool = Field(default=True, alias="com.nevion.virtuoso_re.AdvancedReachabilityCheck")
    """
Enable advanced communication check\n
Use a more thorough communication check, this will report an IP address as down if all HBR cards have a status of 'Booting' \n
	"""

    enable_bulk_config: bool = Field(default=False, alias="com.nevion.virtuoso_re.enable_bulk_config")
    """
Enable bulk config\n
Configure this unit's audio elements using bulk API\n
	"""

    linear_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_re.linear_uplink_support")
    """
Support uplink routing for Linear cards\n
Support backplane routing to Uplink cards for Linear cards\n
	"""

    madi_uplink_support: bool = Field(default=False, alias="com.nevion.virtuoso_re.madi_uplink_support")
    """
Support uplink routing for MADI cards\n
Support backplane routing to Uplink cards for MADI cards\n
	"""


class CustomSettings_com_nevion_vizrt_vizengine_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.vizrt_vizengine-0.1.0"] = "com.nevion.vizrt_vizengine-0.1.0"

    port: int = Field(default=6100, ge=0, le=65535, alias="com.nevion.vizrt_vizengine.port")
    """
Port\n
	"""


class CustomSettings_com_nevion_zman_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.nevion.zman-0.1.0"] = "com.nevion.zman-0.1.0"


class CustomSettings_com_sony_MLS_X1_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.MLS-X1-1.0"] = "com.sony.MLS-X1-1.0"

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.router.force_tcp")
    """
NS-BUS Router Matrix Protocol: Force TCP\n
Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this.\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_Panel_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.Panel-1.0"] = "com.sony.Panel-1.0"

    force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.config.force_tcp")
    """
NS-BUS Configuration Protocol: Force TCP\n
Don't use TLS, useful for debugging.\n
	"""

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_SC1_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.SC1-1.0"] = "com.sony.SC1-1.0"

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.router.force_tcp")
    """
NS-BUS Router Matrix Protocol: Force TCP\n
Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this.\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_XVS_G1_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.XVS-G1-1.0"] = "com.sony.XVS-G1-1.0"

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.router.force_tcp")
    """
NS-BUS Router Matrix Protocol: Force TCP\n
Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this.\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_cna2_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.cna2-0.1.0"] = "com.sony.cna2-0.1.0"

    domain_number: int = Field(default=0, alias="com.sony.cna2.domain_number")
    """
Domain Number\n
	"""

    matrix_type: str = Field(default="1:1", alias="com.sony.cna2.matrix_type")
    """
MatrixType\n
	"""

    total_cameras: int = Field(default=96, ge=1, le=96, alias="com.sony.cna2.total_cameras")
    """
Total Number of System Cameras\n
	"""

    webhook_url: str = Field(default="", alias="com.sony.cna2.webhook_url")
    """
Webhook URL\n
Typically http://[VIP address]/api\n
	"""


class CustomSettings_com_sony_generic_external_control_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.generic_external_control-1.0"] = "com.sony.generic_external_control-1.0"

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_nsbus_generic_router_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.nsbus_generic_router-1.0"] = "com.sony.nsbus_generic_router-1.0"

    deviceId: str = Field(default="", alias="com.nevion.nsbus.deviceId")
    """
NS-BUS Device ID\n
Device ID for primary management address usually auto-populated by device discovery\n
	"""

    force_tcp: bool = Field(default=False, alias="com.nevion.nsbus.router.force_tcp")
    """
NS-BUS Router Matrix Protocol: Force TCP\n
Don't use TLS on outgoing connection. Note: Depends on support from device, e.g. SC1 may not support this.\n
	"""

    tallyType: Literal["NOT_USE_TALLY", "TALLY_MASTER_DEVICE", "TALLY_DISPLAY_DEVICE", "MASTER_AND_DISPLAY_DEVICE"] = (
        Field(default="NOT_USE_TALLY", alias="com.nevion.nsbus.tallyType")
    )
    """
NS-BUS Tally Type\n
Tally type usually auto-populated by device discovery\n
Possible values:\n
	`NOT_USE_TALLY`: No Tally (default)\n
	`TALLY_MASTER_DEVICE`: Tally Master Device\n
	`TALLY_DISPLAY_DEVICE`: Tally Display Device\n
	`MASTER_AND_DISPLAY_DEVICE`: Tally Master and Display Device
	"""

    matrixId: str = Field(default="", alias="matrixId")
    """
Custom matrix ID\n
	"""


class CustomSettings_com_sony_rcp3500_0_1_0(DriverCustomSettings):
    driver_id: Literal["com.sony.rcp3500-0.1.0"] = "com.sony.rcp3500-0.1.0"

    keepalives: bool = Field(default=True, alias="com.nevion.emberplus.keepalives")
    """
Send keep-alives\n
If selected, keep-alives will be used to determine reachability\n
	"""

    port: int = Field(default=9000, ge=0, le=65535, alias="com.nevion.emberplus.port")
    """
Port\n
	"""

    queue: bool = Field(default=True, alias="com.nevion.emberplus.queue")
    """
Request queueing\n
	"""

    suppress_illegal: bool = Field(default=False, alias="com.nevion.emberplus.suppress_illegal")
    """
Suppress illegal update warnings\n
	"""

    trace: bool = Field(default=False, alias="com.nevion.emberplus.trace")
    """
Tracing (logging intensive)\n
	"""


DRIVER_ID_TO_CUSTOM_SETTINGS: Dict[str, Type[DriverCustomSettings]] = {
    "com.nevion.NMOS-0.1.0": CustomSettings_com_nevion_NMOS_0_1_0,
    "com.nevion.NMOS_multidevice-0.1.0": CustomSettings_com_nevion_NMOS_multidevice_0_1_0,
    "com.nevion.abb_dpa_upscale_st-0.1.0": CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0,
    "com.nevion.adva_fsp150-0.1.0": CustomSettings_com_nevion_adva_fsp150_0_1_0,
    "com.nevion.adva_fsp150_xg400_series-0.1.0": CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0,
    "com.nevion.agama_analyzer-0.1.0": CustomSettings_com_nevion_agama_analyzer_0_1_0,
    "com.nevion.altum_xavic_decoder-0.1.0": CustomSettings_com_nevion_altum_xavic_decoder_0_1_0,
    "com.nevion.altum_xavic_encoder-0.1.0": CustomSettings_com_nevion_altum_xavic_encoder_0_1_0,
    "com.nevion.amagi_cloudport-0.1.0": CustomSettings_com_nevion_amagi_cloudport_0_1_0,
    "com.nevion.amethyst3-0.1.0": CustomSettings_com_nevion_amethyst3_0_1_0,
    "com.nevion.anubis-0.1.0": CustomSettings_com_nevion_anubis_0_1_0,
    "com.nevion.appeartv_x_platform-0.2.0": CustomSettings_com_nevion_appeartv_x_platform_0_2_0,
    "com.nevion.appeartv_x_platform_legacy-0.1.0": CustomSettings_com_nevion_appeartv_x_platform_legacy_0_1_0,
    "com.nevion.appeartv_x_platform_static-0.1.0": CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0,
    "com.nevion.archwave_unet-0.1.0": CustomSettings_com_nevion_archwave_unet_0_1_0,
    "com.nevion.arista-0.1.0": CustomSettings_com_nevion_arista_0_1_0,
    "com.nevion.ateme_cm4101-0.1.0": CustomSettings_com_nevion_ateme_cm4101_0_1_0,
    "com.nevion.ateme_cm5000-0.1.0": CustomSettings_com_nevion_ateme_cm5000_0_1_0,
    "com.nevion.ateme_dr5000-0.1.0": CustomSettings_com_nevion_ateme_dr5000_0_1_0,
    "com.nevion.ateme_dr8400-0.1.0": CustomSettings_com_nevion_ateme_dr8400_0_1_0,
    "com.nevion.avnpxh12-0.1.0": CustomSettings_com_nevion_avnpxh12_0_1_0,
    "com.nevion.aws_media-0.1.0": CustomSettings_com_nevion_aws_media_0_1_0,
    "com.nevion.blade_runner-0.1.0": CustomSettings_com_nevion_blade_runner_0_1_0,
    "com.nevion.cisco_7600_series-0.1.0": CustomSettings_com_nevion_cisco_7600_series_0_1_0,
    "com.nevion.cisco_asr-0.1.0": CustomSettings_com_nevion_cisco_asr_0_1_0,
    "com.nevion.cisco_catalyst_3850-0.1.0": CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0,
    "com.nevion.cisco_me-0.1.0": CustomSettings_com_nevion_cisco_me_0_1_0,
    "com.nevion.cisco_ncs540-0.1.0": CustomSettings_com_nevion_cisco_ncs540_0_1_0,
    "com.nevion.cisco_nexus-0.1.0": CustomSettings_com_nevion_cisco_nexus_0_1_0,
    "com.nevion.cisco_nexus_nbm-0.1.0": CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0,
    "com.nevion.comprimato-0.1.0": CustomSettings_com_nevion_comprimato_0_1_0,
    "com.nevion.cp330-0.1.0": CustomSettings_com_nevion_cp330_0_1_0,
    "com.nevion.cp4400-0.1.0": CustomSettings_com_nevion_cp4400_0_1_0,
    "com.nevion.cp505-0.1.0": CustomSettings_com_nevion_cp505_0_1_0,
    "com.nevion.cp511-0.1.0": CustomSettings_com_nevion_cp511_0_1_0,
    "com.nevion.cp515-0.1.0": CustomSettings_com_nevion_cp515_0_1_0,
    "com.nevion.cp524-0.1.0": CustomSettings_com_nevion_cp524_0_1_0,
    "com.nevion.cp525-0.1.0": CustomSettings_com_nevion_cp525_0_1_0,
    "com.nevion.cp540-0.1.0": CustomSettings_com_nevion_cp540_0_1_0,
    "com.nevion.cp560-0.1.0": CustomSettings_com_nevion_cp560_0_1_0,
    "com.nevion.demo-tns-0.1.0": CustomSettings_com_nevion_demo_tns_0_1_0,
    "com.nevion.device_up_driver-0.1.0": CustomSettings_com_nevion_device_up_driver_0_1_0,
    "com.nevion.dhd_series52-0.1.0": CustomSettings_com_nevion_dhd_series52_0_1_0,
    "com.nevion.dse892-0.1.0": CustomSettings_com_nevion_dse892_0_1_0,
    "com.nevion.dyvi-0.1.0": CustomSettings_com_nevion_dyvi_0_1_0,
    "com.nevion.electra-0.1.0": CustomSettings_com_nevion_electra_0_1_0,
    "com.nevion.embrionix_sfp-0.1.0": CustomSettings_com_nevion_embrionix_sfp_0_1_0,
    "com.nevion.emerge_enterprise-0.0.1": CustomSettings_com_nevion_emerge_enterprise_0_0_1,
    "com.nevion.emerge_openflow-0.0.1": CustomSettings_com_nevion_emerge_openflow_0_0_1,
    "com.nevion.ericsson_avp2000-0.1.0": CustomSettings_com_nevion_ericsson_avp2000_0_1_0,
    "com.nevion.ericsson_ce-0.1.0": CustomSettings_com_nevion_ericsson_ce_0_1_0,
    "com.nevion.ericsson_rx8200-0.1.0": CustomSettings_com_nevion_ericsson_rx8200_0_1_0,
    "com.nevion.evertz_500fc-0.1.0": CustomSettings_com_nevion_evertz_500fc_0_1_0,
    "com.nevion.evertz_570fc-0.1.0": CustomSettings_com_nevion_evertz_570fc_0_1_0,
    "com.nevion.evertz_570itxe_hw_p60_udc-0.1.0": CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0,
    "com.nevion.evertz_570j2k_x19_12e-0.1.0": CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0,
    "com.nevion.evertz_570j2k_x19_6e6d-0.1.0": CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0,
    "com.nevion.evertz_570j2k_x19_u9d-0.1.0": CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0,
    "com.nevion.evertz_570j2k_x19_u9e-0.1.0": CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0,
    "com.nevion.evertz_5782dec-0.1.0": CustomSettings_com_nevion_evertz_5782dec_0_1_0,
    "com.nevion.evertz_5782enc-0.1.0": CustomSettings_com_nevion_evertz_5782enc_0_1_0,
    "com.nevion.evertz_7800fc-0.1.0": CustomSettings_com_nevion_evertz_7800fc_0_1_0,
    "com.nevion.evertz_7880ipg8_10ge2-0.1.0": CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0,
    "com.nevion.evertz_7882dec-0.1.0": CustomSettings_com_nevion_evertz_7882dec_0_1_0,
    "com.nevion.evertz_7882enc-0.1.0": CustomSettings_com_nevion_evertz_7882enc_0_1_0,
    "com.nevion.flexAI-0.1.0": CustomSettings_com_nevion_flexAI_0_1_0,
    "com.nevion.generic_emberplus-0.1.0": CustomSettings_com_nevion_generic_emberplus_0_1_0,
    "com.nevion.generic_snmp-0.1.0": CustomSettings_com_nevion_generic_snmp_0_1_0,
    "com.nevion.gigacaster2-0.1.0": CustomSettings_com_nevion_gigacaster2_0_1_0,
    "com.nevion.gredos-02.22.01": CustomSettings_com_nevion_gredos_02_22_01,
    "com.nevion.gv_kahuna-0.1.0": CustomSettings_com_nevion_gv_kahuna_0_1_0,
    "com.nevion.haivision-0.0.1": CustomSettings_com_nevion_haivision_0_0_1,
    "com.nevion.huawei_cloudengine-0.1.0": CustomSettings_com_nevion_huawei_cloudengine_0_1_0,
    "com.nevion.huawei_netengine-0.1.0": CustomSettings_com_nevion_huawei_netengine_0_1_0,
    "com.nevion.iothink-0.1.0": CustomSettings_com_nevion_iothink_0_1_0,
    "com.nevion.iqoyalink_ic-0.1.0": CustomSettings_com_nevion_iqoyalink_ic_0_1_0,
    "com.nevion.iqoyalink_le-0.1.0": CustomSettings_com_nevion_iqoyalink_le_0_1_0,
    "com.nevion.juniper_ex-0.1.0": CustomSettings_com_nevion_juniper_ex_0_1_0,
    "com.nevion.laguna-0.1.0": CustomSettings_com_nevion_laguna_0_1_0,
    "com.nevion.lawo_ravenna-0.1.0": CustomSettings_com_nevion_lawo_ravenna_0_1_0,
    "com.nevion.liebert_nx-0.1.0": CustomSettings_com_nevion_liebert_nx_0_1_0,
    "com.nevion.lvb440-1.0.0": CustomSettings_com_nevion_lvb440_1_0_0,
    "com.nevion.maxiva-0.1.0": CustomSettings_com_nevion_maxiva_0_1_0,
    "com.nevion.maxiva_uaxop4p6e-0.1.0": CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0,
    "com.nevion.maxiva_uaxt30uc-0.1.0": CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0,
    "com.nevion.md8000-0.1.0": CustomSettings_com_nevion_md8000_0_1_0,
    "com.nevion.mediakind_ce1-0.1.0": CustomSettings_com_nevion_mediakind_ce1_0_1_0,
    "com.nevion.mediakind_rx1-0.1.0": CustomSettings_com_nevion_mediakind_rx1_0_1_0,
    "com.nevion.mock-0.1.0": CustomSettings_com_nevion_mock_0_1_0,
    "com.nevion.mock_cloud-0.1.0": CustomSettings_com_nevion_mock_cloud_0_1_0,
    "com.nevion.montone42-0.1.0": CustomSettings_com_nevion_montone42_0_1_0,
    "com.nevion.multicon-0.1.0": CustomSettings_com_nevion_multicon_0_1_0,
    "com.nevion.mwedge-0.1.0": CustomSettings_com_nevion_mwedge_0_1_0,
    "com.nevion.ndi-0.1.0": CustomSettings_com_nevion_ndi_0_1_0,
    "com.nevion.nec_dtl_30-0.1.0": CustomSettings_com_nevion_nec_dtl_30_0_1_0,
    "com.nevion.nec_dtu_70d-0.1.0": CustomSettings_com_nevion_nec_dtu_70d_0_1_0,
    "com.nevion.nec_dtu_l10-0.1.0": CustomSettings_com_nevion_nec_dtu_l10_0_1_0,
    "com.nevion.net_vision-0.1.0": CustomSettings_com_nevion_net_vision_0_1_0,
    "com.nevion.nodectrl-0.1.0": CustomSettings_com_nevion_nodectrl_0_1_0,
    "com.nevion.nokia7210-0.1.0": CustomSettings_com_nevion_nokia7210_0_1_0,
    "com.nevion.nokia7705-0.1.0": CustomSettings_com_nevion_nokia7705_0_1_0,
    "com.nevion.nso-0.1.0": CustomSettings_com_nevion_nso_0_1_0,
    "com.nevion.nx4600-0.1.0": CustomSettings_com_nevion_nx4600_0_1_0,
    "com.nevion.nxl_me80-1.0.0": CustomSettings_com_nevion_nxl_me80_1_0_0,
    "com.nevion.openflow-0.0.1": CustomSettings_com_nevion_openflow_0_0_1,
    "com.nevion.powercore-0.1.0": CustomSettings_com_nevion_powercore_0_1_0,
    "com.nevion.prismon-1.0.0": CustomSettings_com_nevion_prismon_1_0_0,
    "com.nevion.probel_sw_p_08-0.1.0": CustomSettings_com_nevion_probel_sw_p_08_0_1_0,
    "com.nevion.r3lay-0.1.0": CustomSettings_com_nevion_r3lay_0_1_0,
    "com.nevion.selenio_13p-0.1.0": CustomSettings_com_nevion_selenio_13p_0_1_0,
    "com.nevion.sencore_dmg-0.1.0": CustomSettings_com_nevion_sencore_dmg_0_1_0,
    "com.nevion.snell_probelrouter-0.0.1": CustomSettings_com_nevion_snell_probelrouter_0_0_1,
    "com.nevion.sony_nxlk-ip50y-0.1.0": CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0,
    "com.nevion.sony_nxlk-ip51y-0.1.0": CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0,
    "com.nevion.spg9000-0.1.0": CustomSettings_com_nevion_spg9000_0_1_0,
    "com.nevion.starfish_splicer-0.1.0": CustomSettings_com_nevion_starfish_splicer_0_1_0,
    "com.nevion.sublime-0.1.0": CustomSettings_com_nevion_sublime_0_1_0,
    "com.nevion.tag_mcm9000-0.1.0": CustomSettings_com_nevion_tag_mcm9000_0_1_0,
    "com.nevion.tag_mcs-0.1.0": CustomSettings_com_nevion_tag_mcs_0_1_0,
    "com.nevion.tally-0.1.0": CustomSettings_com_nevion_tally_0_1_0,
    "com.nevion.telestream_surveyor-0.1.0": CustomSettings_com_nevion_telestream_surveyor_0_1_0,
    "com.nevion.thomson_mxs-0.1.0": CustomSettings_com_nevion_thomson_mxs_0_1_0,
    "com.nevion.thomson_vibe-0.1.0": CustomSettings_com_nevion_thomson_vibe_0_1_0,
    "com.nevion.tns4200-0.1.0": CustomSettings_com_nevion_tns4200_0_1_0,
    "com.nevion.tns460-0.1.0": CustomSettings_com_nevion_tns460_0_1_0,
    "com.nevion.tns541-0.1.0": CustomSettings_com_nevion_tns541_0_1_0,
    "com.nevion.tns544-0.1.0": CustomSettings_com_nevion_tns544_0_1_0,
    "com.nevion.tns546-0.1.0": CustomSettings_com_nevion_tns546_0_1_0,
    "com.nevion.tns547-0.1.0": CustomSettings_com_nevion_tns547_0_1_0,
    "com.nevion.tvg420-0.1.0": CustomSettings_com_nevion_tvg420_0_1_0,
    "com.nevion.tvg425-0.1.0": CustomSettings_com_nevion_tvg425_0_1_0,
    "com.nevion.tvg430-0.1.0": CustomSettings_com_nevion_tvg430_0_1_0,
    "com.nevion.tvg450-0.1.0": CustomSettings_com_nevion_tvg450_0_1_0,
    "com.nevion.tvg480-0.1.0": CustomSettings_com_nevion_tvg480_0_1_0,
    "com.nevion.tx9-0.1.0": CustomSettings_com_nevion_tx9_0_1_0,
    "com.nevion.txdarwin_dynamic-0.1.0": CustomSettings_com_nevion_txdarwin_dynamic_0_1_0,
    "com.nevion.txdarwin_static-0.1.0": CustomSettings_com_nevion_txdarwin_static_0_1_0,
    "com.nevion.txedge-0.1.0": CustomSettings_com_nevion_txedge_0_1_0,
    "com.nevion.v__matrix-0.1.0": CustomSettings_com_nevion_v__matrix_0_1_0,
    "com.nevion.v__matrix_smv-0.1.0": CustomSettings_com_nevion_v__matrix_smv_0_1_0,
    "com.nevion.ventura-0.1.0": CustomSettings_com_nevion_ventura_0_1_0,
    "com.nevion.virtuoso-0.1.0": CustomSettings_com_nevion_virtuoso_0_1_0,
    "com.nevion.virtuoso_fa-0.1.0": CustomSettings_com_nevion_virtuoso_fa_0_1_0,
    "com.nevion.virtuoso_mi-0.1.0": CustomSettings_com_nevion_virtuoso_mi_0_1_0,
    "com.nevion.virtuoso_re-0.1.0": CustomSettings_com_nevion_virtuoso_re_0_1_0,
    "com.nevion.vizrt_vizengine-0.1.0": CustomSettings_com_nevion_vizrt_vizengine_0_1_0,
    "com.nevion.zman-0.1.0": CustomSettings_com_nevion_zman_0_1_0,
    "com.sony.MLS-X1-1.0": CustomSettings_com_sony_MLS_X1_1_0,
    "com.sony.Panel-1.0": CustomSettings_com_sony_Panel_1_0,
    "com.sony.SC1-1.0": CustomSettings_com_sony_SC1_1_0,
    "com.sony.XVS-G1-1.0": CustomSettings_com_sony_XVS_G1_1_0,
    "com.sony.cna2-0.1.0": CustomSettings_com_sony_cna2_0_1_0,
    "com.sony.generic_external_control-1.0": CustomSettings_com_sony_generic_external_control_1_0,
    "com.sony.nsbus_generic_router-1.0": CustomSettings_com_sony_nsbus_generic_router_1_0,
    "com.sony.rcp3500-0.1.0": CustomSettings_com_sony_rcp3500_0_1_0,
}

DriverLiteral = Literal[
    "com.nevion.NMOS-0.1.0",
    "com.nevion.NMOS_multidevice-0.1.0",
    "com.nevion.abb_dpa_upscale_st-0.1.0",
    "com.nevion.adva_fsp150-0.1.0",
    "com.nevion.adva_fsp150_xg400_series-0.1.0",
    "com.nevion.agama_analyzer-0.1.0",
    "com.nevion.altum_xavic_decoder-0.1.0",
    "com.nevion.altum_xavic_encoder-0.1.0",
    "com.nevion.amagi_cloudport-0.1.0",
    "com.nevion.amethyst3-0.1.0",
    "com.nevion.anubis-0.1.0",
    "com.nevion.appeartv_x_platform-0.2.0",
    "com.nevion.appeartv_x_platform_legacy-0.1.0",
    "com.nevion.appeartv_x_platform_static-0.1.0",
    "com.nevion.archwave_unet-0.1.0",
    "com.nevion.arista-0.1.0",
    "com.nevion.ateme_cm4101-0.1.0",
    "com.nevion.ateme_cm5000-0.1.0",
    "com.nevion.ateme_dr5000-0.1.0",
    "com.nevion.ateme_dr8400-0.1.0",
    "com.nevion.avnpxh12-0.1.0",
    "com.nevion.aws_media-0.1.0",
    "com.nevion.blade_runner-0.1.0",
    "com.nevion.cisco_7600_series-0.1.0",
    "com.nevion.cisco_asr-0.1.0",
    "com.nevion.cisco_catalyst_3850-0.1.0",
    "com.nevion.cisco_me-0.1.0",
    "com.nevion.cisco_ncs540-0.1.0",
    "com.nevion.cisco_nexus-0.1.0",
    "com.nevion.cisco_nexus_nbm-0.1.0",
    "com.nevion.comprimato-0.1.0",
    "com.nevion.cp330-0.1.0",
    "com.nevion.cp4400-0.1.0",
    "com.nevion.cp505-0.1.0",
    "com.nevion.cp511-0.1.0",
    "com.nevion.cp515-0.1.0",
    "com.nevion.cp524-0.1.0",
    "com.nevion.cp525-0.1.0",
    "com.nevion.cp540-0.1.0",
    "com.nevion.cp560-0.1.0",
    "com.nevion.demo-tns-0.1.0",
    "com.nevion.device_up_driver-0.1.0",
    "com.nevion.dhd_series52-0.1.0",
    "com.nevion.dse892-0.1.0",
    "com.nevion.dyvi-0.1.0",
    "com.nevion.electra-0.1.0",
    "com.nevion.embrionix_sfp-0.1.0",
    "com.nevion.emerge_enterprise-0.0.1",
    "com.nevion.emerge_openflow-0.0.1",
    "com.nevion.ericsson_avp2000-0.1.0",
    "com.nevion.ericsson_ce-0.1.0",
    "com.nevion.ericsson_rx8200-0.1.0",
    "com.nevion.evertz_500fc-0.1.0",
    "com.nevion.evertz_570fc-0.1.0",
    "com.nevion.evertz_570itxe_hw_p60_udc-0.1.0",
    "com.nevion.evertz_570j2k_x19_12e-0.1.0",
    "com.nevion.evertz_570j2k_x19_6e6d-0.1.0",
    "com.nevion.evertz_570j2k_x19_u9d-0.1.0",
    "com.nevion.evertz_570j2k_x19_u9e-0.1.0",
    "com.nevion.evertz_5782dec-0.1.0",
    "com.nevion.evertz_5782enc-0.1.0",
    "com.nevion.evertz_7800fc-0.1.0",
    "com.nevion.evertz_7880ipg8_10ge2-0.1.0",
    "com.nevion.evertz_7882dec-0.1.0",
    "com.nevion.evertz_7882enc-0.1.0",
    "com.nevion.flexAI-0.1.0",
    "com.nevion.generic_emberplus-0.1.0",
    "com.nevion.generic_snmp-0.1.0",
    "com.nevion.gigacaster2-0.1.0",
    "com.nevion.gredos-02.22.01",
    "com.nevion.gv_kahuna-0.1.0",
    "com.nevion.haivision-0.0.1",
    "com.nevion.huawei_cloudengine-0.1.0",
    "com.nevion.huawei_netengine-0.1.0",
    "com.nevion.iothink-0.1.0",
    "com.nevion.iqoyalink_ic-0.1.0",
    "com.nevion.iqoyalink_le-0.1.0",
    "com.nevion.juniper_ex-0.1.0",
    "com.nevion.laguna-0.1.0",
    "com.nevion.lawo_ravenna-0.1.0",
    "com.nevion.liebert_nx-0.1.0",
    "com.nevion.lvb440-1.0.0",
    "com.nevion.maxiva-0.1.0",
    "com.nevion.maxiva_uaxop4p6e-0.1.0",
    "com.nevion.maxiva_uaxt30uc-0.1.0",
    "com.nevion.md8000-0.1.0",
    "com.nevion.mediakind_ce1-0.1.0",
    "com.nevion.mediakind_rx1-0.1.0",
    "com.nevion.mock-0.1.0",
    "com.nevion.mock_cloud-0.1.0",
    "com.nevion.montone42-0.1.0",
    "com.nevion.multicon-0.1.0",
    "com.nevion.mwedge-0.1.0",
    "com.nevion.ndi-0.1.0",
    "com.nevion.nec_dtl_30-0.1.0",
    "com.nevion.nec_dtu_70d-0.1.0",
    "com.nevion.nec_dtu_l10-0.1.0",
    "com.nevion.net_vision-0.1.0",
    "com.nevion.nodectrl-0.1.0",
    "com.nevion.nokia7210-0.1.0",
    "com.nevion.nokia7705-0.1.0",
    "com.nevion.nso-0.1.0",
    "com.nevion.nx4600-0.1.0",
    "com.nevion.nxl_me80-1.0.0",
    "com.nevion.openflow-0.0.1",
    "com.nevion.powercore-0.1.0",
    "com.nevion.prismon-1.0.0",
    "com.nevion.probel_sw_p_08-0.1.0",
    "com.nevion.r3lay-0.1.0",
    "com.nevion.selenio_13p-0.1.0",
    "com.nevion.sencore_dmg-0.1.0",
    "com.nevion.snell_probelrouter-0.0.1",
    "com.nevion.sony_nxlk-ip50y-0.1.0",
    "com.nevion.sony_nxlk-ip51y-0.1.0",
    "com.nevion.spg9000-0.1.0",
    "com.nevion.starfish_splicer-0.1.0",
    "com.nevion.sublime-0.1.0",
    "com.nevion.tag_mcm9000-0.1.0",
    "com.nevion.tag_mcs-0.1.0",
    "com.nevion.tally-0.1.0",
    "com.nevion.telestream_surveyor-0.1.0",
    "com.nevion.thomson_mxs-0.1.0",
    "com.nevion.thomson_vibe-0.1.0",
    "com.nevion.tns4200-0.1.0",
    "com.nevion.tns460-0.1.0",
    "com.nevion.tns541-0.1.0",
    "com.nevion.tns544-0.1.0",
    "com.nevion.tns546-0.1.0",
    "com.nevion.tns547-0.1.0",
    "com.nevion.tvg420-0.1.0",
    "com.nevion.tvg425-0.1.0",
    "com.nevion.tvg430-0.1.0",
    "com.nevion.tvg450-0.1.0",
    "com.nevion.tvg480-0.1.0",
    "com.nevion.tx9-0.1.0",
    "com.nevion.txdarwin_dynamic-0.1.0",
    "com.nevion.txdarwin_static-0.1.0",
    "com.nevion.txedge-0.1.0",
    "com.nevion.v__matrix-0.1.0",
    "com.nevion.v__matrix_smv-0.1.0",
    "com.nevion.ventura-0.1.0",
    "com.nevion.virtuoso-0.1.0",
    "com.nevion.virtuoso_fa-0.1.0",
    "com.nevion.virtuoso_mi-0.1.0",
    "com.nevion.virtuoso_re-0.1.0",
    "com.nevion.vizrt_vizengine-0.1.0",
    "com.nevion.zman-0.1.0",
    "com.sony.MLS-X1-1.0",
    "com.sony.Panel-1.0",
    "com.sony.SC1-1.0",
    "com.sony.XVS-G1-1.0",
    "com.sony.cna2-0.1.0",
    "com.sony.generic_external_control-1.0",
    "com.sony.nsbus_generic_router-1.0",
    "com.sony.rcp3500-0.1.0",
]

# Important:
# To make the discriminator work properly, the custom settings model must be included in the Union type!
# This must be statically typed in order to make intellisense work, we can't reuse DRIVER_ID_TO_CUSTOM_SETTINGS here
CustomSettings = Union[
    CustomSettings_com_nevion_NMOS_0_1_0,
    CustomSettings_com_nevion_NMOS_multidevice_0_1_0,
    CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0,
    CustomSettings_com_nevion_adva_fsp150_0_1_0,
    CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0,
    CustomSettings_com_nevion_agama_analyzer_0_1_0,
    CustomSettings_com_nevion_altum_xavic_decoder_0_1_0,
    CustomSettings_com_nevion_altum_xavic_encoder_0_1_0,
    CustomSettings_com_nevion_amagi_cloudport_0_1_0,
    CustomSettings_com_nevion_amethyst3_0_1_0,
    CustomSettings_com_nevion_anubis_0_1_0,
    CustomSettings_com_nevion_appeartv_x_platform_0_2_0,
    CustomSettings_com_nevion_appeartv_x_platform_legacy_0_1_0,
    CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0,
    CustomSettings_com_nevion_archwave_unet_0_1_0,
    CustomSettings_com_nevion_arista_0_1_0,
    CustomSettings_com_nevion_ateme_cm4101_0_1_0,
    CustomSettings_com_nevion_ateme_cm5000_0_1_0,
    CustomSettings_com_nevion_ateme_dr5000_0_1_0,
    CustomSettings_com_nevion_ateme_dr8400_0_1_0,
    CustomSettings_com_nevion_avnpxh12_0_1_0,
    CustomSettings_com_nevion_aws_media_0_1_0,
    CustomSettings_com_nevion_blade_runner_0_1_0,
    CustomSettings_com_nevion_cisco_7600_series_0_1_0,
    CustomSettings_com_nevion_cisco_asr_0_1_0,
    CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0,
    CustomSettings_com_nevion_cisco_me_0_1_0,
    CustomSettings_com_nevion_cisco_ncs540_0_1_0,
    CustomSettings_com_nevion_cisco_nexus_0_1_0,
    CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0,
    CustomSettings_com_nevion_comprimato_0_1_0,
    CustomSettings_com_nevion_cp330_0_1_0,
    CustomSettings_com_nevion_cp4400_0_1_0,
    CustomSettings_com_nevion_cp505_0_1_0,
    CustomSettings_com_nevion_cp511_0_1_0,
    CustomSettings_com_nevion_cp515_0_1_0,
    CustomSettings_com_nevion_cp524_0_1_0,
    CustomSettings_com_nevion_cp525_0_1_0,
    CustomSettings_com_nevion_cp540_0_1_0,
    CustomSettings_com_nevion_cp560_0_1_0,
    CustomSettings_com_nevion_demo_tns_0_1_0,
    CustomSettings_com_nevion_device_up_driver_0_1_0,
    CustomSettings_com_nevion_dhd_series52_0_1_0,
    CustomSettings_com_nevion_dse892_0_1_0,
    CustomSettings_com_nevion_dyvi_0_1_0,
    CustomSettings_com_nevion_electra_0_1_0,
    CustomSettings_com_nevion_embrionix_sfp_0_1_0,
    CustomSettings_com_nevion_emerge_enterprise_0_0_1,
    CustomSettings_com_nevion_emerge_openflow_0_0_1,
    CustomSettings_com_nevion_ericsson_avp2000_0_1_0,
    CustomSettings_com_nevion_ericsson_ce_0_1_0,
    CustomSettings_com_nevion_ericsson_rx8200_0_1_0,
    CustomSettings_com_nevion_evertz_500fc_0_1_0,
    CustomSettings_com_nevion_evertz_570fc_0_1_0,
    CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0,
    CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0,
    CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0,
    CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0,
    CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0,
    CustomSettings_com_nevion_evertz_5782dec_0_1_0,
    CustomSettings_com_nevion_evertz_5782enc_0_1_0,
    CustomSettings_com_nevion_evertz_7800fc_0_1_0,
    CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0,
    CustomSettings_com_nevion_evertz_7882dec_0_1_0,
    CustomSettings_com_nevion_evertz_7882enc_0_1_0,
    CustomSettings_com_nevion_flexAI_0_1_0,
    CustomSettings_com_nevion_generic_emberplus_0_1_0,
    CustomSettings_com_nevion_generic_snmp_0_1_0,
    CustomSettings_com_nevion_gigacaster2_0_1_0,
    CustomSettings_com_nevion_gredos_02_22_01,
    CustomSettings_com_nevion_gv_kahuna_0_1_0,
    CustomSettings_com_nevion_haivision_0_0_1,
    CustomSettings_com_nevion_huawei_cloudengine_0_1_0,
    CustomSettings_com_nevion_huawei_netengine_0_1_0,
    CustomSettings_com_nevion_iothink_0_1_0,
    CustomSettings_com_nevion_iqoyalink_ic_0_1_0,
    CustomSettings_com_nevion_iqoyalink_le_0_1_0,
    CustomSettings_com_nevion_juniper_ex_0_1_0,
    CustomSettings_com_nevion_laguna_0_1_0,
    CustomSettings_com_nevion_lawo_ravenna_0_1_0,
    CustomSettings_com_nevion_liebert_nx_0_1_0,
    CustomSettings_com_nevion_lvb440_1_0_0,
    CustomSettings_com_nevion_maxiva_0_1_0,
    CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0,
    CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0,
    CustomSettings_com_nevion_md8000_0_1_0,
    CustomSettings_com_nevion_mediakind_ce1_0_1_0,
    CustomSettings_com_nevion_mediakind_rx1_0_1_0,
    CustomSettings_com_nevion_mock_0_1_0,
    CustomSettings_com_nevion_mock_cloud_0_1_0,
    CustomSettings_com_nevion_montone42_0_1_0,
    CustomSettings_com_nevion_multicon_0_1_0,
    CustomSettings_com_nevion_mwedge_0_1_0,
    CustomSettings_com_nevion_ndi_0_1_0,
    CustomSettings_com_nevion_nec_dtl_30_0_1_0,
    CustomSettings_com_nevion_nec_dtu_70d_0_1_0,
    CustomSettings_com_nevion_nec_dtu_l10_0_1_0,
    CustomSettings_com_nevion_net_vision_0_1_0,
    CustomSettings_com_nevion_nodectrl_0_1_0,
    CustomSettings_com_nevion_nokia7210_0_1_0,
    CustomSettings_com_nevion_nokia7705_0_1_0,
    CustomSettings_com_nevion_nso_0_1_0,
    CustomSettings_com_nevion_nx4600_0_1_0,
    CustomSettings_com_nevion_nxl_me80_1_0_0,
    CustomSettings_com_nevion_openflow_0_0_1,
    CustomSettings_com_nevion_powercore_0_1_0,
    CustomSettings_com_nevion_prismon_1_0_0,
    CustomSettings_com_nevion_probel_sw_p_08_0_1_0,
    CustomSettings_com_nevion_r3lay_0_1_0,
    CustomSettings_com_nevion_selenio_13p_0_1_0,
    CustomSettings_com_nevion_sencore_dmg_0_1_0,
    CustomSettings_com_nevion_snell_probelrouter_0_0_1,
    CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0,
    CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0,
    CustomSettings_com_nevion_spg9000_0_1_0,
    CustomSettings_com_nevion_starfish_splicer_0_1_0,
    CustomSettings_com_nevion_sublime_0_1_0,
    CustomSettings_com_nevion_tag_mcm9000_0_1_0,
    CustomSettings_com_nevion_tag_mcs_0_1_0,
    CustomSettings_com_nevion_tally_0_1_0,
    CustomSettings_com_nevion_telestream_surveyor_0_1_0,
    CustomSettings_com_nevion_thomson_mxs_0_1_0,
    CustomSettings_com_nevion_thomson_vibe_0_1_0,
    CustomSettings_com_nevion_tns4200_0_1_0,
    CustomSettings_com_nevion_tns460_0_1_0,
    CustomSettings_com_nevion_tns541_0_1_0,
    CustomSettings_com_nevion_tns544_0_1_0,
    CustomSettings_com_nevion_tns546_0_1_0,
    CustomSettings_com_nevion_tns547_0_1_0,
    CustomSettings_com_nevion_tvg420_0_1_0,
    CustomSettings_com_nevion_tvg425_0_1_0,
    CustomSettings_com_nevion_tvg430_0_1_0,
    CustomSettings_com_nevion_tvg450_0_1_0,
    CustomSettings_com_nevion_tvg480_0_1_0,
    CustomSettings_com_nevion_tx9_0_1_0,
    CustomSettings_com_nevion_txdarwin_dynamic_0_1_0,
    CustomSettings_com_nevion_txdarwin_static_0_1_0,
    CustomSettings_com_nevion_txedge_0_1_0,
    CustomSettings_com_nevion_v__matrix_0_1_0,
    CustomSettings_com_nevion_v__matrix_smv_0_1_0,
    CustomSettings_com_nevion_ventura_0_1_0,
    CustomSettings_com_nevion_virtuoso_0_1_0,
    CustomSettings_com_nevion_virtuoso_fa_0_1_0,
    CustomSettings_com_nevion_virtuoso_mi_0_1_0,
    CustomSettings_com_nevion_virtuoso_re_0_1_0,
    CustomSettings_com_nevion_vizrt_vizengine_0_1_0,
    CustomSettings_com_nevion_zman_0_1_0,
    CustomSettings_com_sony_MLS_X1_1_0,
    CustomSettings_com_sony_Panel_1_0,
    CustomSettings_com_sony_SC1_1_0,
    CustomSettings_com_sony_XVS_G1_1_0,
    CustomSettings_com_sony_cna2_0_1_0,
    CustomSettings_com_sony_generic_external_control_1_0,
    CustomSettings_com_sony_nsbus_generic_router_1_0,
    CustomSettings_com_sony_rcp3500_0_1_0,
]

# used for generic typing to ensure intellisense and correct typing
CustomSettingsType = TypeVar("CustomSettingsType", bound=CustomSettings)
