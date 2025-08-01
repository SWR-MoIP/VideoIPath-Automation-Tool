from enum import Enum

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    DEVICE = "device"
    PROFILE = "profile"
    # Types:
    # Device: "device:<device_id>"
    # Profile: "profile:<profile_id>"
    # Panel project: (not implemented yet)
    # Endpoint group (not implemented yet)
    # Junction (not implemented yet)
    # Macro (not implemented yet)
    # Manual service (not implemented yet)
    # Matrix (not implemented yet)


def parse_resource_type(id_str: str) -> ResourceType:
    try:
        return ResourceType(id_str.split(":")[0])
    except ValueError:
        raise ValueError(f"Invalid or malformed resource type in ID: {id_str}")


class LocalMemberships(BaseModel):
    id: None | str = Field(default=None, alias="_id")
    vid: None | str = Field(default=None, alias="_vid")
    rev: None | str = Field(default=None, alias="_rev")
    domains: list[str]

    # --- Getter ---
    @property
    def resource_type(self) -> ResourceType:
        if not self.id or ":" not in self.id:
            raise ValueError(f"Malformed ID: {self.id}")
        return parse_resource_type(self.id)

    @property
    def resource_id(self) -> str:
        # Returns the ID part of the resource, e.g., "device177" from "device:device177"
        if not self.id or ":" not in self.id:
            raise ValueError(f"Malformed ID: {self.id}")
        return self.id.split(":", 1)[1]
