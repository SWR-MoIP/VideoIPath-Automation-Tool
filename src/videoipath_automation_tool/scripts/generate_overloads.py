import os
import re
from typing import Callable

from videoipath_automation_tool.utils.script_utils import ROOT_DIR, load_module

DRIVERS_MODULE = load_module(
    "drivers_module",
    os.path.join(ROOT_DIR, "apps", "inventory", "model", "drivers.py"),
)
DRIVER_ID_TO_CUSTOM_SETTINGS = DRIVERS_MODULE.DRIVER_ID_TO_CUSTOM_SETTINGS


def generate_create_device_overloads() -> str:
    return "\n".join(
        f"    @overload\n"
        f'    def create_device(self, driver: Literal["{driver_id}"]) -> InventoryDevice[{custom_settings_type.__name__}]: ...\n'
        for driver_id, custom_settings_type in DRIVER_ID_TO_CUSTOM_SETTINGS.items()
    )


def generate_create_device_from_discovered_device_overloads() -> str:
    return "\n".join(
        f"    @overload\n"
        f'    def create_device_from_discovered_device(self, discovered_device_id: str, driver: Literal["{driver_id}"], suggested_config_index: int = 0) -> InventoryDevice[{custom_settings_type.__name__}]: ...\n'
        for driver_id, custom_settings_type in DRIVER_ID_TO_CUSTOM_SETTINGS.items()
    )


def generate_get_device_overloads() -> str:
    return "\n".join(
        f"    @overload\n"
        f'    def get_device(self, label: Optional[str] = None, device_id: Optional[str] = None, address: Optional[str] = None, custom_settings_type: Optional[Literal["{driver_id}"]] = None, config_only: bool = False, label_search_mode: Literal["canonical_label", "factory_label_only", "user_defined_label_only"] = "canonical_label", status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT, status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT) -> InventoryDevice[{custom_settings_type.__name__}]: ...\n'
        for driver_id, custom_settings_type in DRIVER_ID_TO_CUSTOM_SETTINGS.items()
    )


def generate_overloads(method: str, generate_overloads: Callable) -> None:
    FILE_PATH = os.path.join(ROOT_DIR, "apps", "inventory", "app", f"{method}.py")

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


def main():
    overloaded_methods = {
        "create_device": generate_create_device_overloads,
        "create_device_from_discovered_device": generate_create_device_from_discovered_device_overloads,
        "get_device": generate_get_device_overloads,
    }
    for method, generator in overloaded_methods.items():
        generate_overloads(method, generator)


if __name__ == "__main__":
    main()
