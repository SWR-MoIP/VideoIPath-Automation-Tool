"""InspectAPI wiring tests with a fake REST connector: verifies each method hits the right
endpoint, passes allow_projection for scoped reads, and parses responses into DTOs."""

from types import SimpleNamespace

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyData


class FakeRest:
    def __init__(self, get_data=None, post_data=None):
        self._get_data = get_data or {}
        self._post_data = post_data or {}
        self.get_calls = []
        self.post_calls = []

    def get(self, url_path, allow_projection=False, **kwargs):
        self.get_calls.append((url_path, allow_projection))
        return SimpleNamespace(data=self._get_data, header=_ok_header())

    def post(self, url_path, body, **kwargs):
        self.post_calls.append((url_path, body))
        return SimpleNamespace(data=self._post_data, header=_ok_header())


def _ok_header():
    return SimpleNamespace(
        model_dump=lambda mode="json": {
            "auth": True,
            "caption": "OK",
            "code": "OK",
            "errorCodes": [],
            "errorDetails": [],
            "id": "0",
            "msg": [],
            "ok": True,
            "user": "api-user",
        }
    )


def _connector(get_data=None, post_data=None):
    rest = FakeRest(get_data=get_data, post_data=post_data)
    return SimpleNamespace(rest=rest), rest


def _collector(node_items=None, edge_items=None, path_items=None):
    return {
        "status": {
            "collector": {
                "inspect": {
                    "nodeStatus": {"_items": node_items or []},
                    "paths": {"_items": path_items or []},
                },
                "externalEdgesByDeviceKey": {"_items": edge_items or []},
            }
        }
    }


def test_device_skeleton_uses_projection_and_parses(load):
    node_items = load("skeleton_nodestatus_short.json")["data"]["status"]["collector"]["inspect"]["nodeStatus"][
        "_items"
    ]
    conn, rest = _connector(get_data=_collector(node_items=node_items))
    api = InspectAPI(conn)
    devices = api.get_device_skeleton()
    assert len(devices) == len(node_items)
    assert rest.get_calls[0][1] is True  # allow_projection


def test_edge_skeleton_parses(load):
    edge_items = load("edge_skeleton.json")["data"]["status"]["collector"]["externalEdgesByDeviceKey"]["_items"]
    conn, rest = _connector(get_data=_collector(edge_items=edge_items))
    api = InspectAPI(conn)
    edges = api.get_edge_skeleton()
    assert len(edges) == len(edge_items)


def test_device_detail_returns_none_when_absent():
    conn, rest = _connector(get_data=_collector(node_items=[]))
    api = InspectAPI(conn)
    assert api.get_device_detail("deviceX") is None


def test_lookup_edges_hits_correct_endpoint(load):
    conn, rest = _connector(post_data=load("lookup_inspect_edges_by_ids.json")["data"])
    api = InspectAPI(conn)
    resp = api.lookup_edges(["a::b"])
    assert rest.post_calls[0][0].endswith("/lookupInspectEdgesByIds")
    assert resp.data


def test_update_topology_posts_delta():
    conn, rest = _connector(
        post_data={
            "items": [],
            "res": {"msg": [], "ok": True},
            "validation": {"details": {}, "result": {"msg": [], "ok": True}},
        }
    )
    api = InspectAPI(conn)
    resp = api.update_topology(InspectApiUpdateTopologyData())
    assert rest.post_calls[0][0].endswith("/updateTopology")
    assert resp.committed is True


def test_add_and_sync_devices_endpoints():
    conn, rest = _connector(post_data={"msg": [], "ok": True})
    api = InspectAPI(conn)
    api.add_devices([])
    api.sync_devices([], add_only=True, conflict_strategy=0)
    assert rest.post_calls[0][0].endswith("/network/addDevices")
    assert rest.post_calls[1][0].endswith("/network/syncDevices")
