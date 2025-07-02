from typing import Annotated, Generic

from pydantic import BaseModel, Field
from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettingsType
from videoipath_automation_tool.validators.uuid_4 import validate_uuid_4


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

    @property
    def use_global_snmp_settings(self) -> bool:
        """Use (activate) global SNMP settings."""
        return self.cinfoOverrides.snmp.useDefault

    @use_global_snmp_settings.setter
    def use_global_snmp_settings(self, value: bool):
        """Use (activate) global SNMP settings."""
        self.cinfoOverrides.snmp.useDefault = value

    def get_global_snmp_setting_id(self) -> str:
        """
        Returns the ID of the global SNMP setting currently in use.

        Returns:
            str: The ID of the global SNMP setting.
                - "default" if the system's default configuration is used.
                - Otherwise, returns the UUID of the configured global SNMP setting.
                Note: Retrieve the Label of the global SNMP setting using:
                `app.inventory.get_global_snmp_config_label_by_id(id)`
        """
        return self.cinfoOverrides.snmp.id

    def set_global_snmp_setting(self, setting_id: str, activate: bool = True):
        """
        Sets the global SNMP setting by ID.

        Args:
            setting_id (str): The ID of the global SNMP setting to use.
                - Use "default" to apply the system's default configuration.
                - For other configurations, retrieve the ID by label using:
                    `app.inventory.get_global_snmp_config_id_by_label(label)`

            activate (bool): Whether to activate the global SNMP settings (`use_global_snmp_settings = True`).
                Defaults to True. Set to False if you only want to store the ID without activating it yet.

        Raises:
            ValueError: If the setting ID is empty or not a valid UUID (unless "default").
        """
        if not setting_id:
            raise ValueError("Setting ID cannot be empty.")
        if setting_id != "default":
            setting_id = validate_uuid_4(setting_id)

        self.cinfoOverrides.snmp.id = setting_id

        if activate:
            self.cinfoOverrides.snmp.useDefault = True

    # --- Deprecated properties ---
    @property
    @deprecated("The property `custom` is deprecated, use `custom_settings` instead.")
    def custom(self) -> CustomSettingsType:
        return self.custom_settings
