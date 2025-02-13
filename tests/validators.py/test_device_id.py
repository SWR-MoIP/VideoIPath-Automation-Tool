import unittest

from videoipath_automation_tool.validators.device_id import validate_device_id


class TestValidateDeviceId(unittest.TestCase):
    def test_valid_device_id(self):
        self.assertEqual(validate_device_id("device0"), "device0")
        self.assertEqual(validate_device_id("device1"), "device1")
        self.assertEqual(validate_device_id("device123"), "device123")
        self.assertEqual(validate_device_id("device1000"), "device1000")
        self.assertEqual(validate_device_id("device123456789"), "device123456789")

    def test_invalid_device_id(self):
        with self.assertRaises(ValueError):
            validate_device_id("device")
        with self.assertRaises(ValueError):
            validate_device_id("devicea")
        with self.assertRaises(ValueError):
            validate_device_id("device1a")
        with self.assertRaises(ValueError):
            validate_device_id("device-1")
        with self.assertRaises(ValueError):
            validate_device_id("device00")
        with self.assertRaises(ValueError):
            validate_device_id("device01")
        with self.assertRaises(ValueError):
            validate_device_id("device 1")
        with self.assertRaises(ValueError):
            validate_device_id("device1 ")
        with self.assertRaises(ValueError):
            validate_device_id("device 1 ")
        with self.assertRaises(ValueError):
            validate_device_id(" device1")
        with self.assertRaises(ValueError):
            validate_device_id("device1.1")
        with self.assertRaises(ValueError):
            validate_device_id(None)
        with self.assertRaises(ValueError):
            validate_device_id([])
        with self.assertRaises(ValueError):
            validate_device_id({})
        with self.assertRaises(ValueError):
            validate_device_id("Device1")
        with self.assertRaises(ValueError):
            validate_device_id(0)
        with self.assertRaises(ValueError):
            validate_device_id(1)
        with self.assertRaises(ValueError):
            validate_device_id("")


if __name__ == "__main__":
    unittest.main()
