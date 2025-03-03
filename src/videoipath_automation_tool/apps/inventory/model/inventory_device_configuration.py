from typing import Annotated, Generic

from pydantic import BaseModel, Field
from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettingsType


class CinfoOverridesSNMP(BaseModel, validate_assignment=True):
    useDefault: bool = True
    id: str = "default"


class CinfoOverridesHTTP(BaseModel, validate_assignment=True):
    useDefault: bool = False
    id: str = "default"


class CinfoOverrides(BaseModel, validate_assignment=True):
    snmp: CinfoOverridesSNMP = Field(default_factory=CinfoOverridesSNMP)
    http: CinfoOverridesHTTP = Field(default_factory=CinfoOverridesHTTP)


class DriverInfos(BaseModel, validate_assignment=True):
    name: str = ""
    organization: str = ""
    version: str = ""


class Protocol(BaseModel, validate_assignment=True):
    preferredVersion: int = 1
    retries: int = 1
    maxRepetitions: int = 10
    useGetBulk: bool = True
    timeout: int = 5000
    localEngineId: str = ""


class Read(BaseModel, validate_assignment=True):
    level: int = 1
    user: str = ""
    community: str = "public"


class Write(BaseModel, validate_assignment=True):
    level: int = 1
    user: str = ""
    community: str = "private"


class Security(BaseModel, validate_assignment=True):
    read: Read = Field(default_factory=Read)
    write: Write = Field(default_factory=Write)


class CinfoSnmp(BaseModel, validate_assignment=True):
    users: dict = {}
    security: Security = Security()
    protocol: Protocol = Protocol()


class CinfoHttp(BaseModel, validate_assignment=True):
    https: bool = False
    httpAuth: int = 0
    trustAllCertificates: bool = False


class Auth(BaseModel, validate_assignment=True):
    user: str = ""
    password: str = ""


class Traps(BaseModel, validate_assignment=True):
    trapDestinations: list = []
    trapType: str = "Trap"
    user: str = "videoipath"


class Cinfo(BaseModel, validate_assignment=True):
    protocols: dict = {}
    altAddresses: list = []
    altAddressesWithAuth: list = []
    auth: None | Auth = None
    http: CinfoHttp = CinfoHttp()
    snmp: CinfoSnmp = CinfoSnmp()
    address: str = "192.168.0.1"
    socketTimeout: None | str = None
    traps: None | Traps = Traps()


class Desc(BaseModel, validate_assignment=True):
    desc: str = ""
    label: str = ""


class Config(BaseModel, Generic[CustomSettingsType]):
    cinfo: Cinfo = Cinfo()
    driver: DriverInfos = DriverInfos()
    desc: Desc = Desc()
    customSettings: Annotated[
        CustomSettingsType,
        Field(..., discriminator="driver_id"),
        # Note:
        # This is the discriminator field for the customSettings!
        # Information about "Union Discriminator" concept can be found here:
        # https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators
    ]


class DeviceConfiguration(BaseModel, Generic[CustomSettingsType], validate_assignment=True):
    """DeviceConfiguration class is used to represent a device configuration in inventory."""

    cinfoOverrides: CinfoOverrides = CinfoOverrides()
    config: Config[CustomSettingsType]
    meta: dict = {}
    active: bool = True
    id: str = ""

    @property
    def address(self):
        return self.config.cinfo.address

    @address.setter
    def address(self, value):
        self.config.cinfo.address = value

    @property
    def label(self):
        return self.config.desc.label

    @label.setter
    def label(self, value):
        self.config.desc.label = value

    @property
    def description(self):
        return self.config.desc.desc

    @description.setter
    def description(self, value):
        self.config.desc.desc = value

    @property
    def username(self):
        if self.config.cinfo.auth is None:
            raise ValueError("No user set in device configuration.")
        return self.config.cinfo.auth.user

    @username.setter
    def username(self, value):
        if self.config.cinfo.auth is None:
            self.config.cinfo.auth = Auth()
        self.config.cinfo.auth.user = value

    @property
    def password(self):
        if self.config.cinfo.auth is None:
            raise ValueError("No password set in device configuration.")
        return self.config.cinfo.auth.password

    @password.setter
    def password(self, value):
        if self.config.cinfo.auth is None:
            self.config.cinfo.auth = Auth()
        self.config.cinfo.auth.password = value

    @property
    def custom_settings(self) -> CustomSettingsType:
        return self.config.customSettings

    @property
    def device_id(self):
        return self.id

    @property
    def metadata(self):
        return self.meta

    @metadata.setter
    def metadata(self, value):
        self.meta = value

    # --- Deprecated properties ---
    @property
    @deprecated("The property `custom` is deprecated, use `custom_settings` instead.")
    def custom(self) -> CustomSettingsType:
        return self.custom_settings
