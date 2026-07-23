# Getting Started Guide

This guide will help you get started with the VideoIPath Automation Tool. It will
show you how to establish a connection to the VideoIPath server and how to manage
devices in the inventory and topology. Stage 3 covers topology work twice — once
with the classic Topology app and once with the modern Inspect app — so you can
follow the same workflows with either implementation. It also demonstrates how to
configure multicast pools.

## Compatibility (Topology vs Inspect)

| App | API | Compatibility |
|---|---|---|
| **Inspect** (`app.inspect`) | Forward-looking read/write topology interface | Requires **VideoIPath 2025.4 or newer** (recommended) |
| **Topology** (`app.topology`) | Classic topology interface | **Deprecated on 2025.x**; **unsupported on 2026.x** (`TopologyUnsupportedError`) |

Prefer the Inspect variant ([03-B](03_B_Inspect.md)) on modern servers. Inventory
onboarding is unchanged and remains a prerequisite for both.

## Table of Contents

1. [Establishing a Connection to the VideoIPath Server](01_Setup_and_connect_to_Server.md)
2. [Managing Devices in the Inventory](02_Inventory.md)
3. Managing Devices in the Topology — choose an implementation:
   - A. [Topology App](03_A_Topology.md) (classic / legacy)
   - B. [Inspect App](03_B_Inspect.md) (recommended on 2025.4+)
4. [Configuring Multicast Pools](04_Multicast_Pools.md)

For runnable, task-oriented scripts covering realistic automation scenarios
(including paired Topology/Inspect examples), see the
[Examples](../examples/README.md).
