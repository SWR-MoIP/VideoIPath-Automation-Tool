from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from videoipath_automation_tool.utils.cross_app_utils import generate_uuid_4

# REST V2 Model


# --- Enumerates ---
class AlarmTemplate(str, Enum):
    NONE = "None"
    NORMAL_BOOKING_WITH_LOS = "booking.normal"
    SIPS_BOOKING_WITH_LOS_LOR = "booking.sips"


class AlarmGroupTemplate(str, Enum):
    NONE = "None"
    NORMAL_BOOKING_WITH_LOS = "booking.normal"
    SIPS_BOOKING_WITH_LOS_LOR = "booking.sips"


class QOSEnum(str, Enum):
    CS0_00000000 = "00000000"
    CS1_00100000 = "00100000"
    CS2_01000000 = "01000000"
    CS3_01100000 = "01100000"
    CS4_10000000 = "10000000"
    CS5_10100000 = "10100000"
    CS6_11000000 = "11000000"
    CS7_11100000 = "11100000"
    AF11_DSCP10_00101000 = "00101000"
    AF12_DSCP12_00110000 = "00110000"
    AF13_DSCP14_00111000 = "00111000"
    AF21_DSCP18_01001000 = "01001000"
    AF22_DSCP20_01010000 = "01010000"
    AF23_DSCP22_01011000 = "01011000"
    AF31_DSCP26_01101000 = "01101000"
    AF32_DSCP28_01110000 = "01110000"
    AF33_DSCP30_01111000 = "01111000"
    AF41_DSCP34_10001000 = "10001000"
    AF42_DSCP36_10010000 = "10010000"
    AF43_DSCP38_10011000 = "10011000"
    VA_DSCP44_10110000 = "10110000"
    EF_DSCP46_10111000 = "10111000"


class VLANPriorityEnum(str, Enum):
    USE_CARD_SETTINGS = "Use Card Setting"
    BK_BACKGROUND = "BK"
    BE_BEST_EFFORT = "BE"
    EE_EXCELLENT_EFFORT = "EE"
    CA_CRITICAL_APPLICATIONS = "CA"
    VI_VIDEO = "VI"
    VO_VOICE = "VO"
    IC_INTERNETWORK_CONTROL = "IC"
    NC_NETWORK_CONTROL = "NC"


class VLANSeparationEnum(str, Enum):
    NONE = "None"
    STATIC_ONLY = "Static Only"
    AUTOMATIC = "Automatic"


class PacketLen(int, Enum):
    _188 = 188
    _204 = 204


class Protection(str, Enum):
    NONE = "None"
    SIPS = "SIPS"
    SIPS_HIGHEST_RESILIENCE = "SIPS (highest resilience)"
    EPP_ACTIVE = "EPP (active)"
    EPP_PASSIVE = "EPP (passive)"
    PPR = "PPR"
    DPR = "DPR"


class SeverityTriggerLevel(int, Enum):
    DISABLED = 0
    CLEARED = 1
    NOTIFICATION = 2
    WARNING = 3
    MINOR = 4
    MAJOR = 5
    CRITICAL = 6


class SaTriggerLevel(int, Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class FecsEnum(str, Enum):
    NONE = "None"
    SINGLE = "Single"
    DOUBLE = "Double"


class OverheadEnum(int, Enum):
    NONE = 0
    PERCENT_1 = 1
    PERCENT_2 = 2
    PERCENT_3 = 3
    PERCENT_4 = 4
    PERCENT_5 = 5
    PERCENT_6 = 6
    PERCENT_8 = 8
    PERCENT_10 = 10
    PERCENT_12 = 12
    PERCENT_15 = 15
    PERCENT_25 = 25


class GopStruct(str, Enum):
    AUTOMATIC = "Automatic"
    IP = "IP"
    IPB = "IPB"
    IPBB = "IPBB"
    IPBBB = "IPBBB"
    IPBBBB = "IPBBBB"


class SubSampling(str, Enum):
    _4_2_0 = "4:2:0"
    _4_2_2 = "4:2:2"


class VideoDepth(str, Enum):
    _8_BIT = "8 bit"
    _10_BIT = "10 bit"


class VideoCodec(str, Enum):
    MPEG_2 = "MPEG-2"
    H_264 = "H.264"
    H_265 = "H.265"
    AVC_I_50 = "AVC-I 50"
    AVC_I_100 = "AVC-I 100"
    JPEG_2000 = "J2K"
    TICO = "TICO"


class EntropyEncoding(str, Enum):
    CAVLC = "CAVLC"
    CABAC = "CABAC"


class AudioCodec(str, Enum):
    MPEG_1_LAYER_2 = "MPEG-1 Layer 2"
    AAC_LC = "AAC_LC"
    AAC_HE = "AAC_HE"
    SMPTE_302M = "SMPTE 302M"
    DOLBY_E = "Dolby E"
    DOLBY_DIGITAL = "Dolby Digital"


class RateEnumMPEG1Layer2(int, Enum):
    _32 = 32
    _48 = 48
    _56 = 56
    _64 = 64
    _80 = 80
    _96 = 96
    _112 = 112
    _128 = 128
    _160 = 160
    _192 = 192
    _224 = 224
    _256 = 256
    _320 = 320
    _384 = 384


class RateEnumAAC(int, Enum):
    _16 = 16
    _20 = 20
    _24 = 24
    _28 = 28
    _32 = 32
    _40 = 40
    _48 = 48
    _56 = 56
    _64 = 64
    _80 = 80
    _96 = 96
    _112 = 112
    _128 = 128
    _160 = 160
    _192 = 192
    _224 = 224
    _256 = 256


class RateEnumDolbyDigital(int, Enum):
    _40 = 40
    _48 = 48
    _56 = 56
    _64 = 64
    _80 = 80
    _96 = 96
    _112 = 112
    _128 = 128
    _160 = 160
    _192 = 192
    _224 = 224
    _256 = 256
    _320 = 320
    _384 = 384
    _448 = 448
    _512 = 512
    _576 = 576
    _640 = 640


SMPTE_302M_FIXED_RATE = 64


# Enums 2110 Video
class BitDepthEnum(str, Enum):
    _8_BIT = "8 bit"
    _10_BIT = "10 bit"
    _12_BIT = "12 bit"
    _16_BIT = "16 bit"
    _16F_BIT = "16f bit"


class ColorimetryEnum(str, Enum):
    BT601 = "BT601"
    BT709 = "BT709"
    BT2020 = "BT2020"
    BT2100 = "BT2100"


class ExactFramerateEnum(str, Enum):
    _24 = "24"
    _25 = "25"
    _29_97 = "30000/1001"
    _30000_1001 = "30000/1001"
    _30 = "30"
    _50 = "50"
    _59_94 = "60000/1001"
    _60000_1001 = "60000/1001"
    _60 = "60"


class PackedModeEnum(str, Enum):
    # _2110BPM = "2110BPM"
    # _2110GPM = "2110GPM"
    GPM_GENERAL_PACKING_MODE = "2110GPM"
    BLOCK_PACKING_MODE = "2110BPM"


class ResolutionEnum(str, Enum):
    _480I = "480i"
    _576I = "576i"
    _720P = "720p"
    _1080I = "1080i"
    _1080P = "1080p"
    _2160P = "2160p"


class SamplingEnum(str, Enum):
    _4_2_0 = "4:2:0"
    _4_2_2 = "4:2:2"
    _4_4_4 = "4:4:4"


class TcsEnum(str, Enum):
    SDR = "SDR"
    PQ = "PQ"
    HLG = "HLG"
    SLOG3 = "SLOG3"


class TpEnum(str, Enum):
    NARROW = "2110TPN"
    NARROW_LINEAR = "2110TPNL"
    WIDE = "2110TPW"


class BitDepth2110AudioEnum(str, Enum):
    L16 = "L16"
    L20 = "L20"
    L24 = "L24"
    L32 = "L32"
    AM824 = "AM824"


class SampleRate2210AudioEnum(int, Enum):
    _44100HZ = 44100
    _48000HZ = 48000
    _96000HZ = 96000


# --- Sub Models ---
class AlarmOptions(BaseModel):
    reportDriverAlarms: bool = Field(
        default=False, description="'No contact' device alarms"
    )  # General / Templates and alarms
    includeParentModules: bool = Field(default=False, description="Include parent module alerts")  # ...
    reportDisabledDrivers: bool = Field(default=False, description="Disabled device drivers")  # ...
    ignoreAlarmsOnCreate: bool = Field(default=False, description="Ignore alarms on create")  # Network / Routing
    ignoreAlarmsOnReroute: bool = Field(default=False, description="Ignore alarms on reroute")  # ...


class MetricOptions(BaseModel):
    detectFlowLoss: bool = Field(default=False, description="Raise flow loss alarm")  # Templates and alarms


class ConstraintSets(BaseModel):
    useConstraintSets: bool = Field(default=False, description="Use constraint sets")
    mainFormatsOpt1: List[str] = Field(default=[], description="MainFormats: Constrainer set 1")
    mainFormatsOpt2: List[str] = Field(default=[], description="MainFormats: Constrainer set 2")
    spareFormatsOpt1: List[str] = Field(default=[], description="SpareFormats: Constrainer set 1")
    spareFormatsOpt2: List[str] = Field(default=[], description="SpareFormats: Constrainer set 2")


class RoutingOptions(BaseModel):
    preferReuseMcPath: bool = Field(default=True, description="Prefer reuse of multicast path")


class Constraints(BaseModel):
    VLANSeparation: VLANSeparationEnum = Field(default=VLANSeparationEnum.NONE, description="VLAN Separation")
    VLANPriority: VLANPriorityEnum = Field(default=VLANPriorityEnum.USE_CARD_SETTINGS, description="VLAN Priority")
    QOS: QOSEnum = Field(default=QOSEnum.CS0_00000000, description="Quality of Service")


class DefaultUdpPorts(BaseModel):
    main: int = Field(ge=1, le=65535, description="Main UDP port")
    spare: int = Field(ge=1, le=65535, description="Spare UDP port")


class DefaultTxVlans(BaseModel):
    main: int = Field(ge=1, le=4096, description="Main TX VLAN")
    spare: int = Field(ge=1, le=4096, description="Spare TX VLAN")


class DefaultMCPools(BaseModel):
    main: str = Field(default="", description="Main Multicast pool")
    spare: str = Field(default="", description="Spare Multicast pool")


class Sips(BaseModel):
    launchBuffer: int = Field(ge=0, le=65535, default=0, description="Launch buffer")
    preBuffer: int = Field(ge=0, le=65535, default=0, description="Pre-buffering")


class RedundancyControl(BaseModel):
    enable: bool = Field(default=False, description="Enable 'Redundancy controller' under Protection Tab.")
    initWaitTime: int = Field(ge=0, le=600000, default=30000)
    confirmTime: int = Field(ge=0, le=60000, default=5000)
    waitTime: int = Field(ge=2000, le=600000, default=30000)
    waitBackoffFactor: int = Field(ge=1, le=20, default=2)
    maxWaitTimeFactor: int = Field(ge=1, le=100000, default=20)
    waitRandomnessFactor: int = Field(ge=1, le=10, default=1)
    severityTriggerLevel: SeverityTriggerLevel = Field(
        default=SeverityTriggerLevel.MINOR, description="Severity trigger level"
    )
    saTriggerLevel: SaTriggerLevel = Field(default=SaTriggerLevel.FULL, description="Service affecting trigger level")
    ignoreCommonTailNodes: bool = Field(default=False, description="Ignore common tail nodes")


class MbbOptions(BaseModel):
    waitTimeMillis: int = Field(ge=0, le=10000, default=1000, description="Wait time (milliseconds)")


class MpegVideo(BaseModel):
    videoCodec: VideoCodec = Field(default=VideoCodec.H_264, description="Video codec")
    videoDepth: VideoDepth = Field(default=VideoDepth._8_BIT, description="Video sample depth")
    subSampling: SubSampling = Field(default=SubSampling._4_2_2, description="Chroma subsampling")
    gopStruct: GopStruct = Field(default=GopStruct.AUTOMATIC, description="GOP structure")
    entropyEncoding: EntropyEncoding = Field(default=EntropyEncoding.CAVLC, description="Entropy encoding")
    gopSize: int = Field(ge=0, le=65535, default=30, description="GOP size")


class Smpte2110CfgAudio(BaseModel):
    bitDepth: BitDepth2110AudioEnum = Field(default=BitDepth2110AudioEnum.L24, description="Bit depth")
    frameSize: None | int = Field(
        ge=1, le=700, default=None, description="Samples per frame"
    )  # New GUI-Profile Default: None
    linkOffset: None | int = Field(
        ge=0, le=10000000, default=None, description="Link offset (us)"
    )  # New GUI-Profile Default: None
    nChannels: int = Field(ge=1, le=256, default=2, description="Number of channels")
    sampleRate: SampleRate2210AudioEnum = Field(default=SampleRate2210AudioEnum._48000HZ, description="Sampling rate")


class Smpte2110CfgVideo(BaseModel):
    bitDepth: BitDepthEnum = Field(default=BitDepthEnum._10_BIT, description="Bit depth")
    colorimetry: ColorimetryEnum = Field(default=ColorimetryEnum.BT709, description="Colorimetry")
    exactFramerate: ExactFramerateEnum = Field(default=ExactFramerateEnum._25, description="Framerate")
    packedMode: PackedModeEnum = Field(default=PackedModeEnum.GPM_GENERAL_PACKING_MODE, description="Packing mode")
    resolution: ResolutionEnum = Field(default=ResolutionEnum._1080I, description="Resolution")
    sampling: SamplingEnum = Field(default=SamplingEnum._4_2_2, description="Sub sampling")
    tcs: TcsEnum = Field(default=TcsEnum.SDR, description="Transfer characteristic system (TCS)")
    tp: TpEnum = Field(default=TpEnum.NARROW_LINEAR, description="Media type parameter (TP)")


class Smpte2110Cfg(BaseModel):
    ptpDomain: int = Field(ge=0, le=127, default=0, description="PTP domain")
    rtpPayloadType: int = Field(ge=96, le=127, default=96, description="RTP payload type")
    video: Smpte2110CfgVideo = Field(default_factory=Smpte2110CfgVideo)
    audio: Smpte2110CfgAudio = Field(default_factory=Smpte2110CfgAudio)


class AudioPair(BaseModel):
    codec: AudioCodec = Field(default=AudioCodec.MPEG_1_LAYER_2, description="Codec")
    enabled: bool = Field(default=False, description="Enable")
    rate: Union[int, RateEnumMPEG1Layer2, RateEnumAAC, RateEnumDolbyDigital] = Field(
        description="Bitrate (Kbit/s)", default=384
    )  # New GUI-Profile Default: 384

    @field_validator("rate")
    def validate_rate(cls, rate, info):
        codec = info.data.get("codec")

        # Konvertiere die Enum-Werte in eine Liste der Integer-Werte
        if codec == AudioCodec.MPEG_1_LAYER_2 and rate not in [e.value for e in RateEnumMPEG1Layer2]:
            raise ValueError(f"Invalid rate for {codec}. Must be one of {list(e.value for e in RateEnumMPEG1Layer2)}")
        elif codec in (AudioCodec.AAC_LC, AudioCodec.AAC_HE) and rate not in [e.value for e in RateEnumAAC]:
            raise ValueError(f"Invalid rate for {codec}. Must be one of {list(e.value for e in RateEnumAAC)}")
        elif codec == AudioCodec.SMPTE_302M and rate != SMPTE_302M_FIXED_RATE:
            raise ValueError(f"Invalid rate for {codec}. Rate must be {SMPTE_302M_FIXED_RATE}")
        elif codec == AudioCodec.DOLBY_E and not (16 <= rate <= 640):
            raise ValueError(f"Invalid rate for {codec}. Rate must be between 16 and 640")
        elif codec == AudioCodec.DOLBY_DIGITAL and rate not in [e.value for e in RateEnumDolbyDigital]:
            raise ValueError(f"Invalid rate for {codec}. Must be one of {list(e.value for e in RateEnumDolbyDigital)}")

        return rate

    # RateSMPTE302M
    # => No Rate (fixed to 64)

    # RateEnumDolbyE
    # variable int 16 - 640


class AudioCfg(BaseModel):
    p1: AudioPair = Field(default_factory=AudioPair, description="Audio pair 1")
    p2: AudioPair = Field(default_factory=AudioPair, description="Audio pair 2")
    p3: AudioPair = Field(default_factory=AudioPair, description="Audio pair 3")
    p4: AudioPair = Field(default_factory=AudioPair, description="Audio pair 4")
    p5: AudioPair = Field(default_factory=AudioPair, description="Audio pair 5")
    p6: AudioPair = Field(default_factory=AudioPair, description="Audio pair 6")
    p7: AudioPair = Field(default_factory=AudioPair, description="Audio pair 7")
    p8: AudioPair = Field(default_factory=AudioPair, description="Audio pair 8")


# --- Main Model / Super Profile ---
class SuperProfile(BaseModel):
    # (GUI HIDDEN)
    timestamp: int = 0
    type: str = "profile"
    # GENERAL
    # - Meta
    active: bool = Field(default=True, description="Active")
    hidden: bool = Field(default=False, description="Hide profile for manual connection")
    name: str = Field(default="", description="Profile name")
    description: str = Field(default="", description="Description")
    tags: List[str] = []
    # - Templates and alarms
    alarmTemplate: None | AlarmTemplate = Field(
        default=None, description="Alarm template"
    )  # New GUI-Profile Default: None (Instead of AlarmTemplate.NONE)
    alarmGroupTemplate: None | AlarmGroupTemplate = Field(
        default=None, description="Alarm group template"
    )  # New GUI-Profile Default: None (Instead of AlarmGroupTemplate.NONE)
    alarmOptions: AlarmOptions = Field(default_factory=AlarmOptions)
    metricOptions: MetricOptions = Field(default_factory=MetricOptions)  # also in Network!
    # NETWORK
    # - Constraints
    formats: List[str] = Field(default=[], description="Allowed formats (optional)")
    maxBand: float | int = Field(default=20, ge=0, description="Maximum IP bandwidth (Mbit/s)")
    doIngressPolice: bool = Field(default=False, description="Configure ingress policy")
    # - Constraint sets
    constraintSets: ConstraintSets = Field(default_factory=ConstraintSets)
    # - Routing
    routingOptions: RoutingOptions = Field(default_factory=RoutingOptions)
    # - Ethernet/IP
    constraints: Constraints = Field(default_factory=Constraints)
    ttl: int = Field(default=20, ge=0, le=255, description="Time to live")
    defaultUdpPorts: Optional[DefaultUdpPorts] = Field(default=None, description="Assign Default UDP ports")
    defaultTxVlans: Optional[DefaultTxVlans] = Field(default=None, description="Assign Default TX VLANs")
    defaultMCPools: Optional[DefaultMCPools] = Field(default=None, description="Assign Default Multicast pools")
    # - Transport Stream
    tsband: float | int = Field(default=10, ge=0, description="TS bandwidth (Mbit/s)")
    packets: int = Field(default=7, ge=1, le=7, description="TS packets per frame")
    packetLen: PacketLen = Field(default=PacketLen._188, description="TS packets length (bytes")
    ipband: float | int = Field(
        default=15, ge=0, description="IP bandwidth (Mbit/s)"
    )  # New GUI-Profile Default: 15. Float for backward compatibility
    keepSendersEnabled: bool = Field(default=False, description="Keep senders enabled")
    # PROTECTION
    # - Mode
    protection: Protection = Field(default=Protection.NONE)
    sips: Sips = Field(default_factory=Sips, description="Pre-buffering and Launch buffer")
    # - Redundancy controller
    redundancyControl: RedundancyControl = Field(default_factory=RedundancyControl)
    # - Make-Before-Break
    mbbOptions: MbbOptions = Field(default_factory=MbbOptions, description="Make-Before-Break")
    # - FEC
    fecs: FecsEnum = Field(default=FecsEnum.NONE, description="Mode")
    fecc: int = Field(default=4, ge=0, le=65535, description="Columns (L)")
    fecr: int = Field(default=4, ge=0, le=65535, description="Rows (D)")
    overhead: OverheadEnum = Field(default=OverheadEnum.NONE, description="Overhead")
    fecsk: bool = Field(default=False, description="Skew")

    # CODEC
    # - Video
    mpegVideo: MpegVideo = Field(default_factory=MpegVideo, description="Video")
    # - Audio
    audioCfg: AudioCfg = Field(default_factory=AudioCfg, description="Audio")

    # - SMPTE2110
    smpte2110Cfg: Smpte2110Cfg = Field(default_factory=Smpte2110Cfg, description="SMPTE2110")
    # CUSTOM
    custom: dict = {}


# --- Main Model ---
class Profile(SuperProfile):
    # (GUI HIDDEN)
    id: None | str = Field(default=None, alias="_id")
    vid: None | str = Field(default=None, alias="_vid")
    rev: None | str = Field(default=None, alias="_rev")

    @classmethod
    def create(cls, name: str):
        """
        Create a new Profile object with a unique ID and VID.
        """
        id = generate_uuid_4()
        vid = f"_: {id}"
        return cls(_id=id, _vid=vid, name=name)
