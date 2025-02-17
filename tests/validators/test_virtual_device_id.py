import pytest

from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


class TestValidateVirtualDeviceId:
    @pytest.mark.parametrize(
        "virtual_device_id", ["virtual.0", "virtual.1", "virtual.123", "virtual.1000", "virtual.123456789"]
    )
    def test_valid_virtual_device_id(self, virtual_device_id: str):
        assert validate_virtual_device_id(virtual_device_id) == virtual_device_id

    @pytest.mark.parametrize(
        "virtual_device_id",
        [
            "virtual",
            "virtuala",
            "virtual1a",
            "virtual-1",
            "virtual00",
            "virtual01",
            "virtual 1",
            "virtual1 ",
            "virtual 1 ",
            " virtual1",
            "virtual1.1",
            None,
            [],
            {},
            "Virtual1",
            0,
            1,
            "",
        ],
    )
    def test_invalid_virtual_device_id(self, virtual_device_id: str):
        with pytest.raises(ValueError):
            validate_virtual_device_id(virtual_device_id)
