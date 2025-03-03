# Topology App

## 1. Basic Usage

### 1.1. Retrieve the configuration of a device in the Topology

Analogous to the Inventory-App, the Topology-App provides a method to retrieve the configuration of an existing device. If the device does not exist in the topology, but is available for synchronization, it will be generated from driver.

```python
device_topology = app.topology.get_device(device_id="device10")
print(device_topology.configuration.factory_label)
# > BORDERLEAF-26B [10.0.1.26][Arista Networks EOS]
```

### 1.2. Update a Device in the Topology

You can update the configuration of a device in the topology. If the device does not exist, it will be added to the topology.

```python
device_topology.configuration.label = "New Label"
device_topology.configuration.position_x = 100
device_topology.configuration.position_y = 200
device_topology.configuration.icon_size = "large"
device_topology.configuration.icon_type = "ipSwitchRouter"

updated_device = app.topology.update_device(device_topology)
print(updated_device.configuration.label)
# > New Label
```

### 1.3. Remove a Device from the Topology

You can remove a device from the topology by its device ID.

```python
last_config = app.topology.remove_device_by_id(device_id="device10")
```
