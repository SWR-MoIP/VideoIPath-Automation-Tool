import logging
from typing import List, Optional

from videoipath_automation_tool.apps.profile.model.profile_model import Profile, SuperProfile
from videoipath_automation_tool.apps.profile.profile_api import ProfileAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger, generate_uuid_4


class ProfileApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """Profile App contains functionality to interact with VideoIPath Profile App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_profile_app")
        self.vip_connector = vip_connector

        # --- Setup Profile API ---
        self._profile_api = ProfileAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Profile APP initialized.")

    def list_profile_names(self) -> Optional[List[str]]:
        """Get all VideoIPath Profile names.

        Returns:
            Optional[List[str]]: List of Profile names or None if no Profiles are found. Note: Profile must not have a name, in this case the name is an empty string.
        """
        data = self._profile_api.get_profiles_name_id_rev()
        return [item.get("name", "") for item in data] if data else None

    def get_profile_ids_names(self) -> Optional[dict[str, str]]:
        """
        Get all VideoIPath Profile IDs with corresponding names.

        Returns:
            Optional[dict[str, str]]: Dictionary with Profile IDs as keys and Profile names as values or None if no Profiles are found. Note: Profile must not have a name, in this case the name is an empty string.
        """
        data = self._profile_api.get_profiles_name_id_rev()
        return {item["_id"]: item.get("name", "") for item in data} if data else None

    def get_profile(self, name: Optional[str] = None, id: Optional[str] = None) -> Profile | List[Profile] | None:
        """Get a VideoIPath Profile by its name or ID.

        Args:
            name (str): Name of the Profile to get.
            id (str): ID of the Profile to get.

        Returns:
            Profile | List[Profile] | None: Profile object if a single Profile is found, List of Profile objects if multiple Profiles are found, None if no Profile is found.
        """
        if name is None and id is None:
            raise ValueError("No name or ID provided.")
        if sum([1 for x in [name, id] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either name or ID.")

        if name:
            data = self._profile_api.get_profile_by_name(name)
        elif id:
            data = self._profile_api.get_profile_by_id(id)

        if data is None or data == [] or data == [None]:
            return None
        elif isinstance(data, Profile):
            return data
        elif isinstance(data, list):
            return data

    def get_profile_by_id(self, id: str) -> Optional[Profile]:
        """Get a VideoIPath Profile by its ID.

        Args:
            id (str): ID of the Profile to get.

        Returns:
            Profile | None: Profile object if a Profile is found, None if no Profile is found.
        """
        return self._profile_api.get_profile_by_id(id)

    def get_profile_by_name(self, name: str) -> Optional[Profile | List[Profile]]:
        """Get a VideoIPath Profile by its name.

        Args:
            name (str): Name of the Profile to get.

        Returns:
            Profile | None: Profile object if a Profile is found, None if no Profile is found.
        """
        return self._profile_api.get_profile_by_name(name)

    def get_profiles(self) -> Optional[List[Profile]]:
        """Get all VideoIPath Profiles.

        Returns:
            List[Profile] | None: List of Profile objects or None if no Profiles are found.
        """
        return self._profile_api.get_profiles()

    def add_profile(self, profile: SuperProfile | Profile) -> Profile:
        """Add a Profile to the VideoIPath System.

        Args:
            profile (Profile): Profile object to add.

        Returns:
            Profile | None: Profile object if successful, None otherwise.
        """
        try:
            data = self._profile_api.add_profile(super_profile=profile)
            if data:
                return data
            else:
                raise ValueError("Error adding Profile. Empty response.")
        except Exception as e:
            raise ValueError(f"Error adding Profile: {e}")

    def remove_profile(
        self, name: Optional[str] = None, id: Optional[str] = None, profile: Optional[Profile | List[Profile]] = None
    ):
        """Remove a Profile from the VideoIPath System by its name, id or Profile object.

        Args:
            name (str): Name of the Profile to remove.
            id (str): ID of the Profile to remove.
            profile (Profile | List[Profile]): Profile object/s to remove.

        Returns:
            bool: True if the Profile was removed successfully, False otherwise.
        """
        if sum([1 for x in [name, id, profile] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either name, ID or Profile object.")
        if name:
            profile_fetched = self.get_profile(name=name)
        elif id:
            profile_fetched = self.get_profile(id=id)
        elif not (name or id or profile):
            raise ValueError("No name, ID or Profile provided.")

        if profile:
            profile_to_remove = profile
        elif profile_fetched:
            profile_to_remove = profile_fetched
        else:
            raise ValueError("Profile not found.")

        profile_list = []

        if type(profile_to_remove) is List[Profile]:
            self._logger.info("Multiple Profiles found, removing multiple Profiles.")
            profile_list.extend(profile_to_remove)
        else:
            profile_list.append(profile_to_remove)

        if profile_list == [] or profile_list == [None]:
            raise ValueError("No Profiles found to remove.")
        response = self._profile_api.remove_profile(profile=profile_list)

        return response

    def update_profile(self, profile: Profile) -> Profile:
        """Update a Profile in the VideoIPath System.

        Args:
            profile (Profile): Profile object to update.

        Returns:
            Profile | None: Profile object if successful, None otherwise.
        """
        try:
            data = self._profile_api.update_profile(profile)
            if data:
                return data
            else:
                raise ValueError("Error updating Profile. Empty response.")
        except Exception as e:
            raise ValueError(f"Error updating Profile: {e}")

    def create_profile(self, name: str) -> Profile:
        """Create a new Profile-Object.
        Profile can be added to the VideoIPath System using the add_profile() method.

        Args:
            name (str): Name of the Profile.
        """
        return Profile.create(name)

    def clone_profile(self, profile: Profile) -> Profile:
        """Clone an existing Profile-Object in Style of the VideoIPath GUI.
        Cloned Profile can be added to the VideoIPath System using the add_profile() method.

        Args:
            profile (Profile): Profile object to clone.
        """
        cloned_profile = profile.model_copy()
        cloned_profile.id = generate_uuid_4()
        cloned_profile.vid = f"_: {cloned_profile.id}"
        cloned_profile.name += " (clone)"
        return cloned_profile
