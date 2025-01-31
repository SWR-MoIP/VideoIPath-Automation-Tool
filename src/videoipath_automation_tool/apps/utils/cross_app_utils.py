import re


def _validate_device_id_string(device_id: str) -> bool:
    """Validate the device_id string."""
    pattern_device = r"\bdevice\d+\b"
    if re.match(pattern_device, device_id):
        return True
    return False


def _validate_virtual_device_id_string(device_id: str) -> bool:
    """Validate the virtual device_id string."""
    pattern_virtual_device = r"\bvirtual\.\d+\b"
    if re.match(pattern_virtual_device, device_id):
        return True
    return False


def validate_device_id_string(device_id: str, include_virtual: bool = False) -> bool:
    """Validate the device_id string. Optionally include virtual device_id strings."""
    if include_virtual:
        return _validate_device_id_string(device_id) or _validate_virtual_device_id_string(device_id)
    return _validate_device_id_string(device_id)
