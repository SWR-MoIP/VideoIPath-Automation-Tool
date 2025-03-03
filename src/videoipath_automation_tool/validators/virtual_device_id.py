import re


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

    pattern = r"virtual\.(0|[1-9]\d*)"
    # Regular expression pattern explanation:
    # virtual\.(0|[1-9]\d*) - The virtual device ID starts with the word 'virtual.' followed by a number:
    #                       - '0' or
    #                       - a positive integer (1-9) followed by zero or more digits between 0 and 9.

    if not re.fullmatch(pattern, virtual_device_id):
        raise ValueError(
            f"Invalid virtual device ID syntax: '{virtual_device_id}'. The expected format is: virtual.<number>."
        )

    return virtual_device_id
