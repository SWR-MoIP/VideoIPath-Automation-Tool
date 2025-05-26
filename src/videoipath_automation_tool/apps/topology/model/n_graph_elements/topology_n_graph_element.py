from typing import Literal, Optional

from pydantic import BaseModel, Field


class Descriptor(BaseModel, validate_assignment=True):
    desc: str
    label: str


class Gpid(BaseModel, validate_assignment=True):
    component: int
    pointId: list[str]


class MapsElement(BaseModel, validate_assignment=True):
    cType: Literal["Topology", "Geo"] = "Topology"
    id: str = ""
    name: str = ""
    visible: bool = True
    x: float = 0.0
    y: float = 0.0


# --- Literal Types ---
NGraphElementType = Literal[
    "ipVertex",
    "codecVertex",
    "genericVertex",
    "baseDevice",
    "unidirectionalEdge",
    "nGraphResourceTransform",  # Note: Not implemented yet
    "ipTransformVertex",  # Note: Not implemented yet
    "routerVertex",  # Note: Not implemented yet
]

VertexType = Literal["BiDirectional", "In", "Internal", "Out", "Undecided", "Internal"]

ConfigPriority = Literal["high", "low", "off"]

Control = Literal["full", "off", "semi"]

SipsMode = Literal["NONE", "SIPSAuto", "SIPSDuplicate", "SIPSMerge", "SIPSSplit"]

IconSize = Literal["auto", "large", "medium", "small"]

IconType = Literal[
    "default",
    "none",
    "device",
    "camera",
    "monitor",
    "encoder",
    "decoder",
    "audioMixer",
    "videoMixer",
    "processingDevice",
    "transportStreamProcessor",
    "mediaDevice",
    "server",
    "gateway",
    "ipSwitchRouter",
    "vlanCloud",
    "videoAudioRouterMatrix",
    "encoderDecoder",
]

SdpStrategy = Literal[
    "always",  # Continuous
    "once",  # Fetch and Confirm
    "video",  # Continuous Video, Confirm Others
]


class NGraphElement(BaseModel, validate_assignment=True):
    """
    Base class for all nGraphElements.

    Attributes:
        id (str): Unique identifier of the nGraphElement
        rev (Optional[str]): Revision of the nGraphElement
        vid (str): vid of the nGraphElement
        descriptor (Descriptor): User defined label and description of the nGraphElement
        fDescriptor (Descriptor): Factory label and description of the nGraphElement
        tags (list[str]): Tags associated with the nGraphElement
        type (NGraphElementType): Type of the nGraph (`baseDevice`, `ipVertex`, `codecVertex`, `genericVertex`, `unidirectionalEdge`, `nGraphResourceTransform`, `ipTransformVertex`, `routerVertex`)
    """

    id: str = Field(..., alias="_id")
    rev: Optional[str] = Field(..., alias="_rev")
    vid: str = Field(..., alias="_vid")
    descriptor: Descriptor
    fDescriptor: Descriptor
    tags: list[str] = Field(default_factory=list)
    type: NGraphElementType

    @property
    def label(self) -> str:
        """User defined label of the nGraphElement"""
        return self.descriptor.label

    @label.setter
    def label(self, value: str):
        """User defined label of the nGraphElement"""
        self.descriptor.label = value

    @property
    def description(self) -> str:
        """User defined description of the nGraphElement"""
        return self.descriptor.desc

    @description.setter
    def description(self, value: str):
        """User defined description of the nGraphElement"""
        self.descriptor.desc = value

    @property
    def factory_label(self) -> str:
        """Factory label of the nGraphElement"""
        return self.fDescriptor.label

    @property
    def factory_description(self) -> str:
        """Factory description of the nGraphElement"""
        return self.fDescriptor.desc

    def action(self, action: Literal["add", "replace", "remove"]) -> dict:
        """Method to create an API action for the nGraphElement.

        Args:
            action (Literal['add', 'replace', 'remove']): Type of action to be performed

        Returns:
            dict: Body of the API Request
        """
        rev = None if action == "add" else self.rev

        body = {"action": action, "clientId": "topologyManagerSpec", "key": self.id, "rev": rev, "skey": self.id}

        if action in ["add", "replace"]:
            body["value"] = self.model_dump(mode="json", exclude={"id", "rev", "vid"}, by_alias=True)

        return body
