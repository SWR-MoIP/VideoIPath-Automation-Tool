import logging
from unittest.mock import patch

import pytest

from videoipath_automation_tool.apps.inspect.utils.rest_paths import (
    COLLECTOR_LOOKUP_INSPECT_DEVICE,
    COLLECTOR_LOOKUP_SYNC_INFO,
    COLLECTOR_UPDATE_TOPOLOGY,
    NETWORK_ADD_DEVICES,
    NETWORK_SYNC_DEVICES,
)
from videoipath_automation_tool.connector.vip_base_connector import VideoIPathBaseConnectorTimeouts
from videoipath_automation_tool.connector.vip_rest_connector import VideoIPathRestConnector

# Legacy Topology App — not in rest_paths:
TOPOLOGY_VALIDATE_TOPOLOGY_UPDATE = "/rest/v2/actions/status/pathman/validateTopologyUpdate"


@pytest.fixture
def rest_connector():
    with patch.object(VideoIPathRestConnector, "is_connected", return_value=True):
        with patch.object(VideoIPathRestConnector, "is_authenticated", return_value=True):
            yield VideoIPathRestConnector(
                server_address="127.0.0.1",
                username="api",
                password="secret",
                logger=logging.getLogger("test_connector_urls"),
                timeouts=VideoIPathBaseConnectorTimeouts(),
                use_https=False,
                verify_ssl_cert=False,
            )


def test_topology_validate_topology_update_allowed(rest_connector):
    rest_connector._validate_url(TOPOLOGY_VALIDATE_TOPOLOGY_UPDATE, "POST")


def test_network_sync_devices_url_allowed(rest_connector):
    rest_connector._validate_url(NETWORK_SYNC_DEVICES, "POST")


def test_network_add_devices_url_allowed(rest_connector):
    rest_connector._validate_url(NETWORK_ADD_DEVICES, "POST")


def test_collector_lookup_inspect_device_url_allowed(rest_connector):
    rest_connector._validate_url(COLLECTOR_LOOKUP_INSPECT_DEVICE, "POST")


def test_collector_lookup_sync_info_url_allowed(rest_connector):
    rest_connector._validate_url(COLLECTOR_LOOKUP_SYNC_INFO, "POST")


def test_collector_update_topology_url_allowed(rest_connector):
    rest_connector._validate_url(COLLECTOR_UPDATE_TOPOLOGY, "POST")


def test_invalid_post_url_rejected(rest_connector):
    with pytest.raises(ValueError, match="Invalid URL path"):
        rest_connector._validate_url("/rest/v2/actions/unknown/syncDevices", "POST")
