import logging
import re
import uuid

from typing_extensions import deprecated

from videoipath_automation_tool.validators.device_id import validate_device_id
from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


# --- Fallback Logger ---
def create_fallback_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.debug(f"No logger provided. Creating fallback logger: '{name}'.")
    return logger


# --- Generate UUID4 ---
def generate_uuid_4():
    return str(uuid.uuid4())


# --- Natural Sort Device ID list ---
def extract_natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


# --- Deprecated Functions for Device ID Validation ---
# --- Device ID string validation ---
@deprecated("Use 'validate_device_id' from 'videoipath_automation_tool.validators.device_id' instead.")
def _validate_device_id_string(device_id: str) -> bool:
    """Validate the device_id string."""
    try:
        validate_device_id(device_id)
        return True
    except ValueError:
        return False


@deprecated("Use 'validate_virtual_device_id' from 'videoipath_automation_tool.validators.virtual_device_id' instead.")
def _validate_virtual_device_id_string(device_id: str) -> bool:
    """Validate the virtual device_id string."""
    try:
        validate_virtual_device_id(device_id)
        return True
    except ValueError:
        return False


@deprecated(
    "This function is deprecated. Use 'validate_device_id' and 'validate_virtual_device_id' from "
    "'videoipath_automation_tool.validators' instead."
)
def validate_device_id_string(device_id: str, include_virtual: bool = False) -> bool:
    """Validate the device_id string. Optionally include virtual device_id strings."""
    if include_virtual:
        return _validate_device_id_string(device_id) or _validate_virtual_device_id_string(device_id)
    return _validate_device_id_string(device_id)
