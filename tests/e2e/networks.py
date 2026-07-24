"""Declarative network definitions for the generic e2e network-builder suite.

A :class:`Network` is a small, readable description of an architecture — named devices with a grid
position, plus the links between them. The builder suite in ``workflows/test_build_networks.py``
turns any network into a live VideoIPath topology: it creates the devices in the inventory, adds
them to the Inspect topology at ``base position + offset``, labels and tags them, then connects the
links.

Define a new architecture by adding a ``Network`` here (via :func:`build_network`) and a three-line
``Test*`` subclass in the builder suite — each network then builds as its own ordered test suite at
its own map offset, so several networks can coexist on a shared instance without colliding.

Built networks stay in VideoIPath after the run. The next e2e session starts with a sweep that
removes every ``E2E-`` artifact before rebuilding.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceSpec:
    """A device in a network: a unique name, its router-port count, and a relative grid position."""

    name: str
    ports: int
    x: int
    y: int


@dataclass(frozen=True)
class LinkSpec:
    """A bidirectional link between two devices, referenced by their index in ``Network.devices``.

    Repeat a pair to model parallel links between the same two devices.
    """

    a: int
    b: int


@dataclass(frozen=True)
class Network:
    """A named architecture: the devices to build and the links to connect between them."""

    name: str
    devices: list[DeviceSpec]
    links: list[LinkSpec]

    def index_of(self, name: str) -> int:
        for i, device in enumerate(self.devices):
            if device.name == name:
                return i
        raise KeyError(f"Device '{name}' is not part of network '{self.name}'.")

    def neighbours(self) -> dict[str, set[str]]:
        """Undirected neighbour-name set per device (derived from the links)."""
        adjacency: dict[str, set[str]] = {device.name: set() for device in self.devices}
        for link in self.links:
            a, b = self.devices[link.a].name, self.devices[link.b].name
            adjacency[a].add(b)
            adjacency[b].add(a)
        return adjacency

    def parallel_count(self, link: LinkSpec) -> int:
        """How many links connect the same device pair as ``link`` (1 unless there are parallels)."""
        return sum(1 for other in self.links if {other.a, other.b} == {link.a, link.b})


def build_network(
    name: str,
    *,
    devices: list[tuple[str, int, int]],
    links: list[tuple[str, str]],
) -> Network:
    """Build a :class:`Network` from readable ``(name, x, y)`` devices and ``(name_a, name_b)`` links.

    Each device's router-port count is sized automatically to its link degree (repeat a link pair to
    add a parallel link, which also grows the port count), so definitions stay declarative and
    self-consistent.
    """
    index = {device_name: i for i, (device_name, _, _) in enumerate(devices)}
    degree: dict[str, int] = defaultdict(int)
    for a, b in links:
        degree[a] += 1
        degree[b] += 1
    device_specs = [DeviceSpec(name=n, ports=max(1, degree[n]), x=x, y=y) for n, x, y in devices]
    link_specs = [LinkSpec(a=index[a], b=index[b]) for a, b in links]
    return Network(name=name, devices=device_specs, links=link_specs)
