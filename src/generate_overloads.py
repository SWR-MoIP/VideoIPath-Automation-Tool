import re
from typing import Callable

from videoipath_automation_tool.apps.inventory.model.drivers import DRIVER_ID_TO_CUSTOM_SETTINGS


def generate_create_device_overloads() -> str:
    return "\n".join(
        f"    @overload\n"
        f'    def create_device(self, driver: Literal["{driver_id}"]) -> InventoryDevice[{custom_settings_type.__name__}]: ...\n'
        for driver_id, custom_settings_type in DRIVER_ID_TO_CUSTOM_SETTINGS.items()
    )


def generate_get_device_overloads() -> str:
    return "\n".join(
        f"    @overload\n"
        f'    def get_device(self, label: Optional[str] = None, device_id: Optional[str] = None, address: Optional[str] = None, config_only: bool = False, custom_settings_type: Optional[Literal["{driver_id}"]] = None) -> InventoryDevice[{custom_settings_type.__name__}]: ...\n'
        for driver_id, custom_settings_type in DRIVER_ID_TO_CUSTOM_SETTINGS.items()
    )


def generate_overloads(method: str, generate_overloads: Callable) -> None:
    FILE_PATH = f"src/videoipath_automation_tool/apps/inventory/app/{method}.py"

    with open(FILE_PATH, "r") as f:
        content = f.read()

    overload_pattern = re.compile(
        r"# --------------------------------\n    #  Start Auto-Generated Overloads\n    # --------------------------------\n(.*?)# ------------------------------\n    #  End Auto-Generated Overloads\n    # ------------------------------",
        re.DOTALL,
    )

    if not re.findall(overload_pattern, content):
        print(f"No overload section found in {FILE_PATH} ❌")
        return

    with open(FILE_PATH, "w") as f:
        f.write(
            re.sub(
                overload_pattern,
                f"# --------------------------------\n    #  Start Auto-Generated Overloads\n    # --------------------------------\n\n{generate_overloads()}\n\n    # ------------------------------\n    #  End Auto-Generated Overloads\n    # ------------------------------",
                content,
            )
        )

    print(f"Updated overloads in {FILE_PATH} ✅")


if __name__ == "__main__":
    overloaded_methods = {
        "create_device": generate_create_device_overloads,
        "get_device": generate_get_device_overloads,
    }
    for method, generator in overloaded_methods.items():
        generate_overloads(method, generator)
