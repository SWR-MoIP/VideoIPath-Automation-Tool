from pydantic import BaseModel, Field


class LocalMemberships(BaseModel):
    id: None | str = Field(default=None, alias="_id")
    vid: None | str = Field(default=None, alias="_vid")
    rev: None | str = Field(default=None, alias="_rev")
    domains: list[str]

    # --- Getter ---
    @property
    def resource_type(self) -> str:
        # Types:
        # Device: "device:<device_id>"
        # Profile: "profile:<profile_id>"
        # Panel project: (not implemented yet)
        # Endpoint group (not implemented yet)
        # Junction (not implemented yet)
        # Macro (not implemented yet)
        # Manual service (not implemented yet)
        # Matrix (not implemented yet)
        return self.id.split(":")[0] if self.id else ""
