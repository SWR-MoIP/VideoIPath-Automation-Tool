from typing import Literal, Optional, Union, overload

from videoipath_automation_tool.apps.inventory import (
    InventoryApp2023_4_2,
    InventoryApp2023_4_35,
    InventoryApp2024_1_4,
    InventoryApp2024_3_3,
    InventoryApp2024_4_12,
)
from videoipath_automation_tool.apps.videoipath_app import GenericVideoIPathApp, VideoIPathVersion


@overload
def VideoIPathApp(
    *,
    version: Literal["2023.4.2"],
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp[InventoryApp2023_4_2]: ...


@overload
def VideoIPathApp(
    *,
    version: Literal["2023.4.35"],
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp[InventoryApp2023_4_35]: ...


@overload
def VideoIPathApp(
    *,
    version: Literal["2024.1.4"],
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp[InventoryApp2024_1_4]: ...


@overload
def VideoIPathApp(
    *,
    version: Literal["2024.3.3"],
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp[InventoryApp2024_3_3]: ...


@overload
def VideoIPathApp(
    *,
    version: Literal["2024.4.12"],
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp[InventoryApp2024_4_12]: ...


@overload
def VideoIPathApp(
    *,
    version: Optional[VideoIPathVersion] = None,
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> GenericVideoIPathApp: ...


def VideoIPathApp(
    *,
    version: Optional[VideoIPathVersion] = "2024.1.4",
    server_address: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_https: Optional[bool] = None,
    verify_ssl_cert: Optional[bool] = None,
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    environment: Optional[str] = None,
) -> Union[
    GenericVideoIPathApp[InventoryApp2024_1_4],
    GenericVideoIPathApp[InventoryApp2023_4_2],
    GenericVideoIPathApp[InventoryApp2023_4_35],
    GenericVideoIPathApp[InventoryApp2024_3_3],
    GenericVideoIPathApp[InventoryApp2024_4_12],
]:
    """
    Initialize the VideoIPath Automation Tool, establish connection to the VideoIPath-Server and initialize the Apps for interaction.
    Parameters can be provided directly or read from the environment variables.

    Args:
        server_address (str, optional): IP or hostname of the VideoIPath-Server. [ENV: VIPAT_VIDEOIPATH_SERVER_ADDRESS]
        username (str, optional): Username for the API User. [ENV: VIPAT_VIDEOIPATH_USERNAME]
        password (str, optional): Password for the API User. [ENV: VIPAT_VIDEOIPATH_PASSWORD]
        use_https (bool, optional): Set to `True` if the VideoIPath Server uses HTTPS. [ENV: VIPAT_USE_HTTPS]
        verify_ssl_cert (bool, optional): Set to `True` if the SSL certificate should be verified. [ENV: VIPAT_VERIFY_SSL_CERT]
        log_level (str, optional): The log level for the logging module, possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. [ENV: VIPAT_LOG_LEVEL]
        environment (str, optional): Define the environment: `DEV`, `TEST`, `PROD`. [ENV: VIPAT_ENVIRONMENT]
        version (str, optional): The VideoIPath version to use. Defaults to "latest". [ENV: VIPAT_VERSION]
    """
    return GenericVideoIPathApp(
        server_address=server_address,
        username=username,
        password=password,
        use_https=use_https,
        verify_ssl_cert=verify_ssl_cert,
        log_level=log_level,
        environment=environment,
        version=version,
    )
