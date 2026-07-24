import re

_VIRTUAL_DEVICE_ID_PATTERN = re.compile(r"virtual\.(0|[1-9]\d*)")


def is_virtual_device_id(device_id: str) -> bool:
    """Return whether ``device_id`` matches the ``virtual.<number>`` topology id form."""
    return isinstance(device_id, str) and _VIRTUAL_DEVICE_ID_PATTERN.fullmatch(device_id) is not None


def validate_virtual_device_id(virtual_device_id: str) -> str:
    """
    Validates a virtual device ID string.

    Args:
        virtual_device_id: The virtual device ID string to validate.

    Returns:
        The validated virtual device ID string.

    Raises:
        ValueError: If the virtual device ID is not a string or does not match the expected format.
    """
    if not isinstance(virtual_device_id, str):
        raise ValueError(f"Each virtual device ID must be a string. Invalid virtual device ID: {virtual_device_id}")

    if not is_virtual_device_id(virtual_device_id):
        raise ValueError(
            f"Invalid virtual device ID syntax: '{virtual_device_id}'. The expected format is: virtual.<number>."
        )

    return virtual_device_id
