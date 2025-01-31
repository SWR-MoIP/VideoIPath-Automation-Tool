# Example 3: Inventory

## Code Example 1: Connect to the VideoIPath API and retrieve the configuration of an inventory device
The first example illustrates how to utilize the VideoIPath Automation Tool to retrieve the configuration and status of an online device with the ID "device31". It provides access to attributes such as the device's label, IP address and the reachable status.

```python
# 2. Get the online device with device id "device31"
inventory_device = app.inventory.get_device(device_id="device31")

# 3. Print the label / ip of the device
print(inventory_device.label)   
print(inventory_device.address)   

# 4. Print the reachable status of the device
print(inventory_device.status.reachable)
```

#### Example 2: Connect to the VideoIPath API and add a new device to the inventory
The second example demonstrates how to use the VideoIPath Automation Tool to add a new device to the inventory. The new device is a NMOS_multidevice with the label "Hello Word" and the IP address "10.1.100.20".

```python
# 2. Create a new NMOS_multidevice
new_inventory_device = app.inventory.create_device(driver="com.nevion.NMOS_multidevice-0.1.0")
new_inventory_device.label = "Hello World"
new_inventory_device.address = "10.1.100.20"
new_inventory_device.custom.port = 5050

# 3. Add the new device to the inventory and retrieve the created device configuration
online_device = app.inventory.add_device(device=new_inventory_device)

print(f"Device '{online_device.label}' with id '{online_device.device_id}' address '{online_device.address}' and NMOS port '{online_device.custom.port}' created in Inventory!")
```