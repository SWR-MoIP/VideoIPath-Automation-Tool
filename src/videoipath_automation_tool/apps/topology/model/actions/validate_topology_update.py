from typing import List

from pydantic import BaseModel, Field

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import NGraphElement


class ValidateTopologyUpdateData(BaseModel):
    """
    Class for the data field of the RequestRestV2Post object for validating topology updates:
    /rest/v2/actions/status/pathman/validateTopologyUpdate
    """

    added: dict = Field(default_factory=dict)
    removed: list = Field(default_factory=list)

    def added_elements(self, element_list: List[NGraphElement]):
        for element in element_list:
            self.added[element.id] = element.model_dump(mode="json", by_alias=True)
        return self

    def removed_elements(self, element_list: List[NGraphElement]):
        for element in element_list:
            self.removed.append(element.id)
        return self
