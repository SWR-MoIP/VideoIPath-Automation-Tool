from pydantic import BaseModel, Field


class DomainDesc(BaseModel):
    desc: str = ""
    label: str = ""


class Domain(BaseModel):
    id: None | str = Field(default=None, alias="_id")
    vid: None | str = Field(default=None, alias="_vid")
    rev: None | str = Field(default=None, alias="_rev")
    desc: DomainDesc = Field(default_factory=DomainDesc)

    # --- Setter / Getter ---
    @property
    def name(self) -> str:
        """Returns the domain name."""
        return self.desc.label

    @name.setter
    def name(self, value: str):
        """Sets the domain name."""
        self.desc.label = value

    @property
    def description(self) -> str:
        """Returns the domain description."""
        return self.desc.desc

    @description.setter
    def description(self, value: str):
        """Sets the domain description."""
        self.desc.desc = value
