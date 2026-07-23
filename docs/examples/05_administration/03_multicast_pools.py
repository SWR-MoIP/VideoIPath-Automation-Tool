"""Configure multicast allocation pools.

Description
-----------
Multicast allocation pools are the IP ranges VideoIPath draws from when assigning multicast addresses
to services. This example reads the existing pools and their utilization, creates a new pool, extends
it with an extra range, and removes it again.

Prerequisites
-------------
- A reachable VideoIPath server and credentials with system-configuration access.

Related examples
----------------
- 04_inspect/01_explore_topology_read_only.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

POOL_NAME = "pool-a"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    allocation_pools = app.preferences.system_configuration.allocation_pools

    # --- 2. Read existing pools and utilization -------------------------------
    ranges = allocation_pools.get_multicast_ranges()
    print("Pools:", ranges.available_ranges)
    # > Pools: ['default']
    for name in ranges.available_ranges:
        pool = allocation_pools.get_multicast_range_by_name(name)
        print(f"  {name}: {pool.utilization.percentage}% used")
        # >   default: 0% used

    # --- 3. Create a new pool -------------------------------------------------
    staged = allocation_pools.create_multicast_range(name=POOL_NAME, start_ip="239.0.10.0", end_ip="239.0.10.255")
    allocation_pools.add_multicast_range(staged)
    print("Created", POOL_NAME)
    # > Created pool-a

    # --- 4. Extend the pool with another range --------------------------------
    pool = allocation_pools.get_multicast_range_by_name(POOL_NAME)
    pool.add_ip_range(start_ip="239.0.11.0", end_ip="239.0.11.255")
    allocation_pools.update_multicast_range(pool)
    print(f"{POOL_NAME} now has {len(pool.ranges)} range(s).")
    # > pool-a now has 2 range(s).

    # --- 5. Remove the pool ---------------------------------------------------
    allocation_pools.remove_multicast_range(POOL_NAME)
    print("Removed", POOL_NAME)
    # > Removed pool-a


if __name__ == "__main__":
    main()
