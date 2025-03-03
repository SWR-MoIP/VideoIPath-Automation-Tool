from logging import Logger
from typing import Literal, Optional, overload

from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model.drivers import *
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.validators.device_id import validate_device_id


class InventoryGetDeviceMixin:
    STATUS_FETCH_RETRY_DEFAULT = 20
    STATUS_FETCH_DELAY_DEFAULT = 2

    def __init__(self, inventory_api: InventoryAPI, logger: Logger):
        self._inventory_api = inventory_api
        self._logger = logger

    # --------------------------------
    #  Start Auto-Generated Overloads
    # --------------------------------

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_multidevice_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_agama_analyzer_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_decoder_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_encoder_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_amagi_cloudport_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_amethyst3_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_anubis_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_0_2_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_archwave_unet_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_arista_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm4101_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm5000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr5000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr8400_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_avnpxh12_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_aws_media_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_7600_series_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_asr_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_me_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp330_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp4400_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp505_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp511_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp515_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp524_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp525_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp540_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp560_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_demo_tns_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_device_up_driver_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_dhd_series52_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_dse892_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_dyvi_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_electra_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_embrionix_sfp_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_enterprise_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_openflow_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_avp2000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_ce_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_rx8200_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_500fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782dec_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782enc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7800fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882dec_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882enc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_flexAI_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_emberplus_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_snmp_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_gigacaster2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_gredos_02_22_01]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_gv_kahuna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_haivision_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_cloudengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_netengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_iothink_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_ic_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_le_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_juniper_ex_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_laguna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_lawo_ravenna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_liebert_nx_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_md8000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_ce1_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_rx1_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_mock_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_montone42_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_multicon_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_mwedge_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtl_30_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_70d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_l10_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_net_vision_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nodectrl_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7210_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7705_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nso_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_nx4600_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_openflow_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_powercore_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_prismon_1_0_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_r3lay_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_selenio_13p_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_sencore_dmg_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_snell_probelrouter_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_starfish_splicer_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_sublime_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tag_mcm9000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tally_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_mxs_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_vibe_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns4200_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns460_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns541_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns544_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns546_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns547_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg420_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg425_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg430_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg450_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg480_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_tx9_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_txedge_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_smv_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_ventura_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_fa_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_mi_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_re_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_vizrt_vizengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_nevion_zman_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_MLS_X1_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_Panel_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_SC1_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_cna2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_generic_external_control_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_nsbus_generic_router_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettings_com_sony_rcp3500_0_1_0]: ...

    # ------------------------------
    #  End Auto-Generated Overloads
    # ------------------------------

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice: ...  # Workaround to list all overloads in Intellisense

    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        custom_settings_type: Optional[DriverLiteral] = None,
        config_only: bool = False,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice:
        """Method to get a online device from VideoIPath-Inventory by label, device_id or address as InventoryDevice instance.

        Args:
            label (str, optional): Label of the device to get.
            device_id (str, optional): Device ID of the device to get.
            address (str, optional): Address of the device to get.
            config_only (bool, optional): If True, only the configuration of the device is fetched.
            label_search_mode (Literal["canonical_label", "factory_label_only", "user_defined_label_only"]): Set mode for label search. Default is 'canonical_label'.
            custom_settings_type (str, optional): Set optional driver_id to get Intellisense for custom settings.

        Raises:
            ValueError:  If more than one parameter is given.
            ValueError:  If no device with given label, device_id or address exists in inventory.
            ValueError:  If more than one device with given label or address exists in inventory.

        Returns:
            InventoryDevice: Online configuration of the requested device.
        """
        if sum([1 for x in [label, device_id, address] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either label, device_id or address.")

        if label is not None:
            if label_search_mode == "factory_label_only":
                devive_id_from_label = self._inventory_api.get_device_id_by_factory_label(label)
            elif label_search_mode == "user_defined_label_only":
                devive_id_from_label = self._inventory_api.get_device_id_by_user_defined_label(label)
            elif label_search_mode == "canonical_label":
                devive_id_from_label = self._inventory_api.get_device_id_by_canonical_label(label)
            else:
                raise ValueError(f"Invalid label_search_mode '{label_search_mode}' provided!")

            if label_search_mode == "user_defined_label_only":
                label_name = "user defined"
            elif label_search_mode == "canonical_label":
                label_name = "canonical"
            else:
                label_name = "factory"

            if devive_id_from_label is None:
                raise ValueError(f"No device with {label_name} label '{label}' found in Inventory.")
            elif isinstance(devive_id_from_label, list):
                if len(devive_id_from_label) > 1:
                    raise ValueError(
                        f"More than one device with {label_name} label '{label}' found in Inventory: {', '.join(devive_id_from_label)}"
                    )
                else:
                    device_id = devive_id_from_label[0]
            else:
                device_id = devive_id_from_label

        elif device_id is not None:
            if validate_device_id(device_id=device_id):
                if not self._inventory_api.check_device_id_exists(device_id):
                    raise ValueError(f"No device with id '{device_id}' found in Inventory.")
            else:
                raise ValueError(f"Invalid device_id '{device_id}' provided!")
        elif address is not None:
            devices = self._inventory_api.get_device_id_by_address(address)
            if devices is None:
                raise ValueError(f"No device with address '{address}' found in Inventory.")
            if isinstance(devices, list):
                if len(devices) > 1:
                    raise ValueError(f"More than one device with address '{address}' found in Inventory: {devices}")
                else:
                    device_id = devices[0]
            else:
                device_id = devices

        if type(device_id) is not str:
            raise ValueError("device_id must be a string.")
        online_device = self._inventory_api.get_device(
            device_id=device_id,
            config_only=config_only,
            status_fetch_retry=status_fetch_retry,
            status_fetch_delay=status_fetch_delay,
        )

        return online_device
