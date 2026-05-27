def virtual_dash_to_dot(device_id: str) -> str:
    if device_id.startswith("virtual-"):
        return "virtual." + device_id.removeprefix("virtual-")
    return device_id


def virtual_dot_to_dash(device_id: str) -> str:
    if device_id.startswith("virtual."):
        return "virtual-" + device_id.removeprefix("virtual.")
    return device_id


def format_edge_id(from_id: str, to_id: str) -> str:
    return f"{from_id}::{to_id}"
