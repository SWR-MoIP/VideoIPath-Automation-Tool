from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


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
class SnmpUser(BaseModel):
    level: SecurityLevel = SecurityLevel.NO_AUTH_NO_PRIV
    name: str = "New User"
    authProtocol: AuthProtocol = AuthProtocol.MD5
    privProtocol: PrivProtocol = PrivProtocol.DES
    engineId: str = ""
    privPassword: str = ""
    authPassword: str = ""


class SnmpDescriptor(BaseModel):
    label: str = ""
    desc: str = ""


class SnmpSecurityEntry(BaseModel):
    user: str = ""  # User ID from "Users" section. Must be a valid UUID of an existing user.
    community: str = ""  # Value from "Protocol Settings => SNMP v1/v2c Security => Write / Read community"


class SnmpSecurity(BaseModel):
    read: SnmpSecurityEntry = SnmpSecurityEntry(community="public")
    write: SnmpSecurityEntry = SnmpSecurityEntry(community="private")


class SnmpProtocolSettings(BaseModel):
    preferredVersion: SnmpVersion = SnmpVersion.V2C
    retries: int = 1
    maxRepetitions: int = 10
    useGetBulk: bool = True
    timeout: int = 5000
    localEngineId: str = ""


class SnmpConfiguration(BaseModel):
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

    # def dump_to_dict(self) -> dict:
    #     """
    #     Dumps the SnmpConfiguration instance to a dictionary.

    #     Returns:
    #         dict: A dictionary representation of the SnmpConfiguration instance.
    #     """
    #     config_id = self.id
    #     data = self.model_dump(mode="json", exclude={"id"})
    #     return {config_id: data}


# class SnmpConfig(BaseModel):
#     id: str
#     configuration: SnmpConfiguration = Field(default_factory=SnmpConfiguration)
