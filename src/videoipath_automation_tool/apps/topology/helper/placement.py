from logging import Logger
from typing import List, Literal

from videoipath_automation_tool.apps.topology.model.topology_device import TopologyDevice
from videoipath_automation_tool.apps.topology.topology_api import TopologyAPI


class TopologyPlacement:
    def __init__(self, topology_api: TopologyAPI, logger: Logger):
        self._topology_api = topology_api
        self._logger = logger
        self.line = TopologyPlacementLine(topology_api, logger)
        self.grid = TopologyPlacementGrid(topology_api, logger)

    # --- User Methods ---

    def get_all_device_positions(self) -> dict[str, dict[str, float]]:
        """
        Retrieves the x and y positions of all devices in the topology.

        Returns:
            dict[str, dict[str, float]]: A dictionary where each key is a device ID
            and each value is a dictionary containing 'x' and 'y' coordinates.
        Raises:
            ValueError: If the response from the server is invalid or incomplete.
        """
        return self._topology_api.get_all_device_positions()

    def set_device_position(
        self,
        device_id: str,
        x: int | float,
        y: int | float,
        mode: Literal["absolute", "relative"] = "absolute",
        inspect_app_format=True,
        fetch_device=True,
    ) -> TopologyDevice | None:
        """
        Set the position of a device in the topology.

        Args:
            device_id (str): Device ID.
            x (int | float): X coordinate.
            y (int | float): Y coordinate.
            mode (Literal["absolute", "relative"], optional): Positioning mode. Defaults to "absolute".
            inspect_app_format (bool, optional): If True, the device will be retrieved from the VideoIPath API after the position change. Defaults to True.

        Returns:
            TopologyDevice: TopologyDevice object.
        """
        response = self._topology_api.set_device_position(device_id, x, y, mode, inspect_app_format)

        if response.header.ok:
            self._logger.info(f"Device '{device_id}' position set to ({x}, {y}).")
            if fetch_device:
                device = self._topology_api.get_device_from_topology(device_id)
                return device
            else:
                return None
        else:
            raise ValueError(f"Error setting device position: {response.header}")


class TopologyPlacementLine:
    """Helper class for calculating and applying device positions in a line."""

    def __init__(self, topology_api: TopologyAPI, logger: Logger):
        self._topology_api = topology_api
        self._logger = logger

    def calculate_positions(
        self,
        device_ids: list[str],
        start_position: tuple[float, float] = (0.0, 0.0),
        step: float = 250.0,
        direction: Literal["horizontal", "vertical"] = "horizontal",
    ) -> dict[str, tuple[float, float]]:
        """
        Calculates device positions in a line.

        Args:
            start_position (tuple[float, float]): Starting position (x, y).
            step (float): Step distance between devices.

        Returns:
            dict[str, tuple[float, float]]: Device positions.
        """
        # Validate input
        if step == 0.0:
            raise ValueError("Step must be greater than 0.")

        x, y = start_position
        positions = {}
        for device_id in device_ids:
            positions[device_id] = (x, y)
            if direction == "horizontal":
                x += step
            elif direction == "vertical":
                y += step
            else:
                raise ValueError(f"Invalid direction: {direction}")
        return positions

    def apply_positions(
        self,
        device_ids: list[str],
        start_position: tuple[float, float] = (0.0, 0.0),
        step: float = 250.0,
        direction: Literal["horizontal", "vertical"] = "horizontal",
    ):
        """
        Aligns devices in a line.

        Args:
            device_ids (list[str]): Device IDs.
            start_position (tuple[float, float]): Starting position (x, y). Defaults to (0.0, 0.0).
            step (float): Step distance between devices. Defaults to 250.0.
            direction (Literal["horizontal", "vertical"], optional): Direction. Defaults to "horizontal".

        Returns:
            dict[str, tuple[float, float]]: Device positions.
        """
        # Validate input
        if step == 0.0:
            raise ValueError("Step must be greater than 0.")

        if direction not in ["horizontal", "vertical"]:
            raise ValueError(f"Invalid direction: {direction}")

        device_positions = self.calculate_positions(device_ids, start_position, step, direction)
        for device_id in device_positions:
            x, y = device_positions[device_id]
            self._topology_api.set_device_position(device_id=device_id, x=x, y=y)
        return device_positions


class TopologyPlacementGrid:
    """Helper class for calculating and applying device positions in a grid."""

    def __init__(self, topology_api: TopologyAPI, logger: Logger):
        self._topology_api = topology_api
        self._logger = logger

    def calculate_positions(
        self,
        device_ids: List[str],
        start_position: tuple[float, float] = (0.0, 0.0),
        columns: int = 2,
        row_spacing: float = 250.0,
        column_spacing: float = 250.0,
        order: Literal["row-major", "column-major"] = "row-major",
        alignment: Literal[
            "Top-Left",
            "Top-Center",
            "Top-Right",
            "Center-Left",
            "Center",
            "Center-Right",
            "Bottom-Left",
            "Bottom-Center",
            "Bottom-Right",
        ] = "Top-Left",
    ) -> dict[str, tuple[float, float]]:
        """
        Calculates device positions in a grid.

        Args:
            device_ids (List[str]): Device IDs.
            start_position (tuple[float, float]): Reference position for alignment. Defaults to (0.0, 0.0).
            columns (int): Number of columns. Defaults to 2.
            row_spacing (float): Spacing between rows. Defaults to 250.0.
            column_spacing (float): Spacing between columns. Defaults to 250.0.
            order (Literal["row-major", "column-major"], optional): Order. Defaults to "row-major".
            alignment (Literal[...], optional): Grid alignment relative to start position. Defaults to "Top-Left".

        Returns:
            dict[str, tuple[float, float]]: Device positions.
        """
        # Validate input
        if columns < 1:
            raise ValueError("Columns must be greater than 0.")
        if row_spacing < 0:
            raise ValueError("Row spacing must be greater than or equal to 0.")
        if column_spacing < 0:
            raise ValueError("Column spacing must be greater than or equal to 0.")

        # Calculate grid dimensions
        rows = -(-len(device_ids) // columns)  # Ceiling division for rows
        grid_width = (columns - 1) * column_spacing
        grid_height = (rows - 1) * row_spacing

        # Compute alignment offsets
        if alignment == "Top-Left":
            x_offset, y_offset = 0, 0
        elif alignment == "Top-Center":
            x_offset, y_offset = -grid_width / 2, 0
        elif alignment == "Top-Right":
            x_offset, y_offset = -grid_width, 0
        elif alignment == "Center-Left":
            x_offset, y_offset = 0, -grid_height / 2
        elif alignment == "Center":
            x_offset, y_offset = -grid_width / 2, -grid_height / 2
        elif alignment == "Center-Right":
            x_offset, y_offset = -grid_width, -grid_height / 2
        elif alignment == "Bottom-Left":
            x_offset, y_offset = 0, -grid_height
        elif alignment == "Bottom-Center":
            x_offset, y_offset = -grid_width / 2, -grid_height
        elif alignment == "Bottom-Right":
            x_offset, y_offset = -grid_width, -grid_height
        else:
            raise ValueError(f"Invalid alignment: {alignment}")

        # Apply alignment offsets to starting position
        x, y = start_position[0] + x_offset, start_position[1] + y_offset

        # Calculate positions
        positions = {}
        for i, device_id in enumerate(device_ids):
            if order == "row-major":
                row = i // columns
                column = i % columns
            elif order == "column-major":
                row = i % columns
                column = i // columns
            positions[device_id] = (x + column * column_spacing, y + row * row_spacing)
        return positions

    def apply_positions(
        self,
        device_ids: List[str],
        start_position: tuple[float, float] = (0.0, 0.0),
        columns: int = 2,
        row_spacing: float = 250.0,
        column_spacing: float = 250.0,
        order: Literal["row-major", "column-major"] = "row-major",
        alignment: Literal[
            "Top-Left",
            "Top-Center",
            "Top-Right",
            "Center-Left",
            "Center",
            "Center-Right",
            "Bottom-Left",
            "Bottom-Center",
            "Bottom-Right",
        ] = "Top-Left",
    ) -> dict[str, tuple[float, float]]:
        """
        Aligns devices in a grid.

        Args:
            device_ids (List[str]): Device IDs.
            start_position (tuple[float, float]): Reference position for alignment. Defaults to (0.0, 0.0).
            columns (int): Number of columns. Defaults to 2.
            row_spacing (float): Spacing between rows. Defaults to 250.0.
            column_spacing (float): Spacing between columns. Defaults to 250.0.
            order (Literal["row-major", "column-major"], optional): Order. Defaults to "row-major".
            alignment (Literal[...], optional): Grid alignment relative to start position. Defaults to "Top-Left".

        Returns:
            dict[str, tuple[float, float]]: Device positions.
        """
        device_positions = self.calculate_positions(
            device_ids, start_position, columns, row_spacing, column_spacing, order, alignment
        )
        for device_id in device_positions:
            x, y = device_positions[device_id]
            try:
                self._topology_api.set_device_position(device_id=device_id, x=x, y=y)
            except ValueError:
                self._logger.warning(f"Device '{device_id}' is not found in the topology, skipping.")
                continue
        return device_positions
