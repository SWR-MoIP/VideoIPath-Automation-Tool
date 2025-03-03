import logging
from typing import List

from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI


class License:
    def __init__(self, preferences_api: PreferencesAPI, logger: logging.Logger):
        self._logger = logger
        self._preferences_api = preferences_api

    def get_activation_code(self) -> str:
        """
        Get the main activation code from the VideoIPath System Preferences / License.

        Returns:
            str: Activation code.
        """

        return self._preferences_api.get_license_activation_code()

    def get_activation_codes(self) -> List[str]:
        """
        Get all activation codes from the VideoIPath System Preferences / License.

        Returns:
            List[str]: List of activation codes.
        """
        return self._preferences_api.get_license_activation_codes()

    def get_plan(self) -> str:
        """
        Get the license plan from the VideoIPath System Preferences / License.

        Returns:
            str: License plan.
        """
        return self._preferences_api.get_license_plan()

    def get_concurrent_users(self) -> int:
        """
        Get the number of concurrent users allowed from the VideoIPath System Preferences / License.

        Returns:
            int: Number of concurrent users.
        """
        return self._preferences_api.get_license_concurrent_users()

    def get_advanced_functionality(self) -> List[str]:
        """
        Get the licensed advanced functionality from the VideoIPath System Preferences / License.

        Returns:
            List[str]: Licensed advanced functionality.
        """
        advanced_functionality = self._preferences_api._fetch_license_advanced_functionality()
        capability_labels = self._preferences_api._fetch_advanced_functionality_capability_labels()
        return [capability_labels[functionality] for functionality in advanced_functionality]

    def get_services_summary(self) -> dict:
        """
        Get the summary of services (Used & Allowances) from the VideoIPath System Preferences / License.

        Returns:
            dict: Summary of services. Note: Keys may vary depending on the license plan.
        """
        services_used = {}

        num_connections_now = self._preferences_api._fetch_license_num_connections_now()
        services_used.update(num_connections_now)

        num_pages_now = self._preferences_api._fetch_license_num_pages_used()
        services_used["softwarePanel"] = num_pages_now

        num_tally_now = self._preferences_api._fetch_license_num_tally_used()
        services_used["tally"] = num_tally_now

        num_nmos_query_apis_now = self._preferences_api._fetch_license_num_nmos_query_apis_used()
        services_used["nmosRds"] = num_nmos_query_apis_now

        services_allowances = self._preferences_api._fetch_license_information()["capabilityNow"]["services"]

        for key in services_allowances:
            if key not in services_used:
                raise ValueError(f"Service '{key}' not found in services_used.")

        return {
            key: {"used": services_used[key], "allowances": services_allowances[key]} for key in services_allowances
        }

    def get_devices_summary(self) -> dict:
        """
        Get the summary of devices (Used & Allowances) from the VideoIPath System Preferences / License.

        Returns:
            dict: Summary of devices. Note: Keys may vary depending on the license plan.
        """
        num_devices_used = self._preferences_api._fetch_license_num_devices()
        num_devices_allowances = self._preferences_api._fetch_license_information()["capabilityNow"]["devices"]

        for key in num_devices_allowances:
            if key not in num_devices_used:
                raise ValueError(f"Device '{key}' not found in num_devices_used.")

        return {
            key: {"used": num_devices_used[key], "allowances": num_devices_allowances[key]}
            for key in num_devices_allowances
        }

    def get_licenses(self) -> List[dict]:
        """
        Get all licenses from the VideoIPath System Preferences / License.

        Returns:
            List[dict]: List of licenses.
        """
        data = self._preferences_api._fetch_license_information()
        return data["licenses"]["_items"]

    def upload_license(self, license_dict: dict) -> dict | None:
        """
        Upload a license file in dict format to the VideoIPath System Preferences / License.

        Args:
            license_dict (dict): License file as dictionary.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is already uploaded, returns None.
        """
        return self._preferences_api.upload_license(license_dict)

    def activate_license(self, license_signature: str) -> dict | None:
        """
        Activate a license in the VideoIPath System Preferences / License.

        Args:
            license_signature (str): Signature of the license.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is not found, returns None.
        """
        return self._preferences_api.activate_license(license_signature)

    def deactivate_license(self, license_signature: str) -> dict | None:
        """
        Deactivate a license in the VideoIPath System Preferences / License.

        Args:
            license_signature (str): Signature of the license.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is not found, returns None.
        """
        return self._preferences_api.deactivate_license(license_signature)
