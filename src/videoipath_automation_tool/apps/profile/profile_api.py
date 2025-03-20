import logging
import urllib.parse
from typing import List, Literal, Optional

from deepdiff.diff import DeepDiff

from videoipath_automation_tool.apps.preferences.model import *
from videoipath_automation_tool.apps.profile.model.profile_model import Profile, SuperProfile
from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class ProfileAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """
        Class for VideoIPath Profile API.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger]): Logger instance. If `None`, a fallback logger is used.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_profile_api")
        self.vip_connector = vip_connector

        self._logger.debug("Profile API logger initialized.")

    def _generate_profile_action_request_body(
        self, add_list: List[SuperProfile | Profile], update_list: List[Profile], remove_list: List[Profile]
    ):
        """
        Generate a RequestV2Patch object for Profile actions (add, update, remove).
        """
        body = RequestV2Patch()

        for element in add_list:
            body.add(element)

        for element in update_list:
            body.update(element)

        for element in remove_list:
            body.remove(element)

        return body

    def _validate_response(self, response: ResponseV2Get) -> list[dict]:
        """
        Additional validation for the response data.

        Args:
            response (ResponseV2Get): Response object to validate.

        Returns:
            list[dict]: List of Profile data dictionaries.
        """
        if not response.header.ok:
            raise ValueError(f"Response not OK: {response.header}")
        if response.data:
            if "_items" not in response.data["config"]["pathman"]["profiles"].keys():
                raise ValueError("No _items key in response data.")
            return response.data["config"]["pathman"]["profiles"]["_items"]
        else:
            raise ValueError("No data in response.")

    def get_profiles_name_id_rev(self) -> Optional[List[dict]]:
        """
        Get all VideoIPath Profile names, IDs and revision numbers.

        Returns:
            Optional[List[dict]]: List of Profile data dictionaries if successful, None otherwise.

        """
        self._logger.debug("Requesting all Profile names, IDs and revision numbers")
        response = self.vip_connector.rest.get("/rest/v2/data/config/pathman/profiles/*/name,_id,_rev")
        data = self._validate_response(response)
        return data if data else None

    def get_profiles(self) -> List[Profile] | None:
        """
        Get all VideoIPath Profile configurations.

        Returns:
            List[Profile] | None: List of Profile objects if successful, None otherwise.
        """
        self._logger.debug("Requesting all Profiles")

        response = self.vip_connector.rest.get("/rest/v2/data/config/pathman/profiles/**")
        data = self._validate_response(response)

        if len(data) == 0:
            self._logger.warning("No Profiles found. Returning None.")
            return None
        else:
            return [Profile.model_validate(item) for item in data]

    def get_profile_by_name(self, name: str) -> Profile | List[Profile] | None:
        """
        Get a VideoIPath Profile by its name.
        If multiple Profiles are found with the same name, a list of Profiles is returned.

        Args:
            name (str): Name of the Profile to get.

        Returns:
            Profile | List[Profile] | None: Profile object or list of Profile objects if successful, None otherwise.
        """
        self._logger.debug(f"Requesting Profile/s with name '{name}'")

        response = self.vip_connector.rest.get(f"/rest/v2/data/config/pathman/profiles/* where name='{name}'/**")
        data = self._validate_response(response)

        if len(data) == 0:
            self._logger.warning(f"No Profile found with name '{name}'.")
            return None
        elif len(data) == 1:
            self._logger.debug(f"Profile found with name '{name}'. Returning Profile.")
            return Profile(**data[0])
        elif len(data) > 1:
            self._logger.warning(f"Multiple Profiles found with name '{name}'. Returning list of Profiles.")
            return [Profile.model_validate(item) for item in data]

    def get_profile_by_id(self, profile_id: str) -> Profile | None:
        """
        Get a VideoIPath Profile by its ID.

        Args:
            profile_id (str): ID of the Profile to get.

        Returns:
            Profile | None: Profile object if successful, None otherwise.
        """
        self._logger.debug(f"Requesting Profile with id '{profile_id}'")

        response = self.vip_connector.rest.get(f"/rest/v2/data/config/pathman/profiles/* where _id='{profile_id}' /**")
        data = self._validate_response(response)

        if len(data) == 0:
            self._logger.warning(f"No Profile found with ID '{profile_id}'.")
            return None
        elif len(data) == 1:
            self._logger.debug(f"Profile found with ID '{profile_id}'. Returning Profile.")
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
        body = self._generate_profile_action_request_body(add_list=[super_profile], update_list=[], remove_list=[])

        response = self.vip_connector.rest.patch("/rest/v2/data/config/pathman/profiles", body)

        # Check if response is OK and if the Profile was added, then fetch the Profile by ID and return it
        if response.header.ok and response.result:
            if response.result.items[0].id:
                return_value = self.get_profile_by_id(response.result.items[0].id)
                if not return_value:
                    raise ValueError("Profile not found after adding.")
                else:
                    self._logger.debug(f"Profile '{return_value.name}' added successfully with ID '{return_value.id}'.")

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

        body = self._generate_profile_action_request_body([], [profile], [])

        response = self.vip_connector.rest.patch("/rest/v2/data/config/pathman/profiles", body)

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
            body = self._generate_profile_action_request_body([], [], [profile])
        elif isinstance(profile, list):
            for item in profile:
                if not isinstance(item, Profile):
                    raise ValueError(
                        "Invalid Profile object provided. Please provide a Profile or list of Profile objects."
                    )
            body = self._generate_profile_action_request_body([], [], profile)
        else:
            raise ValueError("Invalid Profile object provided. Please provide a Profile or list of Profile objects.")

        response = self.vip_connector.rest.patch("/rest/v2/data/config/pathman/profiles", body)
        return response

    def get_all_profile_tags(self, mode: Literal["all", "exclude_hidden", "hidden_only"] = "all") -> List[str]:
        """
        Get a list of all Profile tags. Optionally filtered by hidden status.

        Args:
            mode (Literal["all", "exclude_hidden", "hidden_only"], optional): Mode to get the tags. Defaults to "all".

        Returns:
            List[str]: List of Profile tags.
        """

        if mode == "all":
            response = self.vip_connector.rest.get("/rest/v2/data/config/profiles/*/tags/**")
        else:
            hidden = "true" if mode == "hidden_only" else "false"
            response = self.vip_connector.rest.get(f"/rest/v2/data/config/profiles/* where hidden={hidden} /tags/**")

        tags = []
        data = response.data["config"]["profiles"]["_items"]
        if data:
            for item in data:
                tags.extend(item["tags"])

        return tags

    def analyze_profile_configuration_changes_local(self, reference_profile: Profile, staged_profile: Profile):
        """
        Analyze the configuration changes between two Profiles.

        Args:
            reference_profile (Profile): Reference Profile.
            staged_profile (Profile): Staged Profile.
        """
        diff = DeepDiff(
            reference_profile.model_dump(mode="json"), staged_profile.model_dump(mode="json"), ignore_order=True
        )
        return diff

    def analyze_profile_configuration_changes(self, staged_profile: Profile):
        """
        Analyze the configuration changes between a Profile and the VideoIPath System.

        Args:
            staged_profile (Profile): Staged Profile.
        """
        profile_id = staged_profile.id
        if not profile_id:
            raise ValueError("Profile ID not found in Profile object.")
        reference_profile = self.get_profile_by_id(profile_id)
        if type(reference_profile) is not Profile:
            return None
        return self.analyze_profile_configuration_changes_local(reference_profile, staged_profile)

    def get_services_using_profile(self, profile_id: str) -> Optional[List[str] | str]:
        """
        Get a list of all Services using a Profile.

        Args:
            profile_id (str): ID of the Profile.

        Returns:
            Optional[List[str] | str]: List of Service IDs if successful, None otherwise.
        """
        response = self.vip_connector.rest.get(
            "/rest/v2/data/status/conman/services/*/connection/profileIds,generic/**"
        )
        service_ids = []
        for service in response.data["status"]["conman"]["services"]["_items"]:
            if profile_id in service["connection"]["profileIds"] and service["connection"]["generic"]["state"] == 1:
                service_ids.append(service["_id"])

        if len(service_ids) == 0:
            return None
        if len(service_ids) == 1:
            return service_ids[0]
        else:
            return service_ids

    def get_usage_count(self, profile_id: str, mode: Literal["build_in", "enhanced"] = "build_in") -> int:
        """
        Get the number of Services using a Profile.

        Args:
            profile_id (str): ID of the Profile.
            mode (Literal["build_in", "enhanced"], optional): The mode for calculating the usage count.
                - "build_in" (default): Uses built-in GUI data to retrieve the usage count.
                - "enhanced": Uses the API for a more accurate count based on service data.

        Returns:
            int: Number of Services using the Profile.

        Raises:
            ValueError: If the usage count is not found in the response data or an invalid mode is provided.
        """
        if mode == "build_in":
            escaped_profile_id = urllib.parse.quote(profile_id)
            response = self.vip_connector.rest.get(
                f"/rest/v2/data/status/pathman/profiles/* where _id='{escaped_profile_id}'/usageCount"
            )
            if response.data:
                return response.data["status"]["pathman"]["profiles"]["_items"][0]["usageCount"]
            else:
                raise ValueError("Usage count not found in response data.")
        elif mode == "enhanced":
            service_ids = self.get_services_using_profile(profile_id)
            if not service_ids:
                return 0
            if type(service_ids) is list:
                return len(service_ids)
            else:
                return 1
        else:
            raise ValueError("Invalid mode provided. Please provide 'build_in' or 'enhanced'.")
