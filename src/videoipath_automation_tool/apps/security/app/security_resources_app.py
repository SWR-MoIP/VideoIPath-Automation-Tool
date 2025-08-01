from logging import Logger
from typing import Optional

from videoipath_automation_tool.apps.security.model.domain_membership_model import LocalMemberships, ResourceType
from videoipath_automation_tool.apps.security.security_api import SecurityAPI
from videoipath_automation_tool.apps.security.security_exceptions import MembershipsNotFoundError
from videoipath_automation_tool.validators.device_id_including_virtual import validate_device_id_including_virtual


class SecurityResources:
    def __init__(self, security_api: SecurityAPI, logger: Logger):
        self._security_api = security_api
        self._logger = logger

    def get_device_memberships(self, device_id: str) -> LocalMemberships:
        """
        Returns memberships for the given device ID.
        Creates an empty membership object if none found.

        Note:
        This method does NOT verify whether the device actually exists in the system.
        Make sure to perform that check separately if required by your use case.

        Args:
            device_id (str): The ID of the device to retrieve memberships for.

        Returns:
            LocalMemberships: The LocalMemberships object containing the device's memberships.
        """
        validate_device_id_including_virtual(device_id)
        try:
            return self._security_api.get_memberships_by_type_and_id(ResourceType.DEVICE, device_id)
        except MembershipsNotFoundError:
            self._logger.info(
                f"No memberships found for device ID: {device_id}, creating new Memberships object (without domains)."
            )
            return LocalMemberships.model_validate(
                {
                    "_id": f"device:{device_id}",
                    "_vid": f"device:{device_id}",
                    "_rev": "",
                    "domains": [],
                }
            )
        except Exception as e:
            self._logger.error(f"Error retrieving memberships for device ID '{device_id}': {e}")
            raise

    def get_profile_memberships(self, profile_id: str) -> LocalMemberships:
        """
        Returns memberships for the given profile ID.
        Creates an empty membership object if none found.

        Note:
        This method does NOT verify whether the profile actually exists in the system.
        Make sure to perform that check separately if required by your use case.

        Args:
            profile_id (str): The ID of the profile to retrieve memberships for.

        Returns:
            LocalMemberships: The LocalMemberships object containing the profile's memberships.
        """
        try:
            return self._security_api.get_memberships_by_type_and_id(ResourceType.PROFILE, profile_id)
        except MembershipsNotFoundError:
            self._logger.info(
                f"No memberships found for profile ID: {profile_id}, creating new Memberships object (without domains)."
            )
            return LocalMemberships.model_validate(
                {
                    "_id": f"profile:{profile_id}",
                    "_vid": f"profile:{profile_id}",
                    "_rev": "",
                    "domains": [],
                }
            )
        except Exception as e:
            self._logger.error(f"Error retrieving memberships for profile ID '{profile_id}': {e}")
            raise

    def update_memberships(self, memberships: LocalMemberships) -> Optional[LocalMemberships]:
        """
        Updates the memberships for a resource.

        Args:
            memberships (LocalMemberships): The LocalMemberships object to update.

        Returns:
            Optional[LocalMemberships]: The updated LocalMemberships object, or None if all domains were removed.

        Raises:
            ValueError: If the membership ID or revision does not match the existing membership.
        """
        try:
            existing_membership = self._security_api.get_memberships_by_type_and_id(
                memberships.resource_type, memberships.resource_id
            )
        except MembershipsNotFoundError:
            existing_membership = None
            return self._security_api.add_memberships(memberships)

        if existing_membership is not None:
            if existing_membership.rev != memberships.rev:
                raise ValueError(
                    f"Membership with ID '{memberships.id}' has a different revision. "
                    f"Expected: {memberships.rev}, Found: {existing_membership.rev}"
                )
            if memberships.domains == []:
                # Empty Domains will result in VALIDATION_ERROR: "Cannot update to empty domain set. Remove the key instead."
                self._logger.info(
                    f"Membership for resource ID '{memberships.resource_id}' contains no domains. Removing membership via API instead of updating."
                )
                return self._security_api.remove_memberships(memberships)

            return self._security_api.update_memberships(memberships)

    def convert_domain_ids_to_names(self, domain_ids: list[str]) -> list[str]:
        """
        Converts a list of domain IDs to their corresponding names.

        Args:
            domain_ids (list[str]): A list of domain IDs to convert.

        Returns:
            list[str]: A list of domain names corresponding to the provided IDs.
        """
        domain_names = []
        if len(domain_ids) == 0:
            self._logger.warning("No domain IDs provided for conversion. Returning an empty list.")
            return domain_names
        elif len(domain_ids) == 1:
            self._logger.debug(
                f"Converting single domain ID '{domain_ids[0]}' to name by fetching this domain from the API."
            )
            domain = self._security_api.get_domain_by_id(domain_ids[0])
            if domain:
                return [domain.name]
            else:
                raise ValueError(f"Domain ID '{domain_ids[0]}' not found in the system, cannot convert to name.")
        elif len(domain_ids) > 1:
            self._logger.debug(
                f"Converting multiple domain IDs {domain_ids} to names by fetching all domains from the API."
            )
            all_domains = self._security_api.get_all_domains()
            domain_map = {domain.id: domain.name for domain in all_domains}
            for domain_id in domain_ids:
                if domain_id in domain_map:
                    domain_names.append(domain_map[domain_id])
                else:
                    raise ValueError(
                        f"Domain ID '{domain_id}' not found in the system, cannot convert all IDs to names."
                    )
            if len(set(domain_names)) != len(domain_names):
                self._logger.warning(
                    "Duplicate domain names found in the conversion result! This may indicate that multiple IDs map to the same name. Be cautious when using these names."
                )
            return domain_names
        else:
            return domain_names  # not nesessary during runtime, just to avoid IDE warnings

    def convert_domain_names_to_ids(self, domain_names: list[str]) -> list[str]:
        """
        Converts a list of domain names to their corresponding IDs.

        Args:
            domain_names (list[str]): A list of domain names to convert.

        Returns:
            list[str]: A list of domain IDs corresponding to the provided names.
        """
        domain_ids = []
        if len(domain_names) == 0:
            self._logger.warning("No domain names provided for conversion. Returning an empty list.")
            return domain_ids
        elif len(domain_names) == 1:
            self._logger.debug(
                f"Converting single domain name '{domain_names[0]}' to ID by fetching this domain from the API."
            )
            domain = self._security_api.get_domain_by_name(domain_names[0])
            if domain and domain.id:
                self._logger.debug(f"Domain name '{domain_names[0]}' converted to ID '{domain.id}'.")
                return [domain.id]
            else:
                raise ValueError(f"Domain name '{domain_names[0]}' not found in the system, cannot convert to ID.")
        elif len(domain_names) > 1:
            self._logger.debug(
                f"Converting multiple domain names {domain_names} to IDs by fetching all domains from the API."
            )
            all_domains = self._security_api.get_all_domains()

            seen = {}
            duplicates = {}
            for domain in all_domains:
                if domain.name in seen:
                    duplicates.setdefault(domain.name, {seen[domain.name]}).add(domain.id)
                else:
                    seen[domain.name] = domain.id

            relevant_duplicates = {name: ids for name, ids in duplicates.items() if name in domain_names}
            if relevant_duplicates:
                dup_str = ", ".join(f"'{name}': {sorted(ids)}" for name, ids in relevant_duplicates.items())
                raise ValueError(f"Duplicate domain names in input – cannot continue: {dup_str}")

            domain_map = {domain.name: domain.id for domain in all_domains}
            for domain_name in domain_names:
                if domain_name in domain_map:
                    domain_ids.append(domain_map[domain_name])
                else:
                    raise ValueError(
                        f"Domain name '{domain_name}' not found in the system, cannot convert all names to IDs."
                    )

            return domain_ids
        else:
            return domain_ids  # not nesessary during runtime, just to avoid IDE warnings

    def add_domain_by_name_to_membership_object(
        self, domain_name: str, membership: LocalMemberships
    ) -> LocalMemberships:
        """
        Adds a domain to a membership object by its name.

        Args:
            domain_name (str): The name of the domain to add.
            membership (LocalMemberships): The LocalMemberships object to which the domain will be added.

        Returns:
            LocalMemberships: The updated LocalMemberships object with the domain added.
        """
        domain = self._security_api.get_domain_by_name(domain_name)

        if not domain or not domain.id:
            raise ValueError(f"Domain with name '{domain_name}' not found.")

        if domain.id in membership.domains:
            self._logger.info(
                f"Domain '{domain_name}' is already in the membership for resource ID '{membership.resource_id}'. No changes made."
            )
            return membership

        membership.domains.append(domain.id)

        return membership

    def remove_domain_by_name_from_membership_object(
        self, domain_name: str, membership: LocalMemberships
    ) -> LocalMemberships:
        """
        Removes a domain from a membership object by its name.

        Args:
            domain_name (str): The name of the domain to remove.
            membership (LocalMemberships): The LocalMemberships object from which the domain will be removed.

        Returns:
            LocalMemberships: The updated LocalMemberships object with the domain removed.
        """
        domain = self._security_api.get_domain_by_name(domain_name)

        if not domain or not domain.id:
            raise ValueError(f"Domain with name '{domain_name}' not found.")

        if domain.id not in membership.domains:
            self._logger.info(
                f"Domain '{domain_name}' is not in the membership for resource ID '{membership.resource_id}'. No changes made."
            )
            return membership

        membership.domains.remove(domain.id)

        return membership
