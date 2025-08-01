import logging
from typing import List, Optional

from videoipath_automation_tool.apps.security.model.domain_membership_model import LocalMemberships, ResourceType
from videoipath_automation_tool.apps.security.model.domain_model import Domain
from videoipath_automation_tool.apps.security.security_exceptions import (
    DomainAlreadyExistsError,
    DomainNotFoundError,
    DomainRemoveError,
    MembershipAlreadyExistsError,
    MembershipsNotFoundError,
    MultipleDomainsFoundError,
    MultipleMembershipsFoundError,
)
from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class SecurityAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """
        Class for VideoIPath Security-App API.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger]): Logger instance. If `None`, a fallback logger is used.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_security_api")
        self.vip_connector = vip_connector

        self._logger.debug("Security-App API initialized.")

    # --- Domain CRUD ---

    def get_all_domains(self) -> List[Domain]:
        """
        Fetch all domains from the VideoIPath Security-App.

        Returns:
            List[Domain]: List of Domain objects.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/config/domainman/domains/**")
        if response.data and isinstance(response.data["config"]["domainman"]["domains"]["_items"], list):
            domains = response.data["config"]["domainman"]["domains"]["_items"]
            return [Domain.model_validate(domain) for domain in domains]
        else:
            raise ValueError("Response data is empty or malformed.")

    def _build_domain_id_name_mapping(self, domains: List[Domain]) -> dict[str, str]:
        """
        Build a mapping of domain IDs to names for quick lookup.

        Args:
            domains (List[Domain]): List of Domain objects.

        Returns:
            dict: Mapping of domain IDs to names.
        """
        return {domain.id: domain.name for domain in domains if domain.id and domain.name}

    def _build_domain_name_id_mapping(self, domains: List[Domain]) -> dict[str, str]:
        """
        Build a mapping of domain names to IDs for quick lookup.

        Args:
            domains (List[Domain]): List of Domain objects.

        Returns:
            dict: Mapping of domain names to IDs.
        """
        return {domain.name: domain.id for domain in domains if domain.id and domain.name}

    def get_domain_by_id(self, domain_id: str) -> Domain:
        """
        Fetch a specific domain by its ID.

        Args:
            domain_id (str): The ID of the domain to fetch.

        Returns:
            Domain: The Domain object corresponding to the given ID.
        """
        response = self.vip_connector.rest.get(
            f"/rest/v2/data/config/domainman/domains/* where _id = '{domain_id}' /**"
        )

        domains = (
            response.data.get("config", {}).get("domainman", {}).get("domains", {}).get("_items")
            if response.data
            else None
        )

        if domains and isinstance(domains, list):
            return self._validate_filtered_response(response.data, "id", domain_id)
        else:
            raise DomainNotFoundError(f"Domain with ID '{domain_id}' not found or malformed response.")

    def get_domain_by_name(self, domain_name: str) -> Domain:
        """
        Fetch a specific domain by its name.

        Args:
            domain_name (str): The name of the domain to fetch.

        Returns:
            Domain: The Domain object corresponding to the given name.
        """
        response = self.vip_connector.rest.get(
            f"/rest/v2/data/config/domainman/domains/* where desc.label = '{domain_name}' /**"
        )
        if response.data and "config" in response.data and "domainman" in response.data["config"]:
            return self._validate_filtered_response(response.data, "name", domain_name)
        else:
            raise DomainNotFoundError(f"Domain with name '{domain_name}' not found or malformed.")

    def add_domain(self, domain: Domain, name_id_check: bool = True) -> Domain:
        """
        Add a new domain to the VideoIPath Security-App.

        Args:
            domain (Domain): The Domain object to add.
            name_id_check (bool): If True, checks if a domain with the same name or ID already exists before adding.

        Returns:
            Domain: The added Domain object with its ID and revision updated.
        """
        if name_id_check:
            errors = []
            # Check by name
            try:
                self.get_domain_by_name(domain.desc.label)
                errors.append(f"Domain with name '{domain.desc.label}' already exists.")
            except DomainNotFoundError:
                pass
            # Check by ID
            if domain.id is not None:
                try:
                    self.get_domain_by_id(domain.id)
                    errors.append(f"Domain with ID '{domain.id}' already exists.")
                except DomainNotFoundError:
                    pass
            if errors:
                raise DomainAlreadyExistsError(" ".join(errors))

        body = self._generate_domain_action_request_body(add_list=[domain], update_list=[], remove_list=[])
        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/domains", body=body)

        if not response.result or not response.result.items:
            raise ValueError("Failed to add domain. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise ValueError("Unexpected number of items in response. Expected 1 item for the added domain.")
        if response.result.items[0].res != "added":
            raise ValueError(f"Domain addition failed with response: {response.result.items[0].msg}")

        added_domain = response.result.items[0]
        domain.id = added_domain.id
        domain.rev = added_domain.rev
        self._logger.info(f"Domain '{domain.desc.label}' added with ID '{domain.id}'.")
        return domain

    def update_domain(self, domain: Domain, name_check: bool = True) -> Domain:
        """
        Update an existing domain in the VideoIPath Security-App.

        Args:
            domain (Domain): The Domain object with updated values.
            name_check (bool): If True, checks if a domain with the same name already exists before updating.

        Returns:
            Domain: The updated Domain object with its revision updated.
        """

        if name_check:
            try:
                existing_domain = self.get_domain_by_name(domain.desc.label)
                if existing_domain.id != domain.id:
                    raise DomainAlreadyExistsError(
                        f"A domain with the name '{domain.desc.label}' already exists with ID '{existing_domain.id}'."
                    )
            except DomainNotFoundError:
                pass

        body = self._generate_domain_action_request_body(add_list=[], update_list=[domain], remove_list=[])
        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/domains", body=body)

        if not response.result or not response.result.items:
            raise ValueError("Failed to update domain. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise ValueError("Unexpected number of items in response. Expected 1 item for the updated domain.")

        updated_domain = response.result.items[0]
        domain.rev = updated_domain.rev

        if updated_domain.res == "updated":
            self._logger.info(f"Domain '{domain.desc.label}' updated with new revision '{domain.rev}'.")
        elif updated_domain.res.startswith("ignored"):
            self._logger.warning(f"Ignored update for domain '{domain.desc.label}' because no changes were made.")
        else:
            raise ValueError(f"Domain update failed with response: {updated_domain.msg}")

        return domain

    def remove_domain(self, domain: Domain) -> None:
        """
        Remove a domain from the VideoIPath Security-App.

        Args:
            domain (Domain): The Domain object to remove.

        Raises:
            DomainNotFoundError: If the domain does not exist.
        """
        body = self._generate_domain_action_request_body(add_list=[], update_list=[], remove_list=[domain])
        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/domains", body=body)

        if not response.result or not response.result.items:
            raise DomainRemoveError("Failed to remove domain. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise DomainRemoveError("Unexpected number of items in response. Expected 1 item for the removed domain.")

        removed_domain = response.result.items[0]
        if removed_domain.res == "removed":
            self._logger.info(f"Domain '{domain.desc.label}' with ID '{domain.id}' removed successfully.")
        else:
            raise DomainRemoveError(f"Domain removal failed with response: {removed_domain.msg}")

    def _validate_filtered_response(self, response_data: dict, filter_type: str, filter_value: str) -> Domain:
        """
        Validate the response data for a filtered query.

        Args:
            response_data (dict): The response data from the API.
            filter_type (str): The type of filter used (e.g., "id" or "name").
            filter_value (str): The value used for filtering.

        Returns:
            Domain: The Domain object if found, otherwise raises an error.
        """
        if response_data and "config" in response_data and "domainman" in response_data["config"]:
            domain_data = response_data["config"]["domainman"]["domains"]["_items"]
            if not isinstance(domain_data, list) or len(domain_data) == 0:
                raise DomainNotFoundError(f"No domains found with {filter_type} '{filter_value}'.")
            if len(domain_data) > 1:
                raise MultipleDomainsFoundError(f"Multiple domains found with {filter_type} '{filter_value}'.")
            return Domain.model_validate(domain_data[0])
        else:
            raise ValueError(f"Domain with {filter_type} '{filter_value}' not found or malformed response.")

    def _generate_domain_action_request_body(
        self, add_list: List[Domain], update_list: List[Domain], remove_list: List[Domain]
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

    # --- Resources ---
    def get_all_memberships(self) -> List[LocalMemberships]:
        """
        Fetch all local domain memberships from the VideoIPath Security-App.

        Returns:
            List[LocalMemberships]: List of LocalMemberships objects representing memberships.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/config/domainman/localDomainMemberships/**")
        if response.data and isinstance(response.data["config"]["domainman"]["localDomainMemberships"]["_items"], list):
            memberships = response.data["config"]["domainman"]["localDomainMemberships"]["_items"]
            return [LocalMemberships.model_validate(membership) for membership in memberships]
        else:
            raise ValueError("Response data is empty or malformed.")

    def get_memberships_by_type_and_id(self, resource_type: ResourceType, resource_id: str) -> LocalMemberships:
        """
        Fetch a specific local domain membership by resource type and ID.

        Args:
            resource_type (ResourceType): The type of the resource (e.g., "device", "profile").
            resource_id (str): The ID of the resource.

        Returns:
            LocalMemberships: The LocalMemberships object corresponding to the given type and ID.
        """

        response = self.vip_connector.rest.get(
            f"/rest/v2/data/config/domainman/localDomainMemberships/* where _id = '{resource_type.value}:{resource_id}' /**"
        )

        if response.data and "config" in response.data and "domainman" in response.data["config"]:
            memberships = response.data["config"]["domainman"]["localDomainMemberships"]["_items"]
            if not isinstance(memberships, list) or len(memberships) == 0:
                raise MembershipsNotFoundError(
                    f"No memberships found for {resource_type.value} with ID '{resource_id}'."
                )
            if len(memberships) > 1:
                raise MultipleMembershipsFoundError(
                    f"Multiple memberships found for {resource_type.value} with ID '{resource_id}'."
                )
            return LocalMemberships.model_validate(memberships[0])
        else:
            raise ValueError(
                f"Membership with {resource_type.value} ID '{resource_id}' not found or malformed response."
            )

    def add_memberships(self, memberships: LocalMemberships, check_existing: bool = True) -> LocalMemberships:
        """
        Add new local domain memberships.

        Args:
            memberships (LocalMemberships): The LocalMemberships object to add.

        Returns:
            LocalMemberships: The added LocalMemberships object with its ID and revision updated.
        """
        if check_existing:
            try:
                resource_type = memberships.resource_type
                resource_id = memberships.resource_id
                if not resource_type or not resource_id:
                    raise ValueError("Memberships must have a valid resource type and ID.")
                self.get_memberships_by_type_and_id(resource_type, resource_id)
                raise MembershipAlreadyExistsError(
                    f"Memberships for {resource_type.value} with ID '{resource_id}' already exist."
                )
            except MembershipsNotFoundError:
                pass

        body = RequestV2Patch()
        body.add(memberships)
        body.mode = "ignore_revs"  # Ignore revision checks for adding memberships

        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/localDomainMemberships", body=body)
        if not response.result or not response.result.items:
            raise ValueError("Failed to add memberships. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise ValueError("Unexpected number of items in response. Expected 1 item for the added memberships.")
        if response.result.items[0].res != "added":
            raise ValueError(f"Memberships addition failed with response: {response.result.items[0].msg}")

        # Update the membership object with the ID and revision from the response
        if not response.result.items[0].id or not response.result.items[0].rev:
            raise ValueError("Response does not contain ID or revision for the added memberships.")
        added_membership = response.result.items[0]
        memberships.id = added_membership.id
        memberships.rev = added_membership.rev

        return memberships

    def update_memberships(self, memberships: LocalMemberships, ignore_revs: bool = False) -> LocalMemberships:
        """
        Update existing local domain memberships.

        Args:
            memberships (LocalMemberships): The LocalMemberships object with updated values.

        Returns:
            LocalMemberships: The updated LocalMemberships object with its revision updated.
        """
        body = RequestV2Patch()
        body.update(memberships)

        if ignore_revs:
            body.mode = "ignore_revs"

        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/localDomainMemberships", body=body)
        if not response.result or not response.result.items:
            raise ValueError("Failed to update memberships. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise ValueError("Unexpected number of items in response. Expected 1 item for the updated memberships.")
        updated_membership = response.result.items[0]
        if updated_membership.res == "updated":
            self._logger.info(
                f"Memberships for {memberships.resource_type.value} with ID '{memberships.resource_id}' updated."
            )
        elif updated_membership.res.startswith("ignored"):
            self._logger.warning(
                f"Ignored update for memberships of {memberships.resource_type.value} with ID '{memberships.resource_id}' because no changes were made."
            )
        else:
            raise ValueError(f"Memberships update failed with response: {updated_membership.msg}")

        memberships.rev = updated_membership.rev
        return memberships

    def remove_memberships(self, memberships: LocalMemberships) -> None:
        """
        Remove local domain memberships.

        Args:
            memberships (LocalMemberships): The LocalMemberships object to remove.

        Raises:
            DomainNotFoundError: If the membership does not exist.
        """
        body = RequestV2Patch()
        body.remove(memberships)

        response = self.vip_connector.rest.patch("/rest/v2/data/config/domainman/localDomainMemberships", body=body)
        if not response.result or not response.result.items:
            raise ValueError("Failed to remove membership. Response does not contain expected items.")
        if len(response.result.items) != 1:
            raise ValueError("Unexpected number of items in response. Expected 1 item for the removed membership.")
        removed_membership = response.result.items[0]
        if removed_membership.res == "removed":
            self._logger.info(
                f"Memberships for {memberships.resource_type.value} with ID '{memberships.resource_id}' removed successfully."
            )
        else:
            raise ValueError(f"Memberships removal failed with response: {removed_membership.msg}")
        # No return value, as the membership is removed
