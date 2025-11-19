import re
import json
import asyncio
import pcbnew

from typing import Optional
from mcp.server.fastmcp import FastMCP
from pcb_resource import *
from pcb_tool_get import *
from pcb_tool_set import *
from pcb_tool_check import *


mcp = FastMCP("PCB", log_level="ERROR")

@mcp.tool()
async def get_dataset_info(file_path: str) -> str:
    """
    Scrape the dataset webpage to extract textual and tabular information about IC description, pin function and layout guidance.

    Args:
        file_path (str): Path to the PCB file.
    """

    board = pcbnew.LoadBoard(file_path)
    if not board:
        print(f"Error: Could not load PCB from {file_path}")
        return "Error: Could not load PCB"
    
    msg = []
    for module in board.GetFootprints():
        ref = module.GetReference()
        if ref.startswith('U'):
            value = module.GetValue()
            ic_module = re.sub(r'[A-Za-z]+$', '', value)
            ic_url = f"https://www.ti.com/document-viewer/{ic_module}/datasheet"
            datasheet_info = await spider_datasheet_info(ic_url)
            msg.append({"reference": ref, "ic_module": ic_module, "datasheet_info": datasheet_info})

    if not msg:
        return ["No modules with reference starting with 'U' found"]
    print(json.dumps(msg, indent=2, ensure_ascii=False))

    return msg

@mcp.tool()
async def get_pcb_info(file_path: str) -> str:
    """
    Analyze basic information of board, module, track and via.
    
    Args:
        file_path (str): Path to the PCB file.
    """

    board = pcbnew.LoadBoard(file_path)
    if not board:
        print(f"Error: Could not load PCB from {file_path}")
        return "Error: Could not load PCB"

    info_functions = [ana_board_info, ana_module_info, ana_net_info, ana_track_info, ana_via_info]
    info_results = []
    for func in info_functions:
        try:
            result = await func(board)
            info_results.append(result)
        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            return error_msg
    board_info, module_info, net_info, track_info, via_info = info_results

    msg = f"{'='*60}\n" + board_info + f"{'='*60}\n" + "".join(module_info) + f"{'='*60}\n" + "".join(net_info) + f"{'='*60}\n" + "".join(track_info) + f"{'='*60}\n" + "".join(via_info) + f"{'='*60}\n"
    print(msg)

    return msg

@mcp.tool()
async def get_pcb_image(file_path: str) -> str:
    """
    Export svg images of the PCB file.
    
    Args:
        file_path (str): Path to the PCB file.
    """

    msg = await save_pcb_image(file_path)
    print(msg)

    return msg

@mcp.tool()
async def init_pcb(file_path: str) -> str:
    """
    Initialize the modules to ensure the center of the courtyard is at the origin of each footprint. This is a prerequisite for subsequent operations.
    
    Args:
        file_path (str): Path to the PCB file.
    """

    msg = await init_module(file_path)
    print(msg)

    return msg

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

    # msg = await label_shape_by_layer(file_path, func, center_x, center_y, size_x, size_y)
    msg = await label_zone_by_name(file_path, func, center_x, center_y, size_x, size_y)
    print(msg)

    return msg

@mcp.tool()
async def adjust_module_position(file_path: str, module_ref: str, pos_x: Optional[float] = None, pos_y: Optional[float] = None) -> str:
    """
    Adjust the position and angle of one module.

    Args:
        path (str): Path to the PCB file.
        module_ref (str): Reference of the module to modify.
        pos_x (Optional[float]): New X position in mm. If None, keeps current position.
        pos_y (Optional[float]): New Y position in mm. If None, keeps current position.
    """

    board = pcbnew.LoadBoard(file_path)
    if not board:
        print(f"Error: Could not load PCB from {file_path}")
        return "Error: Could not load PCB"

    msg_functions = [set_module_position, check_module_statue]
    msg = ""
    for func in msg_functions:
        try:
            result = await func(file_path, board, module_ref, pos_x, pos_y)
            msg += result
        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            return error_msg
    print(msg)

    return msg

@mcp.tool()
async def adjust_module_angle(file_path: str, module_ref: str, angle: Optional[float] = None) -> str:
    """
    Adjust the position and angle of one module.

    Args:
        path (str): Path to the PCB file.
        module_ref (str): Reference of the module to modify.
        angle (Optional[float]): New angle in degrees. If None, keeps current angle.
    """

    board = pcbnew.LoadBoard(file_path)
    if not board:
        print(f"Error: Could not load PCB from {file_path}")
        return "Error: Could not load PCB"

    msg_functions = [set_module_angle]
    msg = ""
    for func in msg_functions:
        try:
            result = await func(file_path, board, module_ref, angle)
            msg += result
        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            return error_msg
    print(msg)

    return msg

# @mcp.tool()
# async def adjust_net_track(file_path: str, net: str, start_x: list[float], start_y: list[float], end_x: list[float], end_y: list[float], width: list[float]) -> str:
#     """
#     Adjust the position and width of tracks for a net.
#     """

#     board = pcbnew.LoadBoard(file_path)

#     if not board:
#         print(f"Error: Could not load board from {file_path}")
#         return "Error: Could not load board"

#     msg = await set_net_track(file_path, board, net, start_x, start_y, end_x, end_y, width)
#     print(msg)

#     return msg

@mcp.tool()
async def set_board(file_path: str) -> str:
    """
    When finishing the module placement, adjust the board size in the Edge.Cuts layer according to the current effective area. Add copper zone for GND net on B.Cu layer
    
    Args:
        path (str): Path to the PCB file.
    """

    msg =  await set_board_cut(file_path)
    msg += "\n" + await set_board_GND(file_path)
    print(msg)

    return msg

@mcp.tool()
async def check_power_density(file_path: str) -> str:
    """
    check the power density of the PCB board by calculating the footprint area ratio and the effective area ratio.
    
    Args:
        file_path (str): Path to the PCB file.
    """

    board = pcbnew.LoadBoard(file_path)

    if not board:
        print(f"Error: Could not load board from {file_path}")
        return "Error: Could not load board"
    
    msg = await calculate_power_density(board)
    print(msg)

    return msg

@mcp.tool()
async def check_design_rule(file_path: str, min_clearance: Optional[float] = None) -> str:
    """
    Run Design Rule Check (DRC) on the PCB file and report violations. The current implementation checks for module clearance violations.
    
    Args:
        file_path (str): Path to the PCB file.
        min_clearance (Optional[float]): Minimum clearance in mm between modules. If None, uses default 0.2 mm.
    """
    
    board = pcbnew.LoadBoard(file_path)
    
    if not board:
        print(f"Error: Could not load board from {file_path}")
        return "Error: Could not load board"

    check_functions = [check_board_onboard_violations, check_board_clearance_violations]
    check_results = []
    for func in check_functions:
        try:
            if func == check_board_clearance_violations:
                result = await func(board, min_clearance)
            else:
                result = await func(board)
            check_results.append(result)
        except Exception as e:
            error_msg = f"Error: {str(e)}\n"
            return error_msg
    onboard_violations, clearance_violations = check_results

    # Violation summary
    if len(onboard_violations) + len(clearance_violations) == 0:
        msg = "Design Rule Check (DRC) passed! No violations found.\n" + f"{'='*60}\n"
    else:
        msg = f"""Design Rule Check (DRC) error! Here is the error summary:
{'='*60}
Total DRC Violations: {len(onboard_violations) + len(clearance_violations)}
On-Board Violations: {len(onboard_violations)}
Clearance Violations: {len(clearance_violations)}
{'='*60}
"""
    # Violation details
    if len(onboard_violations) > 0:
        msg += "On-Board Violations:\n"
    for i, v in enumerate(onboard_violations, 1):
        violation = f"{i}. {v}"
        msg += violation + "\n"
    if len(onboard_violations) > 0:
        msg += f"{'='*60}\n"

    if len(clearance_violations) > 0:
        msg += "Clearance Violations:\n"
    for i, v in enumerate(clearance_violations, 1):
        violation = f"{i}. {v}"
        msg += violation + "\n"
    if len(clearance_violations) > 0:
        msg += f"{'='*60}\n"

    print(msg)
    return msg

if __name__ == "__main__":
    # mcp.run(transport="stdio")

    file_path = r"test_board\test.kicad_pcb"
    module_ref = "L1"
    pos_x = 55.0
    pos_y = 40
    angle = 90
    # asyncio.run(adjust_module_position(file_path, module_ref))

    # center_x = 75.0
    # center_y = 50.0
    # size_x = 20.0
    # size_y = 20.0

    asyncio.run(get_pcb_info(file_path))
    # asyncio.run(init_pcb(file_path))
    # asyncio.run(label_area(file_path, "myVOUT", center_x, center_y, size_x, size_y))
    # asyncio.run(check_design_rule(file_path))
    # asyncio.run(set_board(file_path))