import pytest

from videoipath_automation_tool.validators.device_id import validate_device_id


class TestValidateDeviceId:
    @pytest.mark.parametrize("device_id", ["device0", "device1", "device123", "device1000", "device123456789"])
    def test_valid_device_id(self, device_id: str):
        assert validate_device_id(device_id) == device_id

    @pytest.mark.parametrize(
        "device_id",
        [
            "device",
            "devicea",
            "device1a",
            "device-1",
            "device00",
            "device01",
            "device 1",
            "device1 ",
            "device 1 ",
            " device1",
            "device1.1",
            None,
            [],
            {},
            "Device1",
            0,
            1,
            "",
        ],
    )
    def test_invalid_device_id(self, device_id: str):
        with pytest.raises(ValueError):
            validate_device_id(device_id)
