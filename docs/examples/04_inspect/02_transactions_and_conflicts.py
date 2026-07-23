"""Batch changes with transactions and handle concurrent edits.

Description
-----------
A transaction stages several changes and commits them atomically — either all apply or none do. This
example batches a device edit, a vertex edit, and a new connection into one commit, then shows how to
handle a concurrent modification: the commit detects it, raises ``InspectCommitConflictError``, and you
``rebase`` onto fresh server state and retry.

The recommended way to stage domain-object edits into a transaction is ``tx.update(objects)``;
the keyword-style ``tx.update_device(...)`` is shown as an alternative.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.
- Devices ``leaf-1`` and ``spine-1`` in the topology with synced ports.

Related examples
----------------
- 03_topology_and_inspect/03_connect_devices_with_edges_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.apps.inspect import InspectCommitConflictError, InspectCommitError

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

MAX_RETRIES = 3


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    leaf = app.inspect.find_device_by_label("leaf-1")
    spine = app.inspect.find_device_by_label("spine-1")
    assert leaf is not None and spine is not None

    leaf_out = next((p.vertex_out for p in leaf.ports if p.vertex_out), None)
    spine_in = next((p.vertex_in for p in spine.ports if p.vertex_in), None)
    assert leaf_out is not None and spine_in is not None

    # --- 2. Stage several changes and commit them atomically ------------------
    leaf.description = "Rack A leaf"
    leaf_out.use_as_endpoint = True
    try:
        with app.inspect.transaction() as tx:
            tx.update([leaf, leaf_out])  # stage setter edits into the transaction
            tx.connect(leaf_out.id, spine_in.id, bidirectional=True)  # edge creation (no setter form)
            result = tx.commit()
        print("Committed:", result.applied_ids)
        # > Committed: ['device34', 'device34.1.0', ...]
    except InspectCommitError as error:
        # The server rejected the commit (validation / apply gate) — nothing was written.
        print("Server rejected the commit:", error)
        return

    # Alternative keyword style for the same device edit:
    #     tx.update_device(leaf.id, description="Rack A leaf")

    # --- 3. Handle a concurrent modification with rebase + retry --------------
    # Stage the edit once, then retry the commit; rebase re-fetches baselines and keeps our intent.
    leaf.description = "Rack A leaf (updated)"
    tx = app.inspect.transaction()
    tx.update(leaf)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tx.commit()
            print("Committed on attempt", attempt)
            # > Committed on attempt 1
            break
        except InspectCommitConflictError as conflict:
            # Someone changed leaf-1 since we staged it.
            print(f"Conflict on {[c.entity_id for c in conflict.conflicts]}; rebasing.")
            tx.rebase()
    else:
        print("Gave up after", MAX_RETRIES, "attempts.")
        tx.discard()


if __name__ == "__main__":
    main()
