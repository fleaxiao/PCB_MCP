import pcbnew

from typing import Optional
from pcb_utility import *


async def check_board_onboard_violations(board: pcbnew.BOARD) -> list[str]:
    """
    Check if any modules or labeling areas are out of the board boundaries.
    """
    try:
        onboard_violations = []
        board_courtyard = await get_board_courtyard(board)

        for module in board.GetFootprints():
            module_courtyard = await get_footprint_courtyard(module)
            if not board_courtyard.Contains(module_courtyard):
                ref = module.GetReference()
                pos = module.GetPosition()
                size = module_courtyard.GetSize()
                violation_info = f"On-Board Issue: {ref} is out of board bounds. Size: {pcbnew.ToMM(size.x):.2f} mm x {pcbnew.ToMM(size.y):.2f} mm, Position: ({pcbnew.ToMM(pos.x):.2f} mm, {pcbnew.ToMM(pos.y):.2f} mm)"
                onboard_violations.append(violation_info)

        for item in board.GetDrawings():
            if isinstance(item, (pcbnew.PCB_SHAPE, pcbnew.PCB_TEXT)):
                if item.GetLayer() in [pcbnew.User_1, pcbnew.User_2, pcbnew.User_3, pcbnew.User_4]:
                    item_bbox = item.GetBoundingBox()
                    if not board_courtyard.Contains(item_bbox):
                        pos = item.GetPosition()
                        size = item_bbox.GetSize()
                        if isinstance(item, pcbnew.PCB_SHAPE):
                            item_type = f"Shape ({item.GetShapeStr()})"
                        elif isinstance(item, pcbnew.PCB_TEXT):
                            item_type = "Text"
                        else:
                            item_type = "Drawing"
                        violation_info = f"On-Board Issue: {item_type} is out of board bounds. Size: {pcbnew.ToMM(size.x):.2f} mm x {pcbnew.ToMM(size.y):.2f} mm, Position: ({pcbnew.ToMM(pos.x):.2f} mm, {pcbnew.ToMM(pos.y):.2f} mm)"
                        onboard_violations.append(violation_info)
        return onboard_violations
    
    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}"]
    except Exception as e:
        return [f"Error: Failed to check on-board violations - {str(e)}\n"]


async def check_board_clearance_violations(board: pcbnew.BOARD, min_clearance: float) -> list[str]:
    """
    Check if any modules are put too close so that they violate the clearance rules.
    """
    try:
        clearance_violations = []
        min_clearance = min_clearance if min_clearance is not None else 0.2

        modules = list(board.GetFootprints())
        for i, mod1 in enumerate(modules):

            bbox1 = await get_footprint_courtyard(mod1)
            expanded_bbox1 = pcbnew.BOX2I(bbox1.GetPosition(), bbox1.GetSize())
            expanded_bbox1.Inflate(pcbnew.FromMM(min_clearance))

            for mod2 in modules[i+1:]:
                bbox2 = await get_footprint_courtyard(mod2)

                if expanded_bbox1.Intersects(bbox2):
                    ref1 = mod1.GetReference()
                    ref2 = mod2.GetReference()
                    
                    pos1 = mod1.GetPosition()
                    pos2 = mod2.GetPosition()
                    
                    size1 = bbox1.GetSize()
                    size2 = bbox2.GetSize()

                    violation_info = f"Clearance Issue: {ref1} and {ref2} too close. {ref1}: Size: {pcbnew.ToMM(size1.x):.2f} mm x {pcbnew.ToMM(size1.y):.2f} mm, Position: ({pcbnew.ToMM(pos1.x):.2f} mm, {pcbnew.ToMM(pos1.y):.2f} mm). {ref2}: Size: {pcbnew.ToMM(size2.x):.2f} mm x {pcbnew.ToMM(size2.y):.2f} mm, Position: ({pcbnew.ToMM(pos2.x):.2f} mm, {pcbnew.ToMM(pos2.y):.2f} mm)"
                    clearance_violations.append(violation_info)
        return clearance_violations
    
    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}"]
    except Exception as e:
        return [f"Error: Failed to check clearance violations - {str(e)}\n"]


async def calculate_power_density(board):
    """
    Calculate the power density of the PCB board by calculating the footprint area ratio (footprint area / effective area) and the effective area ratio (effective area / board area).
    """
    footprint_arae = 0.0
    for module in board.GetFootprints():
        footprint_w_i, footprint_h_i = await get_footprint_size(module)
        footprint_area = footprint_w_i * footprint_h_i
        footprint_arae += footprint_area
    
    board_size = board.ComputeBoundingBox().GetSize()
    board_size_x = pcbnew.ToMM(board_size.x)
    board_size_y = pcbnew.ToMM(board_size.y)
    board_area = board_size_x * board_size_y

    power_density = (footprint_arae / board_area) * 100 if board_area > 0 else 0
    if power_density < 40:
        power_density_info = "Warning: modules are placed too loosely, please adjust the model close to each other!"
    else:
        power_density_info = "The modules are placed appropriately."

    msg = f"""Footprint area: {footprint_arae:.2f} mm², Board area: {board_area:.2f} mm². Power density: {power_density:.2f}%. {power_density_info}"""

    return msg


async def check_module_clearance(board: pcbnew.BOARD, mod1: pcbnew.FOOTPRINT, min_clearance: Optional[float] = None) -> list[str]:
    
    modules = list(board.GetFootprints())
    bbox1 = await get_footprint_courtyard(mod1)
    expanded_bbox1 = pcbnew.BOX2I(bbox1.GetPosition(), bbox1.GetSize())
    expanded_bbox1.Inflate(pcbnew.FromMM(min_clearance))

    overlapped_modules = []
    for mod2 in modules:
        if mod2.GetReference() == mod1.GetReference():
            continue
        bbox2 = await get_footprint_courtyard(mod2)
        ref2 = mod2.GetReference()

        if expanded_bbox1.Intersects(bbox2):
            overlapped_modules.append(ref2)

    return overlapped_modules


async def check_pad2pad_connection(board: pcbnew.BOARD, mod1: pcbnew.FOOTPRINT) -> str:
    module_pos_x, module_pos_y = pcbnew.ToMM(mod1.GetPosition())

    distance_info = ""
    alignment = []
    segments = []
    module_connections = {}
    
    for pad in mod1.Pads():
        net_name = pad.GetNetname()
        if net_name != "" and net_name != "GND":
            pad_pos_x, pad_pos_y = pcbnew.ToMM(pad.GetPosition())
            net = board.FindNet(net_name)
            net_code = net.GetNetCode()
            for module_i in board.GetFootprints():
                if module_i.GetReference() != mod1.GetReference() and module_i.IsLocked() == False:
                    module_i_ref = module_i.GetReference()

                    for pad_i in module_i.Pads():
                        if pad_i.GetNetCode() == net_code:
                            module_i_pos_x, module_i_pos_y = pcbnew.ToMM(module_i.GetPosition())
                            module2module_distance = ((module_pos_x - module_i_pos_x) ** 2 + (module_pos_y - module_i_pos_y) ** 2) ** 0.5

                            if module_i_ref not in module_connections:
                                module_connections[module_i_ref] = {
                                    'distance': module2module_distance,
                                    'connections': []
                                }
                            
                            pad_i_pos_x, pad_i_pos_y = pcbnew.ToMM(pad_i.GetPosition())
                            pad2pad_distance = ((pad_pos_x - pad_i_pos_x) ** 2 + (pad_pos_y - pad_i_pos_y) ** 2) ** 0.5

                            pad_num = pad.GetNumber()
                            pad_i_num = pad_i.GetNumber()
                            
                            module_connections[module_i_ref]['connections'].append(
                                f"the pad-to-pad distance between pad {pad_num} of {mod1.GetReference()} and pad {pad_i_num} of {module_i_ref} in net {net_name} is {pad2pad_distance:.2f} mm"
                            )
                            if pad2pad_distance > module2module_distance:
                                alignment.append((pad_num, mod1.GetReference(), pad_i_num, module_i_ref, net_name))

                            segments.append((pad_pos_x, pad_pos_y, pad_i_pos_x, pad_i_pos_y, net_name))
    
    for idx, (module_ref, data) in enumerate(module_connections.items(), start=1):
        distance_info += f"Connection {idx}: {mod1.GetReference()} is connected to {module_ref}, "
        distance_info += f"the module-to-module distance is {data['distance']:.2f} mm, "
        distance_info += f"{', '.join(data['connections'])}" + ". "

    intersect = await check_segments_intersect(segments)

    return alignment, intersect, distance_info


async def check_module_status_by_angles(file_path: str, board: pcbnew.BOARD, module_ref: str, pos_x: Optional[float] = None, pos_y: Optional[float] = None, angle: Optional[float] = None, min_clearance: Optional[float] = None) -> str:

    msg = ""
    min_clearance = min_clearance if min_clearance is not None else 0.2
    
    mod1 = board.FindFootprintByReference(module_ref)

    for angle in [0, 90, 180, 270]:
        mod1.SetOrientationDegrees(angle)
        
        overlapped_modules = await check_module_clearance(board, mod1, min_clearance)
        alignment, intersect, distance_info = await check_pad2pad_connection(board, mod1)

        if overlapped_modules:
            msg += f"ERROR: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} overlap with {', '.join(overlapped_modules)}.\n"
        else :
            if alignment:
                msg += f"WARNING: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets the clearance requirements, but the possible pad-to-pad misalignments should be checked: "
                for pad1, mod1_ref, pad2, mod2_ref, net in alignment:
                    alignment_msgs = [f"the pad {pad1} of {mod1_ref} and pad {pad2} of {mod2_ref} in net {net}" for pad1, mod1_ref, pad2, mod2_ref, net in alignment]
                msg += ', '.join(alignment_msgs) + ". "
                msg += distance_info + "\n"
                continue
            if intersect:
                msg += f"WARNING: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets the clearance requirements, but there are pin-to-pin connections intersections: "
                for seg1_idx, seg2_idx, net1, net2 in intersect:
                    intersection_msg = f"the net {net1} and net {net2}"
                    msg += ', '.join([intersection_msg]) + ". "
                    msg += distance_info + "\n"
                continue
            else:
                msg += f"INFO: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets all clearance requirements, and there is no pin-to-pin misalignment or intersection. {distance_info}\n"


    for seg1_idx, seg2_idx, net1, net2 in intersect:
        msg += f"Warning: There are pin-to-pin connections intersecting for net {net1} and net {net2} in module {module_ref}, please consider adjusting the position or angle of the module\n"

    return msg


async def check_module_status_by_positions(file_path: str, board: pcbnew.BOARD, module_ref: str, pos_x: Optional[float] = None, pos_y: Optional[float] = None, angle: Optional[float] = None, min_clearance: Optional[float] = None) -> str:

    msg = ""
    min_clearance = min_clearance if min_clearance is not None else 0.2
    
    mod1 = board.FindFootprintByReference(module_ref)

    for angle in [0, 90, 180, 270]:
        mod1.SetOrientationDegrees(angle)
        
        overlapped_modules = await check_module_clearance(board, mod1, min_clearance)
        alignment, intersect, distance_info = await check_pad2pad_connection(board, mod1)

        if overlapped_modules:
            msg += f"ERROR: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} overlap with {', '.join(overlapped_modules)}.\n"
        else :
            if alignment:
                msg += f"WARNING: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets the clearance requirements, but the possible pad-to-pad misalignments should be checked: "
                for pad1, mod1_ref, pad2, mod2_ref, net in alignment:
                    alignment_msgs = [f"the pad {pad1} of {mod1_ref} and pad {pad2} of {mod2_ref} in net {net}" for pad1, mod1_ref, pad2, mod2_ref, net in alignment]
                msg += ', '.join(alignment_msgs) + ". "
                msg += distance_info + "\n"
                continue
            if intersect:
                msg += f"WARNING: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets the clearance requirements, but there are pin-to-pin connections intersections: "
                for seg1_idx, seg2_idx, net1, net2 in intersect:
                    intersection_msg = f"the net {net1} and net {net2}"
                    msg += ', '.join([intersection_msg]) + ". "
                    msg += distance_info + "\n"
                continue
            else:
                msg += f"INFO: when the angle of {module_ref} is {angle} degrees, {mod1.GetReference()} meets all clearance requirements, and there is no pin-to-pin misalignment or intersection. {distance_info}\n"


    for seg1_idx, seg2_idx, net1, net2 in intersect:
        msg += f"Warning: There are pin-to-pin connections intersecting for net {net1} and net {net2} in module {module_ref}, please consider adjusting the position or angle of the module\n"

    return msg