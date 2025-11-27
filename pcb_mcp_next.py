import re
import json
import asyncio
import pcbnew

from typing import Optional
from mcp.server.fastmcp import FastMCP
from pcb_tool_get import *
from pcb_tool_set import *
from pcb_tool_check import *


mcp = FastMCP("PCB", log_level="ERROR")

@mcp.tool()
async def label_area(file_path: str, func: str, center_x: float, center_y: float, size_x: float, size_y: float) -> str:
    """
    Label a rectangular area by its function on a specific user layer.

    Args:
        path (str): Path to the PCB file.
        func (str): Function name of the area to label.
        center_x (float): Center X of the area in mm.
        center_y (float): Center Y of the area in mm.
        size_x (float): Width of the area in mm.
        size_y (float): Height of the area in mm.
    """

    msg = await label_shape_by_layer(file_path, func, center_x, center_y, size_x, size_y)
    msg = await label_zone_by_name(file_path, func, center_x, center_y, size_x, size_y)

    return msg


@mcp.tool()
async def adjust_net_track(file_path: str, net: str, start_x: list[float], start_y: list[float], end_x: list[float], end_y: list[float], width: list[float]) -> str:
    """
    Adjust the position and width of tracks for a net.
    """

    board = pcbnew.LoadBoard(file_path)

    if not board:
        print(f"Error: Could not load board from {file_path}")
        return "Error: Could not load board"

    msg = await set_net_track(file_path, board, net, start_x, start_y, end_x, end_y, width)

    return msg


@mcp.tool()
async def get_pcb_image(file_path: str) -> str:
    """
    Export svg images of the current PCB layout with the board outline adjusted to the effective area.
    
    Args:
        file_path (str): Path to the PCB file.
    """

    msg = await export_pcb_image(file_path)
    print(msg)

    return msg