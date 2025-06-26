from videoipath_automation_tool.apps.inventory.model.global_snmp_config import SnmpConfiguration
from videoipath_automation_tool.connector.models.request_rpc import RequestRPC
from videoipath_automation_tool.validators.uuid_4 import validate_uuid_4


class SnmpRequestRpc(RequestRPC):
    # Wrapper class for RequestRpc

    def add(self, config: SnmpConfiguration):
        """Method to add a new global SNMP configuration

        Args:
            config (SnmpConfiguration): SNMP configuration to add
        """
        try:
            validate_uuid_4(config.id)
        except ValueError as e:
            raise ValueError(
                f"To add a new global SNMP configuration, a valid 'id' (UUID 4 format) must be set in the configuration. Error: {e}"
            )
        return super().add(config.id, config)

    def update(self, config: SnmpConfiguration):
        """Method to update a global SNMP configuration

        Args:
            config (SnmpConfiguration): SNMP configuration to update
        """
        try:
            validate_uuid_4(config.id)
        except ValueError as e:
            raise ValueError(
                f"To update a global SNMP configuration, a valid 'id' (UUID 4 format) must be set in the configuration. Error: {e}"
            )
        return super().update(config.id, config)

    def remove(self, config_id: str | list[str]):
        """Method to remove a global SNMP configuration

        Args:
            config_id (str | list[str]): Id or List of Ids of the configuration
        """
        try:
            if isinstance(config_id, list):
                for c_id in config_id:
                    validate_uuid_4(c_id)
            else:
                validate_uuid_4(config_id)
        except ValueError as e:
            raise ValueError(f"Invalid 'config_id' format. Must be a valid UUID 4 format. Error: {e}")
        return super().remove(config_id)
