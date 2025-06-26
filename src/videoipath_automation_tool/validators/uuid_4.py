import uuid


def validate_uuid_4(uuid_4: str) -> str:
    """
    Validates and normalizes a UUIDv4 string.

    Args:
        uuid_4: The input string to validate.

    Returns:
        The normalized UUIDv4 string (lowercase, with dashes).

    Raises:
        ValueError: If input is not a valid UUIDv4.
    """
    if not isinstance(uuid_4, str):
        raise ValueError(f"UUID must be a string, got {type(uuid_4).__name__}")

    try:
        u = uuid.UUID(uuid_4)
    except (ValueError, AttributeError, TypeError):
        raise ValueError(f"Invalid UUID format: '{uuid_4}'")

    if u.version != 4:
        raise ValueError(f"UUID is not version 4: '{uuid_4}'")

    return str(u)
