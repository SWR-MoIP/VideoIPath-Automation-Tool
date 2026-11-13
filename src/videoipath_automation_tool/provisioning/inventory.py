"""Inventory integration: plan and write exactly one Inventory record through the injected app.

Only *managed* fields are compared and written: fields explicitly present in the resolved blueprint,
deliberately supplied instance facts, and labels from enabled naming rules. For an update the current
record is deep-copied and only managed fields are overlaid, so unrelated settings are preserved
(within what the Inventory models represent — the same round-trip ``InventoryApp.update_device``
performs). The generic comparison of ``update_device`` is bypassed once a managed change is known, so
explicit credential changes cannot be swallowed by its authentication filtering.

Secrets (passwords, alternative-address credentials) are write-only: the server masks them on read, so
they are never compared. They are written on create and with every update, and they cause an update on
their own only with ``ApplyOptions(write_credentials=True)``.

Conflict detection is client-side (re-read and compare before writing); a read-to-write race remains.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr

from videoipath_automation_tool.apps.inventory.errors import InventoryStatusUnavailableError
from videoipath_automation_tool.apps.inventory.model.device_status import DeviceStatus
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration import Auth
from videoipath_automation_tool.provisioning.errors import (
    ProvisioningCapabilityError,
    ProvisioningConflictError,
    ProvisioningError,
    ProvisioningTargetError,
    ProvisioningValidationError,
    ValidationIssue,
)
from videoipath_automation_tool.provisioning.models import (
    AlternativeAddress,
    CatalogId,
    FieldChange,
    PlannedOperation,
    ProvisioningDevice,
)
from videoipath_automation_tool.provisioning.resolution import ResolvedInventory

REDACTED = "********"
_SENSITIVE_TOKENS = frozenset({"password", "passwd", "secret", "token", "community", "key"})

# Fields whose change may alter what the driver discovers (topology work after them is deferred).
TOPOLOGY_AFFECTING_PREFIXES = ("address", "alt_addresses", "credentials.", "generic.", "custom_settings.", "active")


class DesiredValue(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    value: Any
    source: str


class InventoryWork(BaseModel):
    """Internal, unredacted Inventory work captured by a plan (never serialized for review)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    action: str  # "create" | "update" | "none"
    inventory_id: str | None = None
    driver_id: str
    desired: dict[str, DesiredValue]
    baseline: dict[str, str]
    """Fingerprints of the current managed values (and driver) used for the stale-plan check."""
    changes: list[FieldChange]

    @property
    def operation(self) -> PlannedOperation | None:
        if self.action == "none":
            return None
        return PlannedOperation(
            action="create" if self.action == "create" else "update",
            entity_kind="inventory",
            entity_id=self.inventory_id,
            changes=self.changes,
        )

    @property
    def affects_topology(self) -> bool:
        return self.action == "create" or any(
            change.field.startswith(TOPOLOGY_AFFECTING_PREFIXES) for change in self.changes
        )


class InventoryGateway:
    """The only place that talks to ``app.inventory``."""

    def __init__(self, inventory_app: Any) -> None:
        self._app = inventory_app
        self._snmp_cache: dict[str, str] = {}

    # --- Reads ---

    def read(self, inventory_id: str) -> InventoryDevice:
        try:
            return self._app.get_device(device_id=inventory_id, config_only=True)
        except ValueError as exc:
            raise ProvisioningTargetError(f"Inventory record '{inventory_id}' was not found: {exc}") from None

    def read_status(self, device: InventoryDevice) -> DeviceStatus | None:
        """One fresh status request, without the Inventory get-device retry loop."""
        try:
            return self._app.refresh_device_status(device=device).status
        except InventoryStatusUnavailableError:
            return None

    def ids_with_label(self, label: str) -> list[str]:
        found = self._app.find_device_id_by_label(label, label_search_mode="user_defined_label_only")
        return _as_list(found)

    def ids_by_addresses(self, addresses: list[str]) -> dict[str, list[str]]:
        """Device ids per address (normalized comparison), in one read.

        A response with no item list raises :class:`ProvisioningError`.
        """
        if not addresses:
            return {}
        try:
            return self._app.find_device_ids_by_addresses(addresses)
        except ValueError as exc:
            raise ProvisioningError(f"Could not read Inventory addresses for the conflict check: {exc}") from exc

    def resolve_snmp(self, reference: str | CatalogId) -> str:
        """Exact SNMP configuration id for a label or ``{id: ...}``; missing/ambiguous fail."""
        key = reference.id if isinstance(reference, CatalogId) else f"label:{reference}"
        if key in self._snmp_cache:
            return self._snmp_cache[key]
        if isinstance(reference, CatalogId):
            if reference.id != "default" and self._app.get_global_snmp_config_label_by_id(reference.id) is None:
                raise ProvisioningTargetError(f"SNMP configuration id '{reference.id}' does not exist.")
            resolved = reference.id
        else:
            found = _as_list(self._app.get_global_snmp_config_id_by_label(reference))
            if not found:
                raise ProvisioningTargetError(f"No SNMP configuration labelled '{reference}'.")
            if len(found) > 1:
                raise ProvisioningTargetError(
                    f"SNMP configuration label '{reference}' is ambiguous ({', '.join(found)}); use {{id: ...}}."
                )
            resolved = found[0]
        self._snmp_cache[key] = resolved
        return resolved

    # --- Writes ---

    def create(self, candidate: InventoryDevice) -> InventoryDevice:
        return self._app.add_device(candidate, label_check=False, address_check=False, config_only=True)

    def update(self, candidate: InventoryDevice) -> InventoryDevice:
        return self._app.update_device(candidate, compare_config=False, config_only=True)


def plan_inventory(
    gateway: InventoryGateway,
    resolved: ResolvedInventory,
    device: ProvisioningDevice,
    *,
    label: str | None,
    description: str | None,
    write_credentials: bool = False,
) -> tuple[InventoryWork, InventoryDevice | None]:
    """Compute the Inventory work (read-only). Returns the work and the current record (if bound).

    Secrets are not compared (see the module docstring); for an existing record they are listed as
    changes only when ``write_credentials`` is set.
    """
    desired = _desired_values(gateway, resolved, device, label=label, description=description)

    current: InventoryDevice | None = None
    if device.inventory_id is not None:
        current = gateway.read(device.inventory_id)
        if current.driver_id != resolved.driver_id:
            raise ProvisioningCapabilityError(
                f"Inventory record '{device.inventory_id}' uses driver '{current.driver_id}', the blueprint selects "
                f"'{resolved.driver_id}'. Driver migration is not automatic; migrate explicitly with the Inventory API."
            )
    else:
        if device.management_address is None:
            raise ProvisioningTargetError(
                f"Creating an Inventory record for '{device.key}' requires 'management_address' "
                "(or bind an existing record with 'inventory_id')."
            )
        if "label" not in desired:
            raise ProvisioningValidationError(
                ValidationIssue(
                    path="naming.inventory_label",
                    message="Creating an Inventory record requires an Inventory label; the naming entry is disabled.",
                    code="naming.missing",
                )
            )

    changes = [
        _field_change(key, get_field(current, key) if current is not None else None, item)
        for key, item in desired.items()
        if current is None
        or (write_credentials if is_sensitive(key) else not values_equal(get_field(current, key), item.value))
    ]
    _check_conflicts(gateway, device, desired, changes, own_id=device.inventory_id)

    action = "create" if current is None else ("update" if changes else "none")
    work = InventoryWork(
        action=action,
        inventory_id=device.inventory_id,
        driver_id=resolved.driver_id,
        desired=desired,
        baseline=_baseline(current, desired) if current is not None else {},
        changes=changes,
    )
    return work, current


def recheck_conflicts(gateway: InventoryGateway, device: ProvisioningDevice, work: InventoryWork) -> None:
    """Repeat the label/address conflict check immediately before a write."""
    _check_conflicts(gateway, device, work.desired, work.changes, own_id=work.inventory_id)


def build_candidate(base: InventoryDevice, desired: dict[str, DesiredValue]) -> InventoryDevice:
    candidate = base.model_copy(deep=True)
    for key, item in desired.items():
        set_field(candidate, key, item.value)
    return candidate


def new_device(driver_id: str) -> InventoryDevice:
    return InventoryDevice.create(driver_id=driver_id)


def check_baseline(work: InventoryWork, fresh: InventoryDevice) -> None:
    """Stop when a managed value or the driver changed since planning."""
    current = _baseline(fresh, work.desired)
    changed = sorted(key for key in work.baseline if current.get(key) != work.baseline[key])
    if changed:
        raise ProvisioningConflictError(
            f"Inventory record '{work.inventory_id}' changed since planning ({', '.join(changed)}); replan."
        )


def verify(device: InventoryDevice, desired: dict[str, DesiredValue]) -> list[str]:
    """Managed fields whose read-back differs (secrets are not compared: the server masks them)."""
    return sorted(
        key
        for key, item in desired.items()
        if not is_sensitive(key) and not values_equal(get_field(device, key), item.value)
    )


def get_field(device: InventoryDevice, key: str) -> Any:
    getter, _ = _accessor(key)
    return getter(device)


def set_field(device: InventoryDevice, key: str, value: Any) -> None:
    _, setter = _accessor(key)
    setter(device, value)


def values_equal(current: Any, desired: Any) -> bool:
    return _plain(current) == _plain(desired)


def is_sensitive(key: str) -> bool:
    if key in ("credentials.password", "alt_addresses_with_auth"):
        return True
    tokens = set(re.split(r"[^a-z0-9]+", key.lower()))
    return bool(tokens & _SENSITIVE_TOKENS)


# --- Internal ---


def _desired_values(
    gateway: InventoryGateway,
    resolved: ResolvedInventory,
    device: ProvisioningDevice,
    *,
    label: str | None,
    description: str | None,
) -> dict[str, DesiredValue]:
    config = resolved.config
    provenance = resolved.provenance
    desired: dict[str, DesiredValue] = {}

    def put(key: str, value: Any, source: str) -> None:
        desired[key] = DesiredValue(value=value, source=source)

    if label is not None:
        put("label", label, "naming")
    if description is not None:
        put("description", description, "naming")
    if device.management_address is not None:
        put("address", device.management_address, "instance")
    if device.alternative_addresses is not None:
        entries = device.alternative_addresses
        put("alt_addresses", [e if isinstance(e, str) else e.address for e in entries], "instance")
        put(
            "alt_addresses_with_auth",
            [_alt_with_auth(e) for e in entries if isinstance(e, AlternativeAddress) and e.credentials is not None],
            "instance",
        )
    if device.credentials is not None:
        put("credentials.username", device.credentials.username, "instance")
        put("credentials.password", device.credentials.password, "instance")
    if config.active is not None:
        put("active", config.active, provenance.get("active", "blueprint"))
    if config.generic_settings is not None:
        for name, value in config.generic_settings.managed().items():
            put(f"generic.{name}", value, provenance.get(f"generic_settings.{name}", "blueprint"))
    if config.snmp is not None:
        snmp = config.snmp.managed()
        if "use_global_settings" in snmp:
            put(
                "snmp.use_global_settings",
                snmp["use_global_settings"],
                provenance.get("snmp.use_global_settings", "blueprint"),
            )
        if "configuration" in snmp:
            source = provenance.get("snmp.configuration", provenance.get("snmp.configuration.id", "blueprint"))
            put("snmp.configuration", gateway.resolve_snmp(snmp["configuration"]), source)
    for name, value in resolved.custom_settings.items():
        put(f"custom_settings.{name}", value, provenance.get(f"custom_settings.{name}", "blueprint"))
    for name, value in (config.metadata or {}).items():
        put(f"metadata.{name}", value, provenance.get(f"metadata.{name}", "blueprint"))
    return desired


def _alt_with_auth(entry: AlternativeAddress) -> dict[str, Any]:
    assert entry.credentials is not None
    return {
        "address": entry.address,
        "authentication": {"user": entry.credentials.username, "password": entry.credentials.password},
    }


def _check_conflicts(
    gateway: InventoryGateway,
    device: ProvisioningDevice,
    desired: dict[str, DesiredValue],
    changes: list[FieldChange],
    *,
    own_id: str | None,
) -> None:
    """Label/address collisions with *other* records for values that are being set or changed."""
    changed = {change.field for change in changes}
    conflicts: list[str] = []
    if "label" in changed:
        others = [i for i in gateway.ids_with_label(desired["label"].value) if i != own_id]
        if others:
            conflicts.append(f"label '{desired['label'].value}' is used by {', '.join(others)}")
    addresses: list[str] = []
    if "address" in changed:
        addresses.append(desired["address"].value)
    if "alt_addresses" in changed:
        addresses.extend(desired["alt_addresses"].value)
    found = gateway.ids_by_addresses(addresses)
    for address in addresses:
        others = [i for i in found.get(address, []) if i != own_id]
        if others:
            conflicts.append(f"address '{address}' is used by {', '.join(others)}")
    if conflicts:
        hint = "" if own_id else " Bind the existing record explicitly with 'inventory_id' if it is the same device."
        raise ProvisioningTargetError(f"Inventory conflict for '{device.key}': {'; '.join(conflicts)}.{hint}")


def _baseline(device: InventoryDevice, desired: dict[str, DesiredValue]) -> dict[str, str]:
    """Fingerprints of the managed non-secret values (masked secrets carry no information) and driver."""
    baseline = {key: _digest(get_field(device, key)) for key in desired if not is_sensitive(key)}
    baseline["driver_id"] = _digest(device.driver_id)
    return baseline


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_plain(value), sort_keys=True, default=str).encode()).hexdigest()


def _field_change(key: str, before: Any, item: DesiredValue) -> FieldChange:
    sensitive = is_sensitive(key)
    return FieldChange(
        field=key,
        before=_redact(key, before) if sensitive else _plain(before),
        after=_redact(key, item.value) if sensitive else _plain(item.value),
        source=item.source,
        sensitive=sensitive,
    )


def _redact(key: str, value: Any) -> Any:
    if value is None or value == "":
        return value
    if key == "alt_addresses_with_auth" and isinstance(value, list):
        return [
            {"address": entry.get("address"), "authentication": REDACTED} for entry in value if isinstance(entry, dict)
        ]
    return REDACTED


def _plain(value: Any) -> Any:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, BaseModel):
        return _plain(value.model_dump(mode="json"))
    return value


def _as_list(found: Any) -> list[str]:
    if found is None:
        return []
    return [found] if isinstance(found, str) else list(found)


def _auth(device: InventoryDevice) -> Auth:
    cinfo = device.configuration.config.cinfo
    if cinfo.auth is None:
        cinfo.auth = Auth()
    return cinfo.auth


def _set_password(device: InventoryDevice, value: Any) -> None:
    _auth(device).password = value.get_secret_value() if isinstance(value, SecretStr) else value


def _set_alt_with_auth(device: InventoryDevice, value: list[dict[str, Any]]) -> None:
    device.configuration.config.cinfo.altAddressesWithAuth = _plain(value)


def _accessor(key: str) -> tuple[Callable[[InventoryDevice], Any], Callable[[InventoryDevice, Any], None]]:
    fixed = _ACCESSORS.get(key)
    if fixed is not None:
        return fixed
    prefix, _, name = key.partition(".")
    if prefix == "custom_settings":
        return (
            lambda d: getattr(d.configuration.config.customSettings, name, None),
            lambda d, v: setattr(d.configuration.config.customSettings, name, v),
        )
    if prefix == "metadata":
        return (lambda d: d.configuration.meta.get(name), lambda d, v: d.configuration.meta.__setitem__(name, v))
    raise KeyError(f"Unsupported managed Inventory field '{key}'.")


def _cinfo(device: InventoryDevice) -> Any:
    return device.configuration.config.cinfo


_ACCESSORS: dict[str, tuple[Callable[[InventoryDevice], Any], Callable[[InventoryDevice, Any], None]]] = {
    "label": (
        lambda d: d.configuration.config.desc.label,
        lambda d, v: setattr(d.configuration.config.desc, "label", v),
    ),
    "description": (
        lambda d: d.configuration.config.desc.desc,
        lambda d, v: setattr(d.configuration.config.desc, "desc", v),
    ),
    "active": (lambda d: d.configuration.active, lambda d, v: setattr(d.configuration, "active", v)),
    "address": (lambda d: _cinfo(d).address, lambda d, v: setattr(_cinfo(d), "address", v)),
    "alt_addresses": (lambda d: list(_cinfo(d).altAddresses), lambda d, v: setattr(_cinfo(d), "altAddresses", list(v))),
    "alt_addresses_with_auth": (lambda d: list(_cinfo(d).altAddressesWithAuth), _set_alt_with_auth),
    "credentials.username": (
        lambda d: _cinfo(d).auth.user if _cinfo(d).auth is not None else None,
        lambda d, v: setattr(_auth(d), "user", v),
    ),
    "credentials.password": (lambda d: _cinfo(d).auth.password if _cinfo(d).auth is not None else None, _set_password),
    "generic.enable_https": (lambda d: _cinfo(d).http.https, lambda d, v: setattr(_cinfo(d).http, "https", v)),
    "generic.trust_all_certificates": (
        lambda d: _cinfo(d).http.trustAllCertificates,
        lambda d, v: setattr(_cinfo(d).http, "trustAllCertificates", v),
    ),
    "generic.http_auth": (lambda d: _cinfo(d).http.httpAuth, lambda d, v: setattr(_cinfo(d).http, "httpAuth", v)),
    "snmp.use_global_settings": (
        lambda d: d.configuration.cinfoOverrides.snmp.useDefault,
        lambda d, v: setattr(d.configuration.cinfoOverrides.snmp, "useDefault", v),
    ),
    "snmp.configuration": (
        lambda d: d.configuration.cinfoOverrides.snmp.id,
        lambda d, v: setattr(d.configuration.cinfoOverrides.snmp, "id", v),
    ),
}


__all__ = [
    "InventoryGateway",
    "InventoryWork",
    "build_candidate",
    "check_baseline",
    "get_field",
    "is_sensitive",
    "new_device",
    "plan_inventory",
    "recheck_conflicts",
    "set_field",
    "values_equal",
    "verify",
]
