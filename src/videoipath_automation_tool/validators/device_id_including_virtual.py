from videoipath_automation_tool.validators.device_id import validate_device_id
from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


def validate_device_id_including_virtual(id: str) -> str:
    """
    Validates a device ID string, supporting both physical and virtual device identifiers.

    Args:
        id: The ID string to validate (format: 'device<number>' or 'virtual.<number>').

    Returns:
        The validated ID string.

    Raises:
        ValueError: If the ID is not a string or does not match one of the expected formats.
    """
    if not isinstance(id, str):
        raise ValueError(f"Each virtual device ID must be a string. Invalid virtual device ID: {id}")

    for validator in (validate_device_id, validate_virtual_device_id):
        try:
            return validator(id)
        except ValueError:
            continue

    raise ValueError(f"Invalid device ID syntax: '{id}'. Expected formats: 'device<number>' or 'virtual.<number>'.")
