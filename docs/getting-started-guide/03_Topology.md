# Topology App

## 1. Introduction

The Topology App focuses on configuring devices, defining their capabilities, and establishing links between them. For all these purposes, instances of "Topology Device" are used.

A **Topology Device** represents a network entity within the topology, containing configuration details. It is composed of multiple elements, each serving a specific role:  

- **Base Device (BaseDevice)**: Stores fundamental properties such as labels, descriptions, and appearance settings.  
- **Vertices**:  
  - **Generic Vertices (GenericVertex)**: Primarily represent switching cores.  
  - **IP Vertices (IpVertex)**: Represent network interfaces.  
  - **Codec Vertices (CodecVertex)**: Represent media-specific inputs and outputs.  
- **Edges**:  
  - **Internal Edges**: Connect vertices within the same device.  
  - **External Edges**: Link the device to other devices in the topology.  

All device properties are stored within the configuration attribute of a **Topology Device**.  
While the **Base Device** exists as a single instance and can be accessed directly, all **Vertices** and **Edges** are stored in lists within configuration, categorized by their type.
The following examples illustrate how to retrieve, modify and update specific properties of a **Topology Device**.

## 2. Basic Usage

### 2.1. Retrieving the Configuration of a Device in the Topology

The configuration of a device that has already been added to the topology or is ready for synchronization can be retrieved using its unique device ID.

```python
device = app.topology.get_device(device_id="device10")
print(device.configuration.factory_label)
# > BORDERLEAF-26B [10.0.1.26][Arista Networks EOS]
```

Alternatively, a device can be identified by determining its device ID based on its label.  

Similar to the Inventory app, multiple label_search_mode options are available, with canonical_label set as the default.  
In this mode, devices that have not yet been added but are ready for synchronization are matched using the factory label.  
For devices already configured in the topology, the displayed label is used—either the user-defined label, if set, or otherwise the factory label.  

```python
device_id = app.topology.find_device_id_by_label("BORDERLEAF-26B [10.0.1.26][Arista Networks EOS]", label_search_mode="canonical_label")

if device_id is None:
    raise ValueError("Device not found")
if isinstance(device_id, list):
    raise ValueError(f"Multiple devices found: {device_id}")


print(device_id)
# > device10
```

### 2.2. Updating a Device in the Topology

The configuration of a device in the topology can be updated. If the device does not exist, it is automatically added to the topology.

```python
device.configuration.label = "New Label"
device.configuration.position_x = 100
device.configuration.position_y = 200
device.configuration.icon_size = "large"
device.configuration.icon_type = "ipSwitchRouter"

updated_device = app.topology.update_device(device)
print(updated_device.configuration.label)
# > New Label
```

The method evaluates which `nGraphElements` have changed compared to the server state and updates only those elements. Additionally, by default, it checks whether any services are affected. This behavior can be bypassed by setting `ignore_affected_services` to `True`.

### 2.3. Remove a Device from the Topology

A device can be removed from the topology using its device ID.

```python
app.topology.remove_device_by_id(device_id="device10")
```

## 3. Working with Vertices and Edges

It is possible to either iterate through all vertices/edges of a category, which is often useful for bulk operations, or access individual vertices/edges directly by their ID or label.

### 3.1 Iterate through all Edges/Vertices of a Category

```python

device = app.topology.get_device(device_id="device80")

codec_vertices = device.configuration.codec_vertices

for codec_vertex in codec_vertices:
    print(codec_vertex.factory_label)
    # > SDI Out 1.1A [SDI Out 1.1A]
    #   SDI Out 1.1B [SDI Out 1.1B]
    #   SDI Out 1.2A [SDI Out 1.2A]
    #   SDI Out 1.2B [SDI Out 1.2B]
    #   Video-IP In 1.1
    #   Video-IP In 1.2
    #   ...
```

### 3.2 Access a Edge/Vertex by its ID

```python
vertice_video_ip_in_1_1 = device.configuration.get_nGraphElement_by_id("device80.1.3000000")

if vertice_video_ip_in_1_1 is None:
    raise Exception("Vertex not found")

print(vertice_video_ip_in_1_1.factory_label)
# > Video-IP In 1.1
```

### 3.3 Access a Vertex by its Label

```python
vertice_video_ip_in_1_1 = device.configuration.get_vertex_by_label("Video-IP In 1.1", label_type="factory")

if vertice_video_ip_in_1_1 is None:
    raise Exception("Vertex not found")

print(vertice_video_ip_in_1_1.id)
# > device80.1.3000000
```

### 3.4. Example: Configure existing Edges/Vertices

#### 3.4.1. Configure Codec Vertices based on information from factory labels

```python
device = app.topology.get_device(device_id="device80")

codec_vertices = device.configuration.codec_vertices

for vertex in codec_vertices:
    if vertex.factory_label.startswith("Video-IP In"):
        direction = "RX"
        codec_format = "Video"
    elif vertex.factory_label.startswith("Video-IP Out"):
        direction = "TX"
        codec_format = "Video"
    elif vertex.factory_label.startswith("Audio-IP In"):
        direction = "RX"
        codec_format = "Audio"
    elif vertex.factory_label.startswith("Audio-IP Out"):
        direction = "TX"
        codec_format = "Audio"
    else:
        continue

    # Generic Settings
    vertex.use_as_endpoint = True
    vertex.sips_mode = "SIPSAuto"
    vertex.sdp_support = True

    if codec_format == "Video":
        vertex.tags = ["V_1080i25", "V_1080p50", "V_2160p50"]
    elif codec_format == "Audio":
        vertex.tags = ["A_2CH_LR", "A_6CH_5.1", "A_8CH_RAW"]

    # TX Settings
    if direction == "TX":
        vertex.main_destination_address_pool = "MAIN_POOL"
        vertex.spare_destination_address_pool = "SPARE_POOL"

    print(
        f"Vertex with id '{vertex.id}‘ and label '{vertex.factory_label}' configured for {codec_format} ({direction}). Tags: {', '.join(vertex.tags)}"
    )
    # > Vertex with id 'device80.1.3000000‘ and label 'Video-IP In 1.1' configured for Video (RX). Tags: V_1080i25, V_1080p50, V_2160p50
    #   Vertex with id 'device80.1.3000001‘ and label 'Video-IP In 1.2' configured for Video (RX). Tags: V_1080i25, V_1080p50, V_2160p50
    #   ...
    
app.topology.update_device(device=device)
```

More examples will be added soon!

---

### 3.5. Creating external Edges between devices

```python
virtuoso_device_id = "device80"
spine_red_device_id = "device0"
spine_blue_device_id = "device1"

# Edges / Slot 1
edges_red_slot_1 = app.topology.create_edges(
    device_1_id=virtuoso_device_id,
    device_1_vertex_factory_label="Ethernet 1.3",
    device_2_id=spine_red_device_id,
    device_2_vertex_factory_label="Ethernet29",
    bandwidth=10000,
    bandwidth_factor=0.9,
    redundancy_mode="OnlyMain",
)
edges_blue_slot_1 = app.topology.create_edges(
    device_1_id=virtuoso_device_id,
    device_1_vertex_factory_label="Ethernet 1.4",
    device_2_id=spine_blue_device_id,
    device_2_vertex_factory_label="Ethernet29",
    bandwidth=10000,
    bandwidth_factor=0.9,
    redundancy_mode="OnlySpare",
)
# ... Slot 2, Slot 3, ...


virtuoso_topology = app.topology.get_device(device_id=virtuoso_device_id)

# Remove all existing external edges and add the new ones
virtuoso_topology.configuration.external_edges = []
virtuoso_topology.configuration.external_edges.extend(edges_red_slot_1)
virtuoso_topology.configuration.external_edges.extend(edges_blue_slot_1)
# ... Slot 2, Slot 3, ...

# Update the device in the topology
app.topology.update_device(device=virtuoso_topology)
```

> **Note:** The documentation is currently being expanded. Upcoming sections will include details on device positioning, virtual device management, and device comparison, as well as synchronization status and various helper functions.
