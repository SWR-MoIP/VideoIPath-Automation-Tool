from pydantic import BaseModel, Field


class RequestRpcHeader(BaseModel):
    """Request RPC Header Model."""

    id: int = Field(default=10)


class RequestRpcData(BaseModel):
    """Request RPC Data Model."""

    add: dict = Field(default_factory=dict)
    update: dict = Field(default_factory=dict)
    remove: list = Field(default_factory=list)


class RequestRPC(BaseModel):
    """Request RPC Model."""

    header: RequestRpcHeader = Field(default_factory=RequestRpcHeader)
    data: str | RequestRpcData = Field(default_factory=RequestRpcData)

    def add(self, id: str, model: BaseModel) -> "RequestRPC":
        """Method to add a new Config to VideoIPath

        Args:
            id (str): Id of the Config
            model (BaseModel): Config Model
        """
        self.data.add[id] = model.model_dump(mode="json", by_alias=True)
        return self

    def update(self, id: str, model: BaseModel) -> "RequestRPC":
        """Method to update a Config in VideoIPath

        Args:
            id (str): Id of the Config
            model (BaseModel): Config Model
        """
        self.data.update[id] = model.model_dump(mode="json", by_alias=True)
        return self

    def remove(self, id: str | list[str]) -> "RequestRPC":
        """Method to remove a Config from VideoIPath

        Args:
            id (str | list[str]): Id or List of Ids of the Config
        """
        if isinstance(id, str):
            id = [id]
        self.data.remove = id
        return self
