import pcbnew
import json

from typing import Optional
from pcb_utility import *


async def init_module(file_path: str) -> str:
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load board from {file_path}"
        
        for module in board.GetFootprints():
            courtyard_bbox = await get_footprint_courtyard(module)
            courtyard_bbox_pos_x = pcbnew.ToMM(courtyard_bbox.GetPosition())[0]
            courtyard_bbox_pos_y = pcbnew.ToMM(courtyard_bbox.GetPosition())[1]
            courtyard_bbox_center_x = courtyard_bbox_pos_x + pcbnew.ToMM(courtyard_bbox.GetWidth()) / 2
            courtyard_bbox_center_y = courtyard_bbox_pos_y + pcbnew.ToMM(courtyard_bbox.GetHeight()) / 2

            module_pos_x = pcbnew.ToMM(module.GetPosition())[0]
            module_pos_y = pcbnew.ToMM(module.GetPosition())[1]

            for graphic in module.GraphicalItems():
                graphic.Move(pcbnew.VECTOR2I(
                    pcbnew.FromMM(module_pos_x - courtyard_bbox_center_x),
                    pcbnew.FromMM(module_pos_y - courtyard_bbox_center_y)
                ))
            for graphic in module.Pads():
                graphic.Move(pcbnew.VECTOR2I(
                    pcbnew.FromMM(module_pos_x - courtyard_bbox_center_x),
                    pcbnew.FromMM(module_pos_y - courtyard_bbox_center_y)
                ))

            module.SetLocked(True)

        board.Save(file_path)
        return "SUCCESSfully initialized modules to center courtyard at origin."

    except Exception as e:
        return f"Error: Failed to initialize new PCB board - {str(e)}"


async def set_module_position(file_path: str, board: pcbnew.BOARD, module_ref: str, pos_x: Optional[float] = None, pos_y: Optional[float] = None) -> str:
    try:
        module = board.FindFootprintByReference(module_ref)
        module.SetLocked(False)

        if not module:
            print(f"Error: Could not find module with reference {module_ref}")
            return "Error: Could not find module"
        
        current_pos_x = pcbnew.ToMM(module.GetPosition())[0]
        current_pos_y = pcbnew.ToMM(module.GetPosition())[1]

        if pos_x is None:
            pos_x = current_pos_x
        if pos_y is None:
            pos_y = current_pos_y

        module.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos_x), pcbnew.FromMM(pos_y)))

        pos_x = pcbnew.ToMM(module.GetPosition())[0]
        pos_y = pcbnew.ToMM(module.GetPosition())[1]

        pad_num_list = []
        pad_pos_x_list = []
        pad_pos_y_list = []
        pad_net_list = []
        for pad in module.Pads():
            net = pad.GetNetname()
            num = pad.GetNumber()
            if net != "":
                pad_num_list.append(num)
                pad_pos_x, pad_pos_y = pcbnew.ToMM(pad.GetPosition())
                pad_pos_x_list.append(pad_pos_x)
                pad_pos_y_list.append(pad_pos_y)    
                pad_net_list.append(net)

        board.Save(file_path)
        msg = f"SUCCESS: The new position of {module_ref} is set to ({pos_x:.2f} mm, {pos_y:.2f} mm). "
        for num, px, py, net in zip(pad_num_list, pad_pos_x_list, pad_pos_y_list, pad_net_list):
            msg += f"Pad {num} for net {net} is at ({px:.2f} mm, {py:.2f} mm); "
        msg += "\n" 
        return msg

    except AttributeError as e:
        return f"Error: Invalid board or module object - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set module position - {str(e)}"
    
async def set_module_angle(file_path: str, board: pcbnew.BOARD, module_ref: str, angle: Optional[float] = None) -> str:
    try:
        module = board.FindFootprintByReference(module_ref)
        module.SetLocked(False)

        if not module:
            print(f"Error: Could not find module with reference {module_ref}")
            return "Error: Could not find module"
        
        current_angle = module.GetOrientationDegrees()

        if angle is None:
            angle = current_angle

        module.SetOrientationDegrees(angle)

        angle_degrees = module.GetOrientationDegrees()

        board.Save(file_path)
        msg = f"SUCCESS: The new angle of {module_ref} is set to {angle_degrees} degrees.\n"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board or module object - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set module angle - {str(e)}"
    

async def set_net_track(file_path: str, board: pcbnew.BOARD, net_name: str,
                        start_x: list[float], start_y: list[float], end_x: list[float], end_y: list[float], width: list[float]) -> str:
    """
    Create tracks for a net.
    """
    try:
        netinfo = board.FindNet(net_name)
        if not netinfo or netinfo.GetNetCode() == 0:
            return f"Error: Net '{net_name}' not found in board"

        for old_track in list(board.GetTracks()):
            if old_track.GetNetname() == net_name:
                board.Delete(old_track)

        for i in range(len(start_x)):
            new_track = pcbnew.PCB_TRACK(board)
            new_track.SetNet(netinfo)
            new_track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start_x[i]), pcbnew.FromMM(start_y[i])))
            new_track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end_x[i]), pcbnew.FromMM(end_y[i])))
            new_track.SetWidth(pcbnew.FromMM(width[i]))
            new_track.SetLayer(pcbnew.F_Cu)
            board.Add(new_track)

        pcbnew.Refresh()
        board.Save(file_path)
        msg = f"SUCCESS: Creating tracks for net '{net_name}'"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to create net traces - {str(e)}"


async def label_shape_by_layer(file_path: str, func: str, center_x: float, center_y: float, size_x: float, size_y: float) -> str:
    """
    Label a rectangular shape by its function on a specific user layer.
    """
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load PCB from {file_path}"
        
        with open('pcb_const.json', 'r') as f:
            config = json.load(f)
            FUNC2LAYER = config['FUNC2LAYER']

        if func in FUNC2LAYER:
            layer_name = FUNC2LAYER[func]
        else:
            layer_name = "F_SilkS"
        layer_id = board.GetLayerID(layer_name)

        for item in list(board.GetDrawings()):
            if isinstance(item, pcbnew.PCB_SHAPE) and item.GetLayer() == layer_id:
                board.Delete(item)

        rect_shape = pcbnew.PCB_SHAPE(board)
        rect_shape.SetShape(pcbnew.SHAPE_T_RECT)
        rect_shape.SetStartX(pcbnew.FromMM(center_x - size_x / 2))
        rect_shape.SetStartY(pcbnew.FromMM(center_y - size_y / 2))
        rect_shape.SetEndX(pcbnew.FromMM(center_x + size_x / 2))
        rect_shape.SetEndY(pcbnew.FromMM(center_y + size_y / 2))
        rect_shape.SetLayer(layer_id)
        board.Add(rect_shape)

        pcbnew.Refresh()
        board.Save(file_path)
        msg = f"SUCCESS: Labeling a rectangular shape '{func}' on layer '{layer_name}' at center ({center_x:.2f} mm, {center_y:.2f} mm) with size {size_x:.2f} mm x {size_y:.2f} mm."
        return msg
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to label area - {str(e)}"


async def label_zone_by_name(file_path: str, func: str, center_x: float, center_y: float, size_x: float, size_y: float) -> str:
    """
    Label a rectangular zone by its function by a specific name.
    """
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load PCB from {file_path}"

        zone = pcbnew.ZONE(board)
        zone.SetLayer(board.GetLayerID("User.1"))
        outline = zone.Outline()
        outline.NewOutline()
        outline.Append(pcbnew.FromMM(center_x - size_x / 2), pcbnew.FromMM(center_y - size_y / 2))
        outline.Append(pcbnew.FromMM(center_x + size_x / 2), pcbnew.FromMM(center_y - size_y / 2))
        outline.Append(pcbnew.FromMM(center_x + size_x / 2), pcbnew.FromMM(center_y + size_y / 2))
        outline.Append(pcbnew.FromMM(center_x - size_x / 2), pcbnew.FromMM(center_y + size_y / 2))
        zone.SetZoneName(func)
        board.Add(zone)

        pcbnew.Refresh()
        board.Save(file_path)

        name = zone.GetZoneName()
        msg = f"SUCCESS: Labeling a rectangular zone '{name}' on layer 'User.1' at center ({center_x:.2f} mm, {center_y:.2f} mm) with size {size_x:.2f} mm x {size_y:.2f} mm."
        return msg
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to label zone - {str(e)}"


async def set_board_cut(file_path: str) -> str:
    """
    Set the PCB board edge at the edge cut layer.
    """
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load board from {file_path}"
        
        for item in list(board.GetDrawings()):
            if isinstance(item, pcbnew.PCB_SHAPE) and item.GetLayer() == pcbnew.Edge_Cuts:
                board.Delete(item)

        size = board.ComputeBoundingBox().GetSize()
        size_x = pcbnew.ToMM(size.x)
        size_y = pcbnew.ToMM(size.y)
        center = board.ComputeBoundingBox().GetCenter()
        center_x = pcbnew.ToMM(center.x)
        center_y = pcbnew.ToMM(center.y)

        rect_shape = pcbnew.PCB_SHAPE(board)
        rect_shape.SetShape(pcbnew.SHAPE_T_RECT)
        rect_shape.SetStartX(pcbnew.FromMM(center_x - size_x / 2))
        rect_shape.SetStartY(pcbnew.FromMM(center_y - size_y / 2))
        rect_shape.SetEndX(pcbnew.FromMM(center_x + size_x / 2))
        rect_shape.SetEndY(pcbnew.FromMM(center_y + size_y / 2))
        rect_shape.SetLayer(pcbnew.Edge_Cuts)
        board.Add(rect_shape)

        board.Save(file_path)
        msg = f"SUCCESS: Setting board cut edge. New Board Center: ({center_x:.2f} mm, {center_y:.2f} mm), New Board Size: {size_x:.2f} mm x {size_y:.2f} mm"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set board size - {str(e)}"


async def set_board_GND(file_path: str) -> str:
    """
    Set the GND zone at the B_Cu layer.
    """
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load board from {file_path}"
        
        for zone in board.Zones():
            if isinstance(zone, pcbnew.ZONE):
                board.Delete(zone)
        size = board.ComputeBoundingBox().GetSize()
        size_x = pcbnew.ToMM(size.x)
        size_y = pcbnew.ToMM(size.y)
        center = board.ComputeBoundingBox().GetCenter()
        center_x = pcbnew.ToMM(center.x)
        center_y = pcbnew.ToMM(center.y)

        zone = pcbnew.ZONE(board)
        zone.SetLayer(pcbnew.B_Cu)
        outline = zone.Outline()
        outline.NewOutline()
        outline.Append(pcbnew.FromMM(center_x - size_x / 2), pcbnew.FromMM(center_y - size_y / 2))
        outline.Append(pcbnew.FromMM(center_x + size_x / 2), pcbnew.FromMM(center_y - size_y / 2))
        outline.Append(pcbnew.FromMM(center_x + size_x / 2), pcbnew.FromMM(center_y + size_y / 2))
        outline.Append(pcbnew.FromMM(center_x - size_x / 2), pcbnew.FromMM(center_y + size_y / 2))
        gnd_net = board.FindNet("GND")
        if gnd_net:
            zone.SetNet(gnd_net)
        else:
            return "Error: GND net not found in board"
        board.Add(zone)
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())

        board.Save(file_path)
        msg = f"SUCCESS: Setting board GND zone."
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set board size - {str(e)}"