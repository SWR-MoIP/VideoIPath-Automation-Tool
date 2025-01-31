import logging

from typing import List, Optional

from videoipath_automation_tool.apps.profile.model.profile_model import Profile, SuperProfile
from videoipath_automation_tool.apps.profile.profile_api import ProfileAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class ProfileApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """Profile App contains functionality to interact with VideoIPath Profile App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        if logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_profile_app"
            )  # create fallback logger if no logger is provided
        else:
            self.logger = logger

        # --- Setup Profile API ---
        try:
            self._profile_api = ProfileAPI(vip_connector=vip_connector, logger=self.logger)
            self.logger.debug("Profile API successfully initialized.")
        except Exception as e:
            self.logger.error(f"Error initializing Profile API: {e}")
            raise ConnectionError("Error initializing Profile API.")

    def get_profile_names(self) -> List[str] | None:
        """Get all VideoIPath Profile names.

        Returns:
            List[str] | None: List of Profile names or None if no Profiles are found.
        """
        return self._profile_api.get_profile_names()

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

        if data is None:
            return None
        elif isinstance(data, Profile):
            return data
        elif isinstance(data, list):
            return data

    def get_profiles(self) -> List[Profile] | List[None]:
        """Get all VideoIPath Profiles.

        Returns:
            List[Profile] | None: List of Profile objects or None if no Profiles are found.
        """
        data = self._profile_api.get_profiles()
        return data

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

    def remove_profile(self, name: Optional[str] = None, id: Optional[str] = None, profile: Optional[Profile] = None):
        """Remove a Profile from the VideoIPath System by its name, id or Profile object.

        Args:
            name (str): Name of the Profile to remove.
            id (str): ID of the Profile to remove.
            profile (Profile): Profile object to remove.

        Returns:
            bool: True if the Profile was removed successfully, False otherwise.
        """
        if sum([1 for x in [name, id, profile] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either name, ID or Profile object.")
        if name:
            profile = self.get_profile(name=name)
        elif id:
            profile = self.get_profile(id=id)
        else:
            raise ValueError("No name, ID or Profile provided.")

        if profile is None:
            raise ValueError("Profile not found.")

        if type(profile) is list:
            self.logger.info("Multiple Profiles found, removing all Profiles.")
            profile_list = profile
        else:
            profile_list = [profile]

        response = self._profile_api.remove_profile(profile_list)

        return response

    # def update_profile(self, profile: Profile) -> Profile:
