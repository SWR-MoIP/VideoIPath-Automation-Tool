import re


def validate_alarm_filter(filter: str) -> str:
    """
    Validates an alarm filter string.

    Args:
        filter: The alarm filter string to validate.

    Returns:
        The validated alarm filter string.

    Raises:
        ValueError: If the filter is not a string or does not match the expected format.
    """
    if not isinstance(filter, str):
        raise ValueError(f"Each alarm filter must be a string. Invalid filter: {filter}")

    pattern = r"^\d+:([a-zA-Z0-9\-\.]+|\*\*|\*):([a-zA-Z0-9\-\s\[\]/]+|/[^/]+/|[\w\-,]+):(\*|[1-6])$"
    # Regular expression pattern explanation:
    # ^\d+:                     - The filter starts with a numeric scFilter (one or more digits) followed by a colon (:).
    # ([a-zA-Z0-9\-\.]+|\*\*|\*) - pointIdFilter: Matches:
    #                              - Alphanumeric strings with dots (.), dashes (-),
    #                              - '**' as a wildcard for all remaining depth,
    #                              - '*' as a wildcard for a single element.
    # :                          - Separator between pointIdFilter and alarmIdFilter.
    # ([a-zA-Z0-9\-\s\[\]/]+|/[^/]+/|[\w\-,]+) - alarmIdFilter: Matches:
    #                              - Alphanumeric strings with dashes (-), spaces, square brackets ([]), and slashes (/),
    #                              - Regular expressions enclosed in slashes (/regex/),
    #                              - Or comma-separated values.
    # :                          - Separator between alarmIdFilter and severityFilter.
    # (\*|[1-6])                 - severityFilter: Matches:
    #                              - '*' as a wildcard for any severity,
    #                              - Or a numeric severity level between 1 and 6.
    # $                          - Ensures the string ends at this point (no extra characters allowed).

    if not re.fullmatch(pattern, filter):
        raise ValueError(
            f"Invalid alarm filter syntax: '{filter}'. The expected format is: "
            "scFilter:pointIdFilter:alarmIdFilter:severityFilter."
        )

    # Additional logic for severity validation
    parts = filter.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid filter structure: '{filter}'. It must contain exactly three colons (':').")

    severity_filter = parts[3]
    if severity_filter != "*" and not severity_filter.isdigit():
        raise ValueError(f"Invalid severity filter in '{filter}'. It must be '*' or a number between 1 and 6.")
    if severity_filter.isdigit():
        severity_value = int(severity_filter)
        if not 1 <= severity_value <= 6:
            raise ValueError(f"Severity filter out of range in '{filter}'. It must be a number between 1 and 6.")

    return filter
