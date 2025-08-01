from logging import Logger
from typing import Optional

from videoipath_automation_tool.apps.security.model.domain_model import Domain, DomainDesc
from videoipath_automation_tool.apps.security.security_api import SecurityAPI


class SecurityDomains:
    def __init__(self, security_api: SecurityAPI, logger: Logger):
        self._security_api = security_api
        self._logger = logger

    def get_domain_by_id(self, domain_id: str) -> Domain:
        """Returns a Domain object by its ID.

        Args:
            domain_id (str): The ID of the domain to retrieve.

        Returns:
            Domain: The Domain object with the specified ID.
        """
        return self._security_api.get_domain_by_id(domain_id)

    def get_domain_by_name(self, domain_name: str) -> Domain:
        """Returns a Domain object by its name.

        Args:
            domain_name (str): The name of the domain to retrieve.

        Returns:
            Domain: The Domain object with the specified name.
        """
        return self._security_api.get_domain_by_name(domain_name)

    def get_all_domains(self) -> list[Domain]:
        """Returns a list of all domains available on the VideoIPath server."""
        return self._security_api.get_all_domains()

    def list_domain_names(self) -> list[str]:
        """Returns a list of all domain names."""
        return [domain.name for domain in self.get_all_domains()]

    def add_domain(self, domain: Domain) -> Domain:
        """Adds a new domain to the VideoIPath server.

        Args:
            domain (Domain): The Domain object to add.

        Returns:
            Domain: The added Domain object with its generated ID and initial revision.
        """
        return self._security_api.add_domain(domain)

    def update_domain(self, domain: Domain) -> Domain:
        """Updates an existing domain on the VideoIPath server.

        Args:
            domain (Domain): The Domain object with updated information.

        Returns:
            Domain: The updated Domain object.
        """
        return self._security_api.update_domain(domain)

    def remove_domain(self, domain: Domain):
        """Removes a domain from the VideoIPath server.

        Args:
            domain (Domain): The Domain object to remove.

        Returns:
            Domain: The removed Domain object.
        """
        try:
            self._security_api.remove_domain(domain)
        except Exception as e:
            self._logger.error(f"Error removing domain: {e}")

    def create_domain(self, name: str, description: Optional[str] = "") -> Domain:
        """Creates a new domain with the given name and optional description on the VideoIPath server.

        Args:
            name (str): The name of the domain to create.
            description (Optional[str], optional): The description of the domain. Defaults to "".

        Returns:
            Domain: The created Domain object with its generated ID and initial revision.
        """

        domain = Domain(desc=DomainDesc.model_validate({"label": name, "desc": description}))

        self._logger.debug(f"Creating domain with name: {name} and description: {description}")
        created_domain = self._security_api.add_domain(domain=domain)

        self._logger.info(
            f"Domain created with ID: {created_domain.id}, Name: {created_domain.name}, "
            f"Description: {created_domain.description} (Revision: {created_domain.rev})"
        )

        return created_domain
