from logging import Logger
from typing import Literal, Optional, overload

from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.inventory_utils import construct_driver_id_from_info
from videoipath_automation_tool.apps.inventory.model.drivers import *
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice


class InventoryCreateDeviceFromDiscoveredDeviceMixin:
    def __init__(self, inventory_api: InventoryAPI, logger: Logger):
        self._inventory_api = inventory_api
        self._logger = logger

    # --------------------------------
    #  Start Auto-Generated Overloads
    # --------------------------------

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.NMOS-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.NMOS_multidevice-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_multidevice_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.abb_dpa_upscale_st-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.adva_fsp150-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.adva_fsp150_xg400_series-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.agama_analyzer-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_agama_analyzer_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.altum_xavic_decoder-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_decoder_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.altum_xavic_encoder-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_encoder_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.amagi_cloudport-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_amagi_cloudport_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.amethyst3-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_amethyst3_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.anubis-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_anubis_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.appeartv_x_platform-0.2.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_0_2_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.appeartv_x_platform_legacy-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_legacy_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.appeartv_x_platform_static-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.archwave_unet-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_archwave_unet_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.arista-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_arista_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ateme_cm4101-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm4101_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ateme_cm5000-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm5000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ateme_dr5000-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr5000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ateme_dr8400-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr8400_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.avnpxh12-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_avnpxh12_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.aws_media-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_aws_media_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.blade_runner-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_blade_runner_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.cisco_7600_series-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_7600_series_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cisco_asr-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_asr_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.cisco_catalyst_3850-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cisco_me-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_me_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.cisco_ncs540-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_ncs540_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.cisco_nexus-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.cisco_nexus_nbm-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.comprimato-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_comprimato_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp330-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp330_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp4400-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp4400_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp505-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp505_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp511-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp511_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp515-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp515_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp524-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp524_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp525-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp525_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp540-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp540_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.cp560-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_cp560_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.demo-tns-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_demo_tns_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.device_up_driver-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_device_up_driver_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.dhd_series52-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_dhd_series52_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.dse892-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_dse892_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.dyvi-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_dyvi_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.electra-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_electra_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.embrionix_sfp-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_embrionix_sfp_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.emerge_enterprise-0.0.1"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_enterprise_0_0_1]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.emerge_openflow-0.0.1"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_openflow_0_0_1]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ericsson_avp2000-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_avp2000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ericsson_ce-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_ce_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.ericsson_rx8200-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_rx8200_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_500fc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_500fc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570fc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570fc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570itxe_hw_p60_udc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570j2k_x19_12e-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570j2k_x19_6e6d-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570j2k_x19_u9d-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_570j2k_x19_u9e-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_5782dec-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782dec_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_5782enc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782enc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_7800fc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7800fc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_7880ipg8_10ge2-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_7882dec-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882dec_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.evertz_7882enc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882enc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.flexAI-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_flexAI_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.generic_emberplus-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_emberplus_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.generic_snmp-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_snmp_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.gigacaster2-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_gigacaster2_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.gredos-02.22.01"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_gredos_02_22_01]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.gv_kahuna-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_gv_kahuna_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.haivision-0.0.1"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_haivision_0_0_1]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.huawei_cloudengine-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_cloudengine_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.huawei_netengine-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_netengine_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.iothink-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_iothink_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.iqoyalink_ic-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_ic_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.iqoyalink_le-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_le_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.juniper_ex-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_juniper_ex_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.laguna-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_laguna_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.lawo_ravenna-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_lawo_ravenna_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.liebert_nx-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_liebert_nx_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.lvb440-1.0.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_lvb440_1_0_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.maxiva-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.maxiva_uaxop4p6e-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.maxiva_uaxt30uc-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.md8000-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_md8000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.mediakind_ce1-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_ce1_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.mediakind_rx1-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_rx1_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.mock-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_mock_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.mock_cloud-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_mock_cloud_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.montone42-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_montone42_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.multicon-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_multicon_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.mwedge-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_mwedge_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.ndi-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_ndi_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nec_dtl_30-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtl_30_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.nec_dtu_70d-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_70d_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.nec_dtu_l10-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_l10_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.net_vision-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_net_vision_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nodectrl-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nodectrl_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nokia7210-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7210_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nokia7705-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7705_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nso-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nso_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nx4600-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nx4600_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.nxl_me80-1.0.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_nxl_me80_1_0_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.openflow-0.0.1"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_openflow_0_0_1]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.powercore-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_powercore_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.prismon-1.0.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_prismon_1_0_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.probel_sw_p_08-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_probel_sw_p_08_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.r3lay-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_r3lay_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.selenio_13p-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_selenio_13p_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.sencore_dmg-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_sencore_dmg_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.snell_probelrouter-0.0.1"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_snell_probelrouter_0_0_1]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.sony_nxlk-ip50y-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.sony_nxlk-ip51y-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.spg9000-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_spg9000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.starfish_splicer-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_starfish_splicer_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.sublime-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_sublime_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.tag_mcm9000-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_tag_mcm9000_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tag_mcs-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tag_mcs_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tally-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tally_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.telestream_surveyor-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_telestream_surveyor_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.thomson_mxs-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_mxs_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.thomson_vibe-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_vibe_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns4200-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns4200_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns460-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns460_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns541-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns541_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns544-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns544_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns546-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns546_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tns547-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tns547_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tvg420-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg420_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tvg425-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg425_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tvg430-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg430_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tvg450-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg450_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tvg480-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg480_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.tx9-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_tx9_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.txdarwin_dynamic-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_txdarwin_dynamic_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.txdarwin_static-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_txdarwin_static_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.txedge-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_txedge_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.v__matrix-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.v__matrix_smv-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_smv_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.ventura-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_ventura_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.virtuoso-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.virtuoso_fa-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_fa_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.virtuoso_mi-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_mi_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.virtuoso_re-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_re_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.nevion.vizrt_vizengine-0.1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_nevion_vizrt_vizengine_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.nevion.zman-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_nevion_zman_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.MLS-X1-1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_MLS_X1_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.Panel-1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_Panel_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.SC1-1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_SC1_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.XVS-G1-1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_XVS_G1_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.cna2-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_cna2_0_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.sony.generic_external_control-1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_sony_generic_external_control_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self,
        discovered_device_id: str,
        driver: Literal["com.sony.nsbus_generic_router-1.0"],
        suggested_config_index: int = 0,
    ) -> InventoryDevice[CustomSettings_com_sony_nsbus_generic_router_1_0]: ...

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Literal["com.sony.rcp3500-0.1.0"], suggested_config_index: int = 0
    ) -> InventoryDevice[CustomSettings_com_sony_rcp3500_0_1_0]: ...

    # ------------------------------
    #  End Auto-Generated Overloads
    # ------------------------------

    @overload
    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Optional[DriverLiteral] = None, suggested_config_index: int = 0
    ) -> InventoryDevice: ...  # Workaround to list all overloads in Intellisense

    def create_device_from_discovered_device(
        self, discovered_device_id: str, driver: Optional[DriverLiteral] = None, suggested_config_index: int = 0
    ) -> InventoryDevice:
        """Method to create a new device configuration for VideoIPath-Inventory using a discovered device as a template.
        Returns an InventoryDevice instance with custom settings schema for the given driver, which ensures IntelliSense support.

        Args:
            discovered_device_id (str): ID of the discovered device to use as a template.
            driver (DriverLiteral): Driver to use for the new device configuration. If None, the driver of the discovered device will be used but IntelliSense will not be available for custom settings.
            suggested_config_index (int, optional): Index of the suggested configuration to use. Defaults to 0.

        Returns:
            InventoryDevice: Empty device configuration for the given driver.
        """
        if type(discovered_device_id) is not str:
            raise ValueError("discovered_device_id must be a string.")

        if type(suggested_config_index) is not int:
            raise ValueError("suggested_config_index must be an integer.")

        discovered_device = self._inventory_api.get_discovered_device(discovered_device_id)

        count_of_suggested_configs = len(discovered_device.suggestedConfigs)
        if count_of_suggested_configs == 0:
            raise ValueError("No suggested configurations found for the discovered device")

        if suggested_config_index >= count_of_suggested_configs or suggested_config_index < 0:
            raise ValueError(
                f"suggested_config_index is out of range. {f'Please provide a index between 0 and {count_of_suggested_configs - 1}' if (count_of_suggested_configs - 1) > 0 else 'Please provide 0 as index.'}"
            )

        suggested_config = discovered_device.suggestedConfigs[suggested_config_index]

        suggested_config_driver_id = construct_driver_id_from_info(
            driver_organization=suggested_config.driver.organization,
            driver_name=suggested_config.driver.name,
            driver_version=suggested_config.driver.version,
        )

        if driver is None:
            device = InventoryDevice.create(driver_id=suggested_config_driver_id)
        else:
            device = InventoryDevice.create(driver_id=driver)

        if device.driver_id != suggested_config_driver_id:
            raise ValueError(
                f"Driver '{device.driver_id}' does not match the discovered device driver '{suggested_config_driver_id}'"
            )

        device.configuration.config = suggested_config

        if not device.configuration.label:
            device.configuration.label = discovered_device.id

        return device
