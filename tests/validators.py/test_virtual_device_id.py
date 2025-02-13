import unittest

from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


class TestValidateVirtualDeviceId(unittest.TestCase):
    def test_valid_virtual_device_id(self):
        self.assertEqual(validate_virtual_device_id("virtual.0"), "virtual.0")
        self.assertEqual(validate_virtual_device_id("virtual.1"), "virtual.1")
        self.assertEqual(validate_virtual_device_id("virtual.123"), "virtual.123")
        self.assertEqual(validate_virtual_device_id("virtual.1000"), "virtual.1000")
        self.assertEqual(validate_virtual_device_id("virtual.123456789"), "virtual.123456789")

    def test_invalid_virtual_device_id(self):
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.a")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.1a")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.-1")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.00")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.01")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual. 1")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.1 ")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual. 1 ")
        with self.assertRaises(ValueError):
            validate_virtual_device_id(" virtual.1")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.1.1")
        with self.assertRaises(ValueError):
            validate_virtual_device_id("virtual.99999999999999999999999999999999")
        with self.assertRaises(ValueError):
            validate_virtual_device_id(None)
        with self.assertRaises(ValueError):
            validate_virtual_device_id([])
        with self.assertRaises(ValueError):
            validate_virtual_device_id({})
        with self.assertRaises(ValueError):
            validate_virtual_device_id("Virtual.1")
        with self.assertRaises(ValueError):
            validate_virtual_device_id(0)
        with self.assertRaises(ValueError):
            validate_virtual_device_id(1)
        with self.assertRaises(ValueError):
            validate_virtual_device_id("")


if __name__ == "__main__":
    unittest.main()
