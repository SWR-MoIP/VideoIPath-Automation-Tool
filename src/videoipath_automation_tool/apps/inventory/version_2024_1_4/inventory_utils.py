from typing import Tuple


def extract_driver_info_from_id(driver_id: str) -> Tuple[str, str, str]:
    """
    Extracts driver_organization, driver_name, and driver_version from driver_id.

    Args:
        driver_id: The driver_id string to extract the information from.

    Returns:
        Tuple[str, str, str]: Tuple with driver_organization, driver_name, and driver_version.
    """
    parts = driver_id.rsplit("-", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid driver_id format: {driver_id}")

    driver_org_and_name, driver_version = parts
    org_parts = driver_org_and_name.split(".")
    driver_organization = ".".join(org_parts[:2])
    driver_name = ".".join(org_parts[2:])

    return driver_organization, driver_name, driver_version


def construct_driver_id_from_info(driver_organization: str, driver_name: str, driver_version: str):
    """
    Constructs driver_id from driver_organization, driver_name, and driver_version.

    Args:
        driver_organization: The driver organization.
        driver_name: The driver name.
        driver_version: The driver version.

    Returns:
        str: The constructed driver_id: "{driver_organization}.{driver_name}-{driver_version}"
    """
    return f"{driver_organization}.{driver_name}-{driver_version}"
