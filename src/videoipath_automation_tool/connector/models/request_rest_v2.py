from typing import Literal

from pydantic import BaseModel, Field


# --- HTTP REST V2 Patch Request ---
class Action(BaseModel, extra="allow"):
    """
    Basemodel for REST V2 Patch Action.

    This model represents the basic structure of an action in a patch request.
    Config attributes will be added dynamically, therefore the extra="allow" parameter is set.

    Attributes:
        action (Literal["add", "update", "remove"]):
            The type of action to be performed. Possible values are "add", "update", or "remove".
    """

    action: Literal["add", "update", "remove"] = Field(..., alias="_action")


class RequestV2Patch(BaseModel):
    """
    Model for REST V2 Patch Request Body.

    This model is designed to handle patch requests in REST V2 API, which are used
    to modify resources in the VideoIPath system. It supports a list of actions
    (add, update, remove) to modify resources, such as nGraphElements or Profiles.
    The behavior of the patch request can be controlled using the `mode` attribute.

    Attributes:
        actions (list[Action]):
            A list of actions to be performed. Each action represents either
            an "add", "update", or "remove" operation on a resource.

        mode (Literal["strict", "relaxed"]):
            Defines the behavior for update and remove actions:
            - "strict" (default): Ensures revision-checks are performed before updating
              or removing resources.
            - "relaxed": Skips revision-checks for updates and removals.

            Attention: Mode "restore" is not implemented due to the high risk of
            unintended data loss.
    """

    actions: list[Action] = Field(default_factory=list)
    mode: Literal["strict", "relaxed"] = (
        "strict"  # Attention: Mode "restore" not implemented, because of the danger of data loss!
    )

    # Background Information (Source: /rest/v2/data/status/system/enums/rest/updateMode/**)
    # "updateMode" : {
    #   "relaxed" : {
    #     "desc" : {
    #       "desc" : "The update request is processed relaxed. No revisions are checked; update and add actions are treated similarly.",
    #       "label" : "Relaxed"
    #     },
    #     "label" : "relaxed",
    #     "value" : 1
    #   },
    #   "restore" : {
    #     "desc" : {
    #       "desc" : "The update request is treated as a complete configuration dump to be restored. Remove requests are ignored, and only update and add actions with id specified are handled. Existing keys in the target collection that is NOT present in the request will be deleted.",
    #       "label" : "Restore"
    #     },
    #     "label" : "restore",
    #     "value" : 2
    #   },
    #   "strict" : {
    #     "desc" : {
    #       "desc" : "The update request is processed strictly. Exact revision matches are required.",
    #       "label" : "Strict"
    #     },
    #     "label" : "strict",
    #     "value" : 0
    #   }

    def add(self, model: BaseModel) -> "RequestV2Patch":
        """Method to add a "add" Action to RequestRestV2-Object

        Args:
            model (BaseModel): Model to add
        """
        self.actions.append(Action(_action="add", **model.model_dump(mode="json", by_alias=True)))
        return self

    def update(self, model: BaseModel) -> "RequestV2Patch":
        """Method to add a "update" Action to RequestRestV2-Object

        Args:
            model (BaseModel): Model to update
        """
        self.actions.append(Action(_action="update", **model.model_dump(mode="json", by_alias=True)))
        return self

    def remove(self, model: BaseModel) -> "RequestV2Patch":
        """Method to add a "remove" Action to RequestRestV2-Object

        Args:
            model (BaseModel): Model to remove
        """  # only include id & rev in dump
        action = Action(_action="remove", **model.model_dump(mode="json", include={"rev", "id"}, by_alias=True))
        self.actions.append(action)
        return self


# --- HTTP REST V2 Post Request ---
class Header(BaseModel):
    """
    Basemodel for REST V2 Post Header.

    This model represents the header of a REST V2 Post request.

    Attributes:
        id (int):
            ID, defaults to 0.
    """

    id: int = 0


class RequestV2Post(BaseModel):
    """
    Model for REST V2 Post Request Body.

    This model is designed to handle post requests in REST V2 API, which are used
    to execute the newer generation of remote procedure calls in the VideoIPath system.

    Attributes:
        header (Header):
            The header of the request, containing the ID.

        data (dict):
            The data to be sent in the request.
    """

    header: Header = Header()
    data: dict = Field(default_factory=dict)
