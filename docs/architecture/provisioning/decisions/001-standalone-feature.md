# ADR-001: Standalone feature, not a VideoIPathApp property

> Status: **Accepted**

## Context

Inventory, topology, preferences, profile, and security are properties of
`VideoIPathApp`. Provisioning sits on top of Inventory and Inspect and is optional
for callers who configure devices directly through the SDK apps.

## Options

- Add `app.provisioning`, initialized lazily like the other apps.
- Keep a separate `ProvisioningEngine` that receives an app.

## Decision

The feature is a separate package object. `VideoIPathApp` neither imports nor
exposes it. Callers write `ProvisioningEngine(app)`.

The engine depends on a `ProvisioningApp` protocol with `inventory` and `inspect`
properties. Any object with those properties can be passed in. Construction
does not read the app or open a connection.

Processor registrations, `ApplyOptions`, and naming defaults live on the engine
instance. Two engines may share one app and still keep separate registries.
There is no process-global processor map.

## Consequences

- The rest of the package can be imported and released without pulling provisioning
  call sites into `VideoIPathApp`.
- Tests can pass a small fake that satisfies the protocol.
- Discoverability is worse than `app.provisioning`. The getting-started page and
  this record are the entry points.
- Sharing an app across engines does not serialize writes. Callers who apply
  concurrently against one server have to coordinate themselves.
