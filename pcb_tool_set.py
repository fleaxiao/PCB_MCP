import pcbnew
import json

from typing import Optional


async def set_board_cut(file_path: str, board: pcbnew.BOARD) -> str:
    """
    Set the PCB board edge at the edge cut layer.
    """
    try:
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
        msg = f"Success: Setting board cut edge. New Board Center: ({center_x:.2f} mm, {center_y:.2f} mm), New Board Size: {size_x:.2f} mm x {size_y:.2f} mm"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set board size - {str(e)}"


async def set_board_GND(file_path: str, board: pcbnew.BOARD) -> str:
    """
    Set the GND zone at the B_Cu layer.
    """
    try:
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
        board.Add(zone)
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())

        board.Save(file_path)
        msg = f"Success: Setting board GND zone."
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set board size - {str(e)}"


async def set_module_position_angle(file_path: str, board: pcbnew.BOARD, module_ref: str, 
                                    pos_x: Optional[float] = None, pos_y: Optional[float] = None, angle: Optional[float] = None) -> str:
    """
    Set the position and angle of one module.
    """
    try:
        module = board.FindFootprintByReference(module_ref)

        if not module:
            print(f"Error: Could not find module with reference {module_ref}")
            return "Error: Could not find module"
        
        current_pos_x = pcbnew.ToMM(module.GetPosition())[0]
        current_pos_y = pcbnew.ToMM(module.GetPosition())[1]
        current_angle = module.GetOrientationDegrees()

        if pos_x is None:
            pos_x = current_pos_x
        if pos_y is None:
            pos_y = current_pos_y
        if angle is None:
            angle = current_angle

        module.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos_x), pcbnew.FromMM(pos_y)))
        module.SetOrientationDegrees(angle)
        pcbnew.Refresh()

        pos_x = pcbnew.ToMM(module.GetPosition())[0]
        pos_y = pcbnew.ToMM(module.GetPosition())[1]
        angle_degrees = module.GetOrientationDegrees()

        board.Save(file_path)
        msg = f"Success: Setting module {module_ref} position and angle. New Position: ({pos_x:.2f} mm, {pos_y:.2f} mm), Angle: {angle_degrees} degrees"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board or module object - {str(e)}"
    except Exception as e:
        return f"Error: Failed to set module position and angle - {str(e)}"
    

async def set_net_track(file_path: str, board: pcbnew.BOARD, net_name: str,
                        start_x: list[float], start_y: list[float], end_x: list[float], end_y: list[float], width: list[float]) -> str:
    """
    Create traces for a net.
    """
    try:
        netinfo = board.FindNet(net_name)
        if not netinfo or netinfo.GetNetCode() == 0:
            return f"Error: Net '{net_name}' not found in board"

        for old_track in list(board.GetTracks()):
            if old_track.GetNetname() == net_name:
                board.Delete(old_track)

        # Create new tracks
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
        msg = f"Success: Creating tracks for net '{net_name}'"
        return msg

    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to create net traces - {str(e)}"


async def label_area_by_layer(file_path: str, board: pcbnew.BOARD, func: str, center_x: float, center_y: float, size_x: float, size_y: float) -> str:
    """
    Label a rectangular area by its function on a specific user layer.
    """
    try:
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
        msg = f"Success: Labeling area '{func}' on layer '{layer_name}' at center ({center_x:.2f} mm, {center_y:.2f} mm) with size {size_x:.2f} mm x {size_y:.2f} mm."
        return msg
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to label area - {str(e)}"