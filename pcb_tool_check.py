import pcbnew

from pcb_utility import *


async def check_onboard_violations(board: pcbnew.BOARD) -> list[str]:
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


async def check_clearance_violations(board: pcbnew.BOARD, min_clearance: float) -> list[str]:
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

    for item in list(board.GetDrawings()):
        if isinstance(item, pcbnew.PCB_SHAPE) and item.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(item)

    effect_size = board.ComputeBoundingBox().GetSize()
    effect_size_x = pcbnew.ToMM(effect_size.x)
    effect_size_y = pcbnew.ToMM(effect_size.y)
    effect_area = effect_size_x * effect_size_y

    footprint_ratio = (footprint_arae / effect_area) * 100 if effect_area > 0 else 0
    if footprint_ratio < 40:
        footprint_info = "Warning: modules are placed too loosely, please adjust the model close to each other!"
    else:
        footprint_info = "The modules are placed appropriately."

    effect_ratio = (effect_area / board_area) * 100 if board_area > 0 else 0
    effect_ratio_x = (effect_size_x / board_size_x) * 100 if board_size_x > 0 else 0
    effect_ratio_y = (effect_size_y / board_size_y) * 100 if board_size_y > 0 else 0
    if effect_ratio < 40:
        effect_info = "Warning: significant unused board area detected!"
        if effect_ratio_x < 60:
            effect_info += f" Please optimize the width usage: {effect_ratio_x:.2f}%"
        if effect_ratio_y < 60:
            effect_info += f" Please optimize the height usage: {effect_ratio_y:.2f}%"
    else:
        effect_info = "The board area is utilized effectively."

    msg = f"""Footprint area: {footprint_arae:.2f} mm². Footprint area ratio: {footprint_ratio:.2f}% (footprint area / effective area). {footprint_info}
Effective area: {effect_area:.2f} mm². Effective area ratio: {effect_ratio:.2f}%  (effective area / board area). {effect_info}
Board area: {board_area:.2f} mm², size: {board_size_x:.2f} mm x {board_size_y:.2f} mm."""

    return msg