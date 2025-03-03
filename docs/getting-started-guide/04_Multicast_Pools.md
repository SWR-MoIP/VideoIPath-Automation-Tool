# System Preferences: Multicast Pools

## Tipp: Define a variable for the allocation_pools_config for easier access

```python
allocation_pools_config = app.preferences.system_configuration.allocation_pools
```

## Code Example 1: Querying Multicast Pools from VideoIPath-Server

```python
mc_ranges = allocation_pools_config.get_multicast_ranges()

print("Names of the Ranges:")
print(mc_ranges.available_ranges, "\n")  # Lists the names of the ranges

print("Range object with the name 'A':")
print(mc_ranges.get_range_by_name("A"))  # Returns the range object with the name "A"
```

### Example Output

```console
Names of the Ranges:
['A', 'B', 'default'] 

Range object with the name 'A':
id='A' vid='A' ranges=[Range(startip=IPv4Address('233.0.0.0'), endip=IPv4Address('233.255.255.255'))] utilization=Utilization(percentage=0, total=16777216, used=1)
```

## Code Example 2: Create a new Multicast Pool

```python
staged_b_range = allocation_pools_config.create_multicast_range(
    name="B", start_ip="234.0.0.0", end_ip="234.255.255.254"
)

allocation_pools_config.add_multicast_range(staged_b_range)
```

## Code Example 3: Extend a pool with a range

```python
b_range = allocation_pools_config.get_multicast_range_by_name("B")
b_range.add_ip_range(start_ip="236.0.0.1", end_ip="236.0.0.2")
print(allocation_pools_config.update_multicast_range(b_range))
print(b_range)
```

### Example Output

```console
available_ranges=['A', 'B', 'default']
id='B' vid='B' ranges=[Range(startip=IPv4Address('234.0.0.0'), endip=IPv4Address('234.255.255.254')), Range(startip=IPv4Address('236.0.0.1'), endip=IPv4Address('236.0.0.2'))] utilization=Utilization(percentage=0, total=16777215, used=0)
```

# Code Example 4: Remove a range from a pool

```python
b_range = allocation_pools_config.get_multicast_range_by_name("B")
print(f"\nBefore Removal:\n{b_range.ranges}")
b_range.remove_range(1)
print(f"\nAfter Removal:\n{b_range.ranges}")
print(allocation_pools_config.update_multicast_range(b_range))
```

### Example Output

```console
Before Removal:
[Range(startip=IPv4Address('234.0.0.0'), endip=IPv4Address('234.255.255.254')), Range(startip=IPv4Address('236.0.0.1'), endip=IPv4Address('236.0.0.2'))]

After Removal:
[Range(startip=IPv4Address('234.0.0.0'), endip=IPv4Address('234.255.255.254'))]
available_ranges=['A', 'B', 'default']
```

# Code Example 5: Delete a pool

```python
# Can be done either by range name or the range object itself
allocation_pools_config.remove_multicast_range("B")
```

# Code Example 6: Use Information to validate a vertex configuration

```python
# The implementation of Inspect-Topology GUI allows to set invalid multicast pools.
# => Tipp: Use Information to validate a vertex configuration
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import nPoolId

allocation_pools_config = app.preferences.system_configuration.allocation_pools
mc_pools_list = allocation_pools_config.get_multicast_ranges().available_ranges

print(f"Available Pools: {mc_pools_list}")

topology_device = app.topology.get_device(
    device_id="device11"
)  # example SNP with invalid pool on "ProcA S1 P1 IP Output Audio 6"
for codec_vertex in topology_device.configuration.codec_vertices:
    if (
        type(codec_vertex.mainDstIp) == nPoolId
    ):  # <= Pool is used for mainDstIp (Connection Defaults-> Multicast Address -> poolId)
        if codec_vertex.mainDstIp.poolId not in mc_pools_list:
            print(f"Vertex {codec_vertex.id} has invalid multicast MAIN Pool! {codec_vertex.mainDstIp}")
            # e.g. Vertex device11.1.206S has invalid multicast MAIN Pool! type='nPoolId' poolId='C'
    if type(codec_vertex.spareDstIp) == nPoolId:
        if codec_vertex.spareDstIp.poolId not in mc_pools_list:
            print(f"Vertex {codec_vertex.id} has invalid multicast SPARE Pool! {codec_vertex.spareDstIp}")
```

### Example Output

```console
Vertex device11.1.206S has invalid multicast MAIN Pool! type='nPoolId' poolId='C'
```
