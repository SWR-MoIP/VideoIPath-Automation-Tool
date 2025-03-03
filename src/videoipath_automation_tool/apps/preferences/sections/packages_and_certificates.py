import logging

from videoipath_automation_tool.apps.preferences.model.package_item import PackageItem
from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI


class PackagesAndCertificates:
    def __init__(self, preferences_api: PreferencesAPI, logger: logging.Logger):
        self._logger = logger
        self._preferences_api = preferences_api

    def get_all_packages(self) -> list[PackageItem]:
        """
        Get all packages from the VideoIPath System Preferences / Packages & Certificates.

        Returns:
            list[PackageItem]: List of all packages.
        """
        return self._preferences_api.get_all_packages()

    def get_backend(self) -> PackageItem:
        """
        Get the backend package from the VideoIPath System Preferences / Packages & Certificates.

        Returns:
            PackageItem: Backend package.
        """
        packages = self.get_all_packages()
        for package in packages:
            if package.package == "backend":
                return package
        raise ValueError("No backend package found in the VideoIPath System Preferences / Packages & Certificates.")

    def get_apps(self) -> PackageItem:
        """
        Get the apps package from the VideoIPath System Preferences / Packages & Certificates.

        Returns:
            PackageItem: Apps package.
        """
        packages = self.get_all_packages()
        for package in packages:
            if package.package == "apps":
                return package
        raise ValueError("No apps package found in the VideoIPath System Preferences / Packages & Certificates.")
