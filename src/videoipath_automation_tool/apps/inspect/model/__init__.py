from __future__ import annotations

from videoipath_automation_tool.apps.inspect.model import (
    actions,
    alarms,
    collector,
    common,
    ngraph,
    tags,
    update_topology,
    virtual,
)
from videoipath_automation_tool.apps.inspect.model.actions import *
from videoipath_automation_tool.apps.inspect.model.alarms import *
from videoipath_automation_tool.apps.inspect.model.collector import *
from videoipath_automation_tool.apps.inspect.model.common import *
from videoipath_automation_tool.apps.inspect.model.ngraph import *
from videoipath_automation_tool.apps.inspect.model.tags import *
from videoipath_automation_tool.apps.inspect.model.update_topology import *
from videoipath_automation_tool.apps.inspect.model.virtual import *

__all__ = [
    *actions.__all__,
    *alarms.__all__,
    *collector.__all__,
    *common.__all__,
    *ngraph.__all__,
    *tags.__all__,
    *update_topology.__all__,
    *virtual.__all__,
]
