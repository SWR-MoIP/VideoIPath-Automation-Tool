# Example 2: Multicast Pools

## Code Example 1: Querying Multicast Pools from VideoIPath-Server

```python
pools = app.preferences.get_multicast_pools()
print("Names of the pools:")
print(pools.available_pools)  # Lists the names of the pools
print("\nPool object with the name 'A':")
print(pools.get_pool_by_name("A"))  # Returns the pool object with the name "A"
```


## Code Example 2: Create a new Multicast Pool

```python
b_pool_staged = app.preferences.create_local_multicast_pool("B", start_ip="234.0.0.0", end_ip="234.255.255.254")
print(app.preferences.add_multicast_pool(b_pool_staged))
```


## Code Example 3: Extend a pool with a range

```python
b_pool = pools.get_pool_by_name("B")
b_pool.add_range(start_ip="236.0.0.1", end_ip="236.0.0.2")
print(app.preferences.update_multicast_pool(b_pool))
```


# Code Example 4: Remove a range from a pool

```python
b_pool = pools.get_pool_by_name("B")
print(f"\nBefore Removal:\n{b_pool.ranges}")
b_pool.remove_range(1)
print(f"\nAfter Removal:\n{b_pool.ranges}")
print(app.preferences.update_multicast_pool(b_pool))
```


# Code Example 5: Delete a pool

```python
# Can be done either by pool name or the pool object itself
print(app.preferences.remove_multicast_pool("Test_Pool"))
```


# Code Example 6: Use Information to validate a vertex configuration

```python
# The implementation of Inspect-Topology allows to set invalid multicast pools :(
# => Tipp: Use Information to validate a vertex configuration

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import nPoolId
pool_list = app.preferences.get_multicast_pools().available_pools
print(f"Available Pools: {pool_list}")

topology_device = app.topology.get_device(device_id="device11")       # example SNP with invalid pool on "ProcA S1 P1 IP Output Audio 6"
for codec_vertex in topology_device.configuration.codec_vertices:
    if type(codec_vertex.mainDstIp) == nPoolId: # <= Pool is used for mainDstIp (Connection Defaults-> Multicast Address -> poolId)
        if codec_vertex.mainDstIp.poolId not in pool_list:
            print(f"Vertex {codec_vertex.id} has invalid multicast MAIN Pool! {codec_vertex.mainDstIp}")
            # e.g. Vertex device11.1.206S has invalid multicast MAIN Pool! type='nPoolId' poolId='C'
    if type(codec_vertex.spareDstIp) == nPoolId:
        if codec_vertex.spareDstIp.poolId not in pool_list:
            print(f"Vertex {codec_vertex.id} has invalid multicast SPARE Pool! {codec_vertex.spareDstIp}")
```
