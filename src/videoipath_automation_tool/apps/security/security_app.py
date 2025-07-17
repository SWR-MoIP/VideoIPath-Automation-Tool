import logging
from typing import Optional

from videoipath_automation_tool.apps.security.model.domain_model import Domain, DomainDesc
from videoipath_automation_tool.apps.security.security_api import SecurityAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class SecurityApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """SecurityApp contains functionality to interact with the VideoIPath Security App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_security_app")

        # --- Setup Security API ---
        self._security_api = SecurityAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Security APP initialized.")

    # experimental
    def create_domain(self, name: str, description: Optional[str] = ""):
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
