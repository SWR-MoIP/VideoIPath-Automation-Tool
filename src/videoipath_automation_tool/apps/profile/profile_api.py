import logging
from pydantic import BaseModel, model_validator
from typing import List, Optional

from videoipath_automation_tool.apps.preferences.model import *

from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector

from videoipath_automation_tool.apps.profile.model.profile_model import Profile, SuperProfile


class ProfileAPI(BaseModel):
    """
    Class for VideoIPath Profile API.

    """

    vip_connector: VideoIPathConnector
    model_config: dict = {"arbitrary_types_allowed": True}
    logger: Optional[logging.Logger] = None

    @model_validator(mode="after")
    def initialize_connector(self):
        if self.logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_profile_api"
            )  # use fallback logger if no logger is provided
            self.logger.debug(
                "No logger for connector provided. Using fallback logger: 'videoipath_automation_tool_profile_api'."
            )
        self.logger.debug("Profile API logger initialized.")
        return self

    def _generate_profile_action(
        self, add_list: List[SuperProfile | Profile], update_list: List[Profile], remove_list: List[Profile]
    ):
        body = RequestV2Patch()

        for element in add_list:
            body.add(element)

        for element in update_list:
            body.update(element)

        for element in remove_list:
            body.remove(element)

        return body

    def _validate_response(self, response: ResponseV2Get) -> dict:
        if not response.header.ok:
            raise ValueError(f"Response not OK: {response.header}")
        if response.data:
            if "config" not in response.data.keys():
                raise ValueError("No config key in response data.")
            if "pathman" not in response.data["config"].keys():
                raise ValueError("No pathman key in response data.")
            if "profiles" not in response.data["config"]["pathman"].keys():
                raise ValueError("No profiles key in response data.")
            if "_items" not in response.data["config"]["pathman"]["profiles"].keys():
                raise ValueError("No _items key in response data.")
            return response.data["config"]["pathman"]["profiles"]["_items"]
        else:
            raise ValueError("No data in response.")

    def get_profile_names(self) -> List[str] | None:
        """
        Get all VideoIPath Profile names.
        """
        response = self.vip_connector.http_get_v2("/rest/v2/data/config/pathman/profiles/*/name")
        data = self._validate_response(response)
        return [item["name"] for item in data] if data else None

    def get_profiles(self) -> List[Profile] | List[None]:
        """
        Get all VideoIPath Profiles.
        """
        response = self.vip_connector.http_get_v2("/rest/v2/data/config/pathman/profiles/**")
        data = self._validate_response(response)

        if len(data) == 0:
            return []
        else:
            return [Profile(**item) for item in data]

    def get_profile_by_name(self, name: str) -> Profile | List[Profile] | None:
        """
        Get a VideoIPath Profile by its name.
        """
        self.logger.debug(f"Requesting Profile/s with name '{name}'")

        response = self.vip_connector.http_get_v2(f"/rest/v2/data/config/pathman/profiles/* where name='{name}'/**")
        data = self._validate_response(response)

        if len(data) == 0:
            self.logger.warning(f"No Profile found with name '{name}'.")
            return None
        elif len(data) == 1:
            self.logger.debug(f"Profile found with name '{name}'. Returning Profile.")
            return Profile(**data[0])
        elif len(data) > 1:
            self.logger.warning(f"Multiple Profiles found with name '{name}'. Returning list of Profiles.")
            return [Profile(**item) for item in data]

    def get_profile_by_id(self, profile_id: str) -> Profile | None:
        """
        Get a VideoIPath Profile by its ID.
        """
        self.logger.debug(f"Requesting Profile with id '{profile_id}'")

        response = self.vip_connector.http_get_v2(
            f"/rest/v2/data/config/pathman/profiles/* where _id='{profile_id}' /**"
        )
        data = self._validate_response(response)

        if len(data) == 0:
            self.logger.warning(f"No Profile found with ID '{profile_id}'.")
            return None
        elif len(data) == 1:
            self.logger.debug(f"Profile found with ID '{profile_id}'. Returning Profile.")
            return Profile(**data[0])
        elif len(data) > 1:
            raise ValueError(f"Multiple Profiles found with ID '{profile_id}'.")

    def add_profile(self, super_profile: SuperProfile | Profile) -> Profile | None:
        """Add a Profile to the VideoIPath System.

        Args:
            profile (SuperProfile | Profile): SuperProfile object to add.

        Returns:
            Profile | None: Profile object if successful, None otherwise.
        """
        body = self._generate_profile_action([super_profile], [], [])

        response = self.vip_connector.http_patch_v2("/rest/v2/data/config/pathman/profiles", body)

        # Check if response is OK and if the Profile was added, then fetch the Profile by ID and return it
        if response.header.ok and response.result:
            if response.result.items[0].id:
                return_value = self.get_profile_by_id(response.result.items[0].id)

        if return_value and type(return_value) is Profile:
            return return_value
        else:
            return None

    def update_profile(self, profile: Profile) -> Profile | None:
        """Update a Profile in the VideoIPath System.

        Args:
            profile (Profile): Profile object to update.

        Returns:
            Profile | None: Profile object if successful, None otherwise.
        """

        # if type(profile) != Profile:
        #     raise ValueError("Invalid Profile object provided. Please provide a Profile object.")
        #     # body = {'actions': [{'_action': 'update', '_id': profile.id, '_rev': profile.rev , **profile.superProfile.model_dump(mode="json")}]}

        body = self._generate_profile_action([], [profile], [])

        response = self.vip_connector.http_patch_v2("/rest/v2/data/config/pathman/profiles", body)

        # Check if response is OK and if the Profile was updated, then fetch the Profile by ID and return it
        if response.header.ok and response.result:
            print(response.result.items[0].id)
            if response.result.items[0].id:
                return_value = self.get_profile_by_id(response.result.items[0].id)

        if return_value and type(return_value) is Profile:
            return return_value
        else:
            return None

    def remove_profile(self, profile: Profile | List[Profile]):
        """Remove a Profile from the VideoIPath System.

        Args:
            profile (Profile | List[Profile]): Profile object or list of Profile objects to remove.

        Returns:
            bool: True if successful, False otherwise.
        """
        if isinstance(profile, Profile):
            body = self._generate_profile_action([], [], [profile])
        elif isinstance(profile, list):
            for item in profile:
                if not isinstance(item, Profile):
                    raise ValueError(
                        "Invalid Profile object provided. Please provide a Profile or list of Profile objects."
                    )
            body = self._generate_profile_action([], [], profile)
        else:
            raise ValueError("Invalid Profile object provided. Please provide a Profile or list of Profile objects.")

        response = self.vip_connector.http_patch_v2("/rest/v2/data/config/pathman/profiles", body)
        return response
