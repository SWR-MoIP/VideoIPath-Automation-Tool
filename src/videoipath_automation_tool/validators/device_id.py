import re


def validate_device_id(device_id: str) -> str:
    """
    Validates a device ID string.

    Args:
        device_id: The device ID string to validate.

    Returns:
        The validated device ID string.

    Raises:
        ValueError: If the device ID is not a string or does not match the expected format.
    """
    if not isinstance(device_id, str):
        raise ValueError(f"Each device ID must be a string. Invalid device ID: {device_id}")

    pattern = r"device(0|[1-9]\d*)"
    # Regular expression pattern explanation:
    # device(0|[1-9]\d*) - The device ID starts with the word 'device' followed by a number:
    #                    - '0' or
    #                    - a positive integer (1-9) followed by zero or more digits between 0 and 9.

    if not re.fullmatch(pattern, device_id):
        raise ValueError(f"Invalid device ID syntax: '{device_id}'. The expected format is: device<number>.")

    return device_id
