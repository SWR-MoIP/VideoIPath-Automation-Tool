import logging
from typing import List, Literal, Optional, overload

from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model import DriverLiteral
from videoipath_automation_tool.apps.inventory.model.drivers import (
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
    CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0,
    CustomSettings_com_nevion_archwave_unet_0_1_0,
    CustomSettings_com_nevion_arista_0_1_0,
    CustomSettings_com_nevion_ateme_cm4101_0_1_0,
    CustomSettings_com_nevion_ateme_cm5000_0_1_0,
    CustomSettings_com_nevion_ateme_dr5000_0_1_0,
    CustomSettings_com_nevion_ateme_dr8400_0_1_0,
    CustomSettings_com_nevion_avnpxh12_0_1_0,
    CustomSettings_com_nevion_aws_media_0_1_0,
    CustomSettings_com_nevion_cisco_7600_series_0_1_0,
    CustomSettings_com_nevion_cisco_asr_0_1_0,
    CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0,
    CustomSettings_com_nevion_cisco_me_0_1_0,
    CustomSettings_com_nevion_cisco_nexus_0_1_0,
    CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0,
    CustomSettings_com_nevion_cp330_0_1_0,
    CustomSettings_com_nevion_cp505_0_1_0,
    CustomSettings_com_nevion_cp511_0_1_0,
    CustomSettings_com_nevion_cp515_0_1_0,
    CustomSettings_com_nevion_cp524_0_1_0,
    CustomSettings_com_nevion_cp525_0_1_0,
    CustomSettings_com_nevion_cp540_0_1_0,
    CustomSettings_com_nevion_cp560_0_1_0,
    CustomSettings_com_nevion_cp4400_0_1_0,
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
    CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0,
    CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0,
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
    CustomSettings_com_nevion_maxiva_0_1_0,
    CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0,
    CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0,
    CustomSettings_com_nevion_md8000_0_1_0,
    CustomSettings_com_nevion_mediakind_ce1_0_1_0,
    CustomSettings_com_nevion_mediakind_rx1_0_1_0,
    CustomSettings_com_nevion_mock_0_1_0,
    CustomSettings_com_nevion_montone42_0_1_0,
    CustomSettings_com_nevion_multicon_0_1_0,
    CustomSettings_com_nevion_mwedge_0_1_0,
    CustomSettings_com_nevion_nec_dtl_30_0_1_0,
    CustomSettings_com_nevion_nec_dtu_70d_0_1_0,
    CustomSettings_com_nevion_nec_dtu_l10_0_1_0,
    CustomSettings_com_nevion_net_vision_0_1_0,
    CustomSettings_com_nevion_NMOS_0_1_0,
    CustomSettings_com_nevion_NMOS_multidevice_0_1_0,
    CustomSettings_com_nevion_nodectrl_0_1_0,
    CustomSettings_com_nevion_nokia7210_0_1_0,
    CustomSettings_com_nevion_nokia7705_0_1_0,
    CustomSettings_com_nevion_nso_0_1_0,
    CustomSettings_com_nevion_nx4600_0_1_0,
    CustomSettings_com_nevion_openflow_0_0_1,
    CustomSettings_com_nevion_powercore_0_1_0,
    CustomSettings_com_nevion_prismon_1_0_0,
    CustomSettings_com_nevion_r3lay_0_1_0,
    CustomSettings_com_nevion_selenio_13p_0_1_0,
    CustomSettings_com_nevion_sencore_dmg_0_1_0,
    CustomSettings_com_nevion_snell_probelrouter_0_0_1,
    CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0,
    CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0,
    CustomSettings_com_nevion_starfish_splicer_0_1_0,
    CustomSettings_com_nevion_sublime_0_1_0,
    CustomSettings_com_nevion_tag_mcm9000_0_1_0,
    CustomSettings_com_nevion_tally_0_1_0,
    CustomSettings_com_nevion_thomson_mxs_0_1_0,
    CustomSettings_com_nevion_thomson_vibe_0_1_0,
    CustomSettings_com_nevion_tns460_0_1_0,
    CustomSettings_com_nevion_tns541_0_1_0,
    CustomSettings_com_nevion_tns544_0_1_0,
    CustomSettings_com_nevion_tns546_0_1_0,
    CustomSettings_com_nevion_tns547_0_1_0,
    CustomSettings_com_nevion_tns4200_0_1_0,
    CustomSettings_com_nevion_tvg420_0_1_0,
    CustomSettings_com_nevion_tvg425_0_1_0,
    CustomSettings_com_nevion_tvg430_0_1_0,
    CustomSettings_com_nevion_tvg450_0_1_0,
    CustomSettings_com_nevion_tvg480_0_1_0,
    CustomSettings_com_nevion_tx9_0_1_0,
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
    CustomSettings_com_sony_cna2_0_1_0,
    CustomSettings_com_sony_generic_external_control_1_0,
    CustomSettings_com_sony_MLS_X1_1_0,
    CustomSettings_com_sony_nsbus_generic_router_1_0,
    CustomSettings_com_sony_Panel_1_0,
    CustomSettings_com_sony_rcp3500_0_1_0,
    CustomSettings_com_sony_SC1_1_0,
)
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration_compare import (
    InventoryDeviceComparison,
)
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import validate_device_id_string


class InventoryApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """Inventory App contains functionality to interact with VideoIPath-Inventory.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or logging.getLogger("videoipath_automation_tool_inventory_app")

        # --- Setup Inventory API ---
        self._inventory_api = InventoryAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Inventory APP initialized.")

    # Note: For each driver, an overload is defined to show the correct intellisense for the driver.
    @overload
    def create_device(
        self, driver: Literal["com.nevion.NMOS-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.NMOS_multidevice-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_multidevice_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.abb_dpa_upscale_st-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.adva_fsp150-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.adva_fsp150_xg400_series-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.agama_analyzer-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_agama_analyzer_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.altum_xavic_decoder-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_decoder_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.altum_xavic_encoder-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_encoder_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.amagi_cloudport-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_amagi_cloudport_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.amethyst3-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_amethyst3_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.anubis-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_anubis_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.appeartv_x_platform-0.2.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_0_2_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.appeartv_x_platform_static-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.archwave_unet-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_archwave_unet_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.arista-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_arista_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ateme_cm4101-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm4101_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ateme_cm5000-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm5000_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ateme_dr5000-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr5000_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ateme_dr8400-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr8400_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.avnpxh12-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_avnpxh12_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.aws_media-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_aws_media_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_7600_series-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_7600_series_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_asr-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_asr_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_catalyst_3850-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_me-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_me_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_nexus-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cisco_nexus_nbm-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp330-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp330_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp4400-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp4400_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp505-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp505_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp511-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp511_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp515-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp515_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp524-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp524_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp525-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp525_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp540-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp540_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.cp560-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_cp560_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.demo-tns-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_demo_tns_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.device_up_driver-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_device_up_driver_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.dhd_series52-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_dhd_series52_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.dse892-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_dse892_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.dyvi-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_dyvi_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.electra-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_electra_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.embrionix_sfp-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_embrionix_sfp_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.emerge_enterprise-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_enterprise_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.emerge_openflow-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_openflow_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ericsson_avp2000-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_avp2000_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ericsson_ce-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_ce_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ericsson_rx8200-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_rx8200_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_500fc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_500fc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570fc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570fc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570itxe_hw_p60_udc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570j2k_x19_12e-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570j2k_x19_6e6d-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570j2k_x19_u9d-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_570j2k_x19_u9e-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_5782dec-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782dec_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_5782enc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782enc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_7800fc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7800fc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_7880ipg8_10ge2-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_7882dec-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882dec_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.evertz_7882enc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882enc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.flexAI-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_flexAI_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.generic_emberplus-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_emberplus_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.generic_snmp-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_snmp_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.gigacaster2-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_gigacaster2_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.gredos-02.22.01"]
    ) -> InventoryDevice[CustomSettings_com_nevion_gredos_02_22_01]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.gv_kahuna-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_gv_kahuna_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.haivision-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_haivision_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.huawei_cloudengine-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_cloudengine_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.huawei_netengine-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_netengine_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.iothink-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_iothink_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.iqoyalink_ic-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_ic_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.iqoyalink_le-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_le_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.juniper_ex-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_juniper_ex_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.laguna-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_laguna_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.lawo_ravenna-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_lawo_ravenna_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.liebert_nx-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_liebert_nx_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.maxiva-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.maxiva_uaxop4p6e-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.maxiva_uaxt30uc-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.md8000-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_md8000_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.mediakind_ce1-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_ce1_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.mediakind_rx1-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_rx1_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.mock-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_mock_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.montone42-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_montone42_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.multicon-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_multicon_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.mwedge-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_mwedge_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nec_dtl_30-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtl_30_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nec_dtu_70d-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_70d_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nec_dtu_l10-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_l10_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.net_vision-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_net_vision_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nodectrl-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nodectrl_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nokia7210-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7210_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nokia7705-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7705_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nso-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nso_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nx4600-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nx4600_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.openflow-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_openflow_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.powercore-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_powercore_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.prismon-1.0.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_prismon_1_0_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.r3lay-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_r3lay_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.selenio_13p-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_selenio_13p_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.sencore_dmg-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_sencore_dmg_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.snell_probelrouter-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_snell_probelrouter_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.sony_nxlk-ip50y-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.sony_nxlk-ip51y-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.starfish_splicer-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_starfish_splicer_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.sublime-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_sublime_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tag_mcm9000-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tag_mcm9000_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tally-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tally_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.thomson_mxs-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_mxs_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.thomson_vibe-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_vibe_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns4200-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns4200_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns460-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns460_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns541-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns541_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns544-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns544_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns546-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns546_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tns547-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tns547_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tvg420-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg420_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tvg425-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg425_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tvg430-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg430_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tvg450-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg450_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tvg480-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg480_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.tx9-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_tx9_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.txedge-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_txedge_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.v__matrix-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.v__matrix_smv-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_smv_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.ventura-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_ventura_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.virtuoso-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.virtuoso_fa-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_fa_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.virtuoso_mi-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_mi_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.virtuoso_re-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_re_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.vizrt_vizengine-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_vizrt_vizengine_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.zman-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_zman_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.MLS-X1-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_MLS_X1_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.Panel-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_Panel_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.SC1-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_SC1_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.cna2-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_cna2_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.generic_external_control-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_generic_external_control_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.nsbus_generic_router-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_nsbus_generic_router_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.rcp3500-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_rcp3500_0_1_0]: ...

    @overload
    def create_device(
        self, driver: DriverLiteral
    ) -> InventoryDevice: ...  # Workaround to list all overloads in Intellisense

    def create_device(self, driver: DriverLiteral) -> InventoryDevice:
        """Method to create a new device configuration for VideoIPath-Inventory.
        Returns an empty InventoryDevice instance with the given driver.

        Args:
            driver (str): Driver of the device to create. (e.g. "com.nevion.NMOS_multidevice-0.1.0")

        Returns:
            InventoryDevice: Empty device configuration for the given driver.
        """
        return InventoryDevice.create(driver_id=str(driver))

    def add_device(
        self, device: InventoryDevice, label_check: bool = True, address_check: bool = True, config_only: bool = False
    ) -> InventoryDevice:
        """Method to add a device to VideoIPath-Inventory. Method will check if a device with same label or address already exists in inventory.
        After adding the device, the online configuration is returned as InventoryDevice instance.

        Raises:
            ValueError:  If device with same label or address already exists in inventory.

        Returns:
            InventoryDevice: Online configuration of the added device. Attention: device_id is set by VideoIPath-Inventory, so it is not known before adding the device.
        """
        if label_check:
            # Check if device with same label already exists in inventory:
            label = device.label
            devices_with_label = self._inventory_api.get_device_ids(label=label)
            if len(devices_with_label["active"]) > 0:
                raise ValueError(
                    f"Device with label '{label}' already exists in Inventory: {devices_with_label['active']}"
                )

        if address_check:
            # Check if device with same address already exists in inventory:
            address = device.address
            devices_with_address = self._inventory_api.get_device_ids(address=str(address))
            if len(devices_with_address["active"]) > 0:
                raise ValueError(
                    f"Device with address '{address}' already exists in Inventory: {devices_with_address['active']}"
                )

        online_device = self._inventory_api.add_device(device, config_only=config_only)
        self._logger.info(f"Device '{online_device.label}' added to Inventory with id '{online_device.device_id}'.")
        return online_device

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.NMOS-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.NMOS_multidevice-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_multidevice_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.abb_dpa_upscale_st-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_abb_dpa_upscale_st_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.adva_fsp150-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.adva_fsp150_xg400_series-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_adva_fsp150_xg400_series_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.agama_analyzer-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_agama_analyzer_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.altum_xavic_decoder-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_decoder_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.altum_xavic_encoder-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_altum_xavic_encoder_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.amagi_cloudport-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_amagi_cloudport_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.amethyst3-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_amethyst3_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.anubis-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_anubis_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.appeartv_x_platform-0.2.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_0_2_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.appeartv_x_platform_static-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_appeartv_x_platform_static_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.archwave_unet-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_archwave_unet_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.arista-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_arista_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ateme_cm4101-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm4101_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ateme_cm5000-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_cm5000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ateme_dr5000-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr5000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ateme_dr8400-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ateme_dr8400_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.avnpxh12-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_avnpxh12_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.aws_media-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_aws_media_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_7600_series-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_7600_series_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_asr-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_asr_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_catalyst_3850-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_catalyst_3850_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_me-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_me_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_nexus-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cisco_nexus_nbm-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cisco_nexus_nbm_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp330-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp330_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp4400-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp4400_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp505-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp505_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp511-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp511_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp515-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp515_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp524-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp524_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp525-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp525_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp540-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp540_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.cp560-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_cp560_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.demo-tns-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_demo_tns_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.device_up_driver-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_device_up_driver_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.dhd_series52-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_dhd_series52_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.dse892-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_dse892_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.dyvi-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_dyvi_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.electra-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_electra_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.embrionix_sfp-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_embrionix_sfp_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.emerge_enterprise-0.0.1"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_enterprise_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.emerge_openflow-0.0.1"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_emerge_openflow_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ericsson_avp2000-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_avp2000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ericsson_ce-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_ce_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ericsson_rx8200-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ericsson_rx8200_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_500fc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_500fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570fc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570itxe_hw_p60_udc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570itxe_hw_p60_udc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570j2k_x19_12e-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_12e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570j2k_x19_6e6d-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_6e6d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570j2k_x19_u9d-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_570j2k_x19_u9e-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_570j2k_x19_u9e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_5782dec-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782dec_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_5782enc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_5782enc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_7800fc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7800fc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_7880ipg8_10ge2-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7880ipg8_10ge2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_7882dec-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882dec_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.evertz_7882enc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_evertz_7882enc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.flexAI-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_flexAI_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.generic_emberplus-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_emberplus_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.generic_snmp-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_generic_snmp_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.gigacaster2-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_gigacaster2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.gredos-02.22.01"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_gredos_02_22_01]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.gv_kahuna-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_gv_kahuna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.haivision-0.0.1"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_haivision_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.huawei_cloudengine-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_cloudengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.huawei_netengine-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_huawei_netengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.iothink-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_iothink_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.iqoyalink_ic-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_ic_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.iqoyalink_le-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_iqoyalink_le_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.juniper_ex-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_juniper_ex_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.laguna-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_laguna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.lawo_ravenna-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_lawo_ravenna_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.liebert_nx-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_liebert_nx_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.maxiva-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.maxiva_uaxop4p6e-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxop4p6e_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.maxiva_uaxt30uc-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_maxiva_uaxt30uc_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.md8000-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_md8000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.mediakind_ce1-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_ce1_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.mediakind_rx1-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_mediakind_rx1_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.mock-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_mock_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.montone42-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_montone42_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.multicon-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_multicon_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.mwedge-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_mwedge_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nec_dtl_30-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtl_30_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nec_dtu_70d-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_70d_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nec_dtu_l10-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nec_dtu_l10_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.net_vision-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_net_vision_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nodectrl-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nodectrl_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nokia7210-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7210_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nokia7705-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nokia7705_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nso-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nso_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.nx4600-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_nx4600_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.openflow-0.0.1"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_openflow_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.powercore-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_powercore_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.prismon-1.0.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_prismon_1_0_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.r3lay-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_r3lay_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.selenio_13p-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_selenio_13p_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.sencore_dmg-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_sencore_dmg_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.snell_probelrouter-0.0.1"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_snell_probelrouter_0_0_1]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.sony_nxlk-ip50y-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip50y_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.sony_nxlk-ip51y-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_sony_nxlk_ip51y_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.starfish_splicer-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_starfish_splicer_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.sublime-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_sublime_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tag_mcm9000-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tag_mcm9000_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tally-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tally_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.thomson_mxs-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_mxs_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.thomson_vibe-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_thomson_vibe_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns4200-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns4200_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns460-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns460_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns541-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns541_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns544-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns544_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns546-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns546_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tns547-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tns547_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tvg420-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg420_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tvg425-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg425_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tvg430-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg430_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tvg450-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg450_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tvg480-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tvg480_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.tx9-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_tx9_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.txedge-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_txedge_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.v__matrix-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.v__matrix_smv-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_v__matrix_smv_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.ventura-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_ventura_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.virtuoso-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.virtuoso_fa-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_fa_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.virtuoso_mi-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_mi_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.virtuoso_re-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_re_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.vizrt_vizengine-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_vizrt_vizengine_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.nevion.zman-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_nevion_zman_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.MLS-X1-1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_MLS_X1_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.Panel-1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_Panel_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.SC1-1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_SC1_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.cna2-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_cna2_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.generic_external_control-1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_generic_external_control_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.nsbus_generic_router-1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_nsbus_generic_router_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[Literal["com.sony.rcp3500-0.1.0"]] = None,
    ) -> InventoryDevice[CustomSettings_com_sony_rcp3500_0_1_0]: ...

    @overload
    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[DriverLiteral] = None,
    ) -> InventoryDevice: ...  # Workaround to list all overloads in Intellisense

    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
        custom_settings_type: Optional[DriverLiteral] = None,
    ) -> InventoryDevice:
        """Method to get a online device from VideoIPath-Inventory by label, device_id or address as InventoryDevice instance.

        Args:
            label (str, optional): Label of the device to get.
            device_id (str, optional): Device ID of the device to get.
            address (str, optional): Address of the device to get.
            config_only (bool, optional): If True, only the configuration of the device is fetched.
            custom_settings_type (str, optional): Set optional driver_id to get Intellisense for custom settings.

        Raises:
            ValueError:  If more than one parameter is given.
            ValueError:  If no device with given label, device_id or address exists in inventory.
            ValueError:  If more than one device with given label or address exists in inventory.

        Returns:
            InventoryDevice: Online configuration of the requested device.
        """

        # Validate which parameter is given, raise error if more than one parameter is given!
        # & Check if device with given label, device_id or address exists in inventory, raise error if not!
        if sum([1 for x in [label, device_id, address] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either label, device_id or address.")
        if label is not None:
            devices = self._inventory_api.get_device_ids(label=label)
            if len(devices["active"]) == 0:
                if validate_device_id_string(device_id=label, include_virtual=False):
                    self._logger.warning(
                        f"It seems that the provided label '{label}' is a device_id. Please use get_device(device_id='{label}') instead."
                    )
                raise ValueError(f"No device with label '{label}' found in Inventory.")
            if len(devices["active"]) > 1:
                raise ValueError(f"More than one device with label '{label}' found in Inventory: {devices['active']}")
            device_id = devices["active"][0]
        elif device_id is not None:
            if validate_device_id_string(device_id=device_id, include_virtual=False):
                if not self._inventory_api.device_id_exists(device_id):
                    raise ValueError(f"No device with id '{device_id}' found in Inventory.")
            else:
                raise ValueError(f"Invalid device_id '{device_id}' provided!")
        elif address is not None:
            devices = self._inventory_api.get_device_ids(address=str(address))
            if len(devices["active"]) == 0:
                raise ValueError(f"No device with address '{address}' found in Inventory.")
            if len(devices["active"]) > 1:
                raise ValueError(
                    f"More than one device with address '{address}' found in Inventory: {devices['active']}"
                )
            device_id = devices["active"][0]

        # Get online configuration of device from VideoIPath-Inventory and return configured InventoryDevice instance:
        if type(device_id) is not str:
            raise ValueError("device_id must be a string.")
        online_device = self._inventory_api.get_device(
            device_id=device_id, config_only=config_only, custom_settings_type=custom_settings_type
        )
        return online_device

    def update_device(self, device: InventoryDevice) -> InventoryDevice:
        """Method to update a device in VideoIPath-Inventory.
        Returns the online configuration of the updated device as InventoryDevice instance.

        Raises:
            ValueError:  If no device_id is given in device configuration (in InventoryDevice instance).

        Returns:
            InventoryDevice: Online configuration of the updated device.
        """
        if "device" not in device.device_id:
            raise ValueError(
                "No device_id given in device configuration. Please pull the device configuration from VideoIPath-Inventory."
            )
        online_device = self._inventory_api.update_device(device)

        self._logger.info(f"Device '{online_device.label}' updated in Inventory with id '{online_device.device_id}'.")
        return online_device

    def diff_device_configuration(
        self, reference_device: InventoryDevice, staged_device: InventoryDevice
    ) -> "InventoryDeviceComparison":
        """Method to compare two devices from VideoIPath-Inventory.
        Returns a dictionary with the differences between the two devices.
        """
        comparison = InventoryDeviceComparison.analyze_inventory_devices(reference_device, staged_device)
        return comparison

    def remove_device(self, device_id: str, check_remove: bool = True):
        """Method to remove a device from VideoIPath-Inventory"""
        if not validate_device_id_string(device_id=device_id, include_virtual=False):
            message = f"Device id '{device_id}' is not a valid device id."
            self._logger.debug(message)
            raise ValueError(message)

        if not self._inventory_api.device_id_exists(device_id):
            message = f"Device with id '{device_id}' not found in Inventory."
            self._logger.debug(message)
            raise ValueError(message)

        response = self._inventory_api.remove_device(device_id)

        if check_remove:
            if response.header.status != "OK":
                message = f"Failed to remove device from VideoIPath-Inventory. Error: {response}"
                self._logger.debug(message)
                raise ValueError(message)

            if self._inventory_api.device_id_exists(device_id):
                message = (
                    f"Failed to remove device from VideoIPath-Inventory. Device with id '{device_id}' still exists."
                )
                self._logger.debug(message)
                raise ValueError(message)
            else:
                self._logger.info(f"Device with id '{device_id}' removed from Inventory.")

    def check_device_exists(self, label: str) -> None | List[str]:
        """Method to check if a device with the given user-defined label exists in VideoIPath-Inventory.
        Returns List of device_ids with the given label.
        If no device with the given label exists, None is returned.
        """
        devices = self._inventory_api.device_label_exists(label)
        return devices

    @staticmethod
    def dump_configuration(device: InventoryDevice) -> dict:
        """Method to dump the configuration of a device as dictionary."""
        return device.dump_configuration()

    @staticmethod
    def parse_configuration(config: dict) -> InventoryDevice:
        """Method to parse a configuration dictionary to a InventoryDevice instance."""
        return InventoryDevice.parse_configuration(config)
