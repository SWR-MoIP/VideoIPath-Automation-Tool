from enum import Enum
from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _validate_engine_id_format(engine_id: str) -> str:
    """
    Basic format check for SNMPv3 Engine ID.
    - Allows empty string
    - Must be valid hex string (after cleaning)
    - Length: 5–32 bytes (10–64 hex digits)
    - No RFC compliance guaranteed
    """
    if not engine_id:
        return engine_id  # allowed for v1/v2c

    cleaned = engine_id.replace(":", "").replace(" ", "").lower()

    if len(cleaned) % 2 != 0:
        raise ValueError("Engine ID must contain full bytes (even number of hex digits)")

    try:
        raw = bytes.fromhex(cleaned)
    except ValueError:
        raise ValueError("Engine ID must be a valid hex string")

    if not (5 <= len(raw) <= 32):
        raise ValueError("Engine ID must be 5–32 bytes long")

    return cleaned


# --- User Enum Classes ---
class SecurityLevel(int, Enum):
    UNDEFINED = 0
    """Undefined security level."""
    NO_AUTH_NO_PRIV = 1
    """NoAuthNoPriv | Without authentication and without privacy."""
    AUTH_NO_PRIV = 2
    """AuthNoPriv | With authentication but without privacy."""
    AUTH_PRIV = 3
    """AuthPriv | With authentication and with privacy."""


class AuthProtocol(int, Enum):
    MD5 = 2
    """MD5 | HMAC-MD5-96 digest authentication protocol."""
    SHA = 3
    """SHA | HMAC-SHA-96 digest authentication protocol."""


class PrivProtocol(int, Enum):
    DES = 2
    """DES | CBC-DES symmetric encryption protocol."""
    THREE_DES = 3
    """3DES | 3DES-EDE symmetric encryption protocol."""
    AES128 = 4
    """AES127 | CFB128-AES-128 privacy protocol."""


# --- Version Enum Class ---
class SnmpVersion(int, Enum):
    V1 = 0
    """SNMP version 1."""
    V2C = 1
    """SNMP version 2 with community security."""
    V3 = 3
    """SNMP version 3."""


# --- Data Model Classes ---
class SnmpUser(BaseModel, validate_assignment=True):
    level: SecurityLevel = SecurityLevel.NO_AUTH_NO_PRIV
    name: str = "New User"
    authProtocol: AuthProtocol = AuthProtocol.MD5
    privProtocol: PrivProtocol = PrivProtocol.DES
    engineId: str = ""
    privPassword: str = ""
    authPassword: str = ""

    @field_validator("engineId")
    def validate_engine_id(cls, value: str) -> str:
        """
        Validates the SNMPv3 Engine ID format.
        - Allows empty string
        - Must be valid hex string (after cleaning)
        - Length: 5–32 bytes (10–64 hex digits)
        """
        return _validate_engine_id_format(value)


class SnmpDescriptor(BaseModel, validate_assignment=True):
    label: str = ""
    desc: str = ""


class SnmpSecurityEntry(BaseModel, validate_assignment=True):
    user: str = ""  # User ID from "Users" section. Must be a valid UUID of an existing user.
    community: str = ""  # Value from "Protocol Settings => SNMP v1/v2c Security => Write / Read community"


class SnmpSecurity(BaseModel, validate_assignment=True):
    read: SnmpSecurityEntry = SnmpSecurityEntry(community="public")
    write: SnmpSecurityEntry = SnmpSecurityEntry(community="private")


class SnmpProtocolSettings(BaseModel, validate_assignment=True):
    preferredVersion: SnmpVersion = SnmpVersion.V2C
    retries: int = Field(default=1, ge=0)
    maxRepetitions: int = Field(default=10, ge=0)
    useGetBulk: bool = True
    timeout: int = Field(default=5000, ge=0)
    localEngineId: str = ""

    @field_validator("localEngineId")
    @classmethod
    def validate_engine_id(cls, value: str) -> str:
        return _validate_engine_id_format(value)


class SnmpConfiguration(BaseModel, validate_assignment=True):
    id: str = Field(alias="_id")
    descriptor: SnmpDescriptor = Field(default_factory=SnmpDescriptor)
    users: dict[str, SnmpUser] = Field(default_factory=dict)
    security: SnmpSecurity = Field(default_factory=SnmpSecurity)
    protocol: SnmpProtocolSettings = Field(default_factory=SnmpProtocolSettings)

    @classmethod
    def create(cls):
        """
        Creates a new instance of SnmpConfiguration with default values.

        Returns:
            SnmpConfiguration: A new instance of SnmpConfiguration.
        """
        config_id = str(uuid4())
        return cls(
            _id=config_id,
            descriptor=SnmpDescriptor(label="New SNMP Configuration", desc=""),
        )

    @classmethod
    def parse_from_dict(cls, data: dict) -> "SnmpConfiguration":
        """
        Parses a dictionary into a SnmpConfiguration instance.

        Args:
            data (dict): The dictionary to parse.

        Returns:
            SnmpConfiguration: An instance of SnmpConfiguration.
        """
        if len(data.keys()) == 1:
            config_id = list(data.keys())[0]
            data = data[config_id]
            data["_id"] = config_id
        else:
            raise ValueError("Data dictionary must contain exactly one key/value pair: <id>: <configuration>")
        return cls(**data)

    # --- Getters and Setters ---
    @property
    def label(self) -> str:
        """Label of the SNMP configuration."""
        return self.descriptor.label

    @label.setter
    def label(self, value: str):
        """Sets the label of the SNMP configuration."""
        self.descriptor.label = value

    @property
    def description(self) -> str:
        """Description of the SNMP configuration."""
        return self.descriptor.desc

    @description.setter
    def description(self, value: str):
        """Sets the description of the SNMP configuration."""
        self.descriptor.desc = value

    @property
    def version(self) -> Literal["SNMP v1", "SNMP v2c", "SNMP v3"]:
        """Preferred SNMP version."""
        version_map = {SnmpVersion.V1: "SNMP v1", SnmpVersion.V2C: "SNMP v2c", SnmpVersion.V3: "SNMP v3"}
        return cast(Literal["SNMP v1", "SNMP v2c", "SNMP v3"], version_map[self.protocol.preferredVersion])

    @version.setter
    def version(self, value: Literal["SNMP v1", "SNMP v2c", "SNMP v3"]):
        """Sets the preferred SNMP version."""
        version_map = {"SNMP v1": SnmpVersion.V1, "SNMP v2c": SnmpVersion.V2C, "SNMP v3": SnmpVersion.V3}
        if value not in version_map:
            raise ValueError(f"Invalid SNMP version: {value}")
        self.protocol.preferredVersion = version_map[value]

    @property
    def retries(self) -> int:
        """Retries"""
        return self.protocol.retries

    @retries.setter
    def retries(self, value: int):
        """Sets the number of retries for SNMP requests."""
        self.protocol.retries = value

    @property
    def timeout(self) -> int:
        """Timeout in milliseconds."""
        return self.protocol.timeout

    @timeout.setter
    def timeout(self, value: int):
        """Sets the timeout for SNMP requests in milliseconds."""
        self.protocol.timeout = value

    @property
    def local_engine_id(self) -> str:
        """Local Engine ID"""
        return self.protocol.localEngineId

    @local_engine_id.setter
    def local_engine_id(self, value: str):
        """Sets the local engine ID for SNMP."""
        self.protocol.localEngineId = value

    @property
    def use_get_bulk(self) -> bool:
        """Use GetBulk"""
        return self.protocol.useGetBulk

    @use_get_bulk.setter
    def use_get_bulk(self, value: bool):
        """Sets whether to use GetBulk for SNMP requests."""
        self.protocol.useGetBulk = value

    @property
    def max_repetitions(self) -> int:
        """Max Repetitions"""
        return self.protocol.maxRepetitions

    @max_repetitions.setter
    def max_repetitions(self, value: int):
        """Sets the maximum number of repetitions for SNMP requests."""
        self.protocol.maxRepetitions = value

    @property
    def read_community(self) -> str:
        """Read Community"""
        return self.security.read.community

    @read_community.setter
    def read_community(self, value: str):
        """Sets the read community for SNMP."""
        self.security.read.community = value

    @property
    def write_community(self) -> str:
        """Write Community"""
        return self.security.write.community

    @write_community.setter
    def write_community(self, value: str):
        """Sets the write community for SNMP."""
        self.security.write.community = value

    def list_usernames(self) -> list[str]:
        """Returns a list of usernames in the SNMP configuration."""
        return list(self.users.keys())

    def get_user_id_by_username(self, username: str) -> str:
        """Returns the user ID for a given username."""
        user_ids = [user_id for user_id, user in self.users.items() if user.name == username]
        if not user_ids:
            raise ValueError(f"No user found with username: {username}")
        if len(user_ids) > 1:
            raise ValueError(f"Multiple users found with username: {username}. Please specify a unique user.")
        return user_ids[0]

    def set_read_user_by_username(self, username: str):
        """Sets the read user by username."""
        user_id = self.get_user_id_by_username(username)
        self.security.read.user = user_id

    def set_write_user_by_username(self, username: str):
        """Sets the write user by username."""
        user_id = self.get_user_id_by_username(username)
        self.security.write.user = user_id
