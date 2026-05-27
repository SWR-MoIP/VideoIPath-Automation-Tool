import logging

from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class InspectCollectorAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: logging.Logger):
        self.vip_connector = vip_connector
        self._logger = logger
