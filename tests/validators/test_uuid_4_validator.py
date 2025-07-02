import uuid

import pytest

from videoipath_automation_tool.validators.uuid_4 import validate_uuid_4


class TestValidateUUID4:
    @pytest.mark.parametrize(
        "uuid_str",
        [
            str(uuid.uuid4()),  # random, valid UUIDv4
            "550e8400-e29b-41d4-a716-446655440000",  # valid v4-UUID
            "00000000-0000-4000-8000-000000000000",  # minimal v4-UUID
            "ffffffff-ffff-4fff-bfff-ffffffffffff",  # maximal v4-UUID
            "550e8400e29b41d4a716446655440000",  # valid, no dashes
            "550E8400-E29B-41D4-A716-446655440000",  # valid, uppercase
        ],
    )
    def test_valid_uuid_4(self, uuid_str):
        normalized = validate_uuid_4(uuid_str)
        assert isinstance(normalized, str)
        # Standardize to lowercase with dashes
        assert uuid.UUID(normalized).version == 4

    @pytest.mark.parametrize(
        "uuid_str",
        [
            "550e8400-e29b-11d4-a716-446655440000",  # v1 instead of v4
            "550e8400-e29b-21d4-a716-446655440000",  # v2 instead of v4
            "550e8400-e29b-51d4-a716-446655440000",  # v5
            "this-is-not-a-uuid",
            "12345678-1234-1234-1234-1234567890ab",
            "zzzzzzzz-zzzz-4zzz-8zzz-zzzzzzzzzzzz",
            "",
            None,
            1234,
            [],
            {},
            object(),
        ],
    )
    def test_invalid_uuid_4(self, uuid_str):
        with pytest.raises(ValueError):
            validate_uuid_4(uuid_str)
