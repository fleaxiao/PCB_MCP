import os
import pcbnew
import xml.etree.ElementTree as ET

from logging import root
from typing import Optional
from pcb_utility import *


async def ana_board_info(board: pcbnew.BOARD) -> str:
    try:
        board_courtyard = await get_board_courtyard(board)
        if not board_courtyard:
            courtyard_info = "The board courtyard has not been defined."
        else:
            courtyard_info = f"Size: {pcbnew.ToMM(board_courtyard.GetWidth()):.2f} mm x {pcbnew.ToMM(board_courtyard.GetHeight()):.2f} mm"

        bounding_box = board.ComputeBoundingBox()
        if not bounding_box:
            return "Error: Could not compute bounding box"
        BoundingBox_center = bounding_box.GetCenter()
        BoundingBox_size = bounding_box.GetSize()
        center_x, center_y = pcbnew.ToMM(BoundingBox_center.x), pcbnew.ToMM(BoundingBox_center.y)
        width, height = pcbnew.ToMM(BoundingBox_size.x), pcbnew.ToMM(BoundingBox_size.y)
        
        num_modules = len(board.GetFootprints())
        num_nets = len(board.GetNetsByName())
        num_tracks = len([track for track in board.GetTracks() if isinstance(track, pcbnew.PCB_TRACK) and not isinstance(track, pcbnew.PCB_VIA)])
        num_vias = len([via for via in board.GetTracks() if isinstance(via, pcbnew.PCB_VIA)])

        board_info = f"""Board Information:
Board Courtyard - {courtyard_info}
Bounding Box - Center: ({center_x:.2f} mm, {center_y:.2f} mm), Size: {width:.2f} mm x {height:.2f} mm
Module - Number: {num_modules}
Net - Number: {num_nets}
Track - Number: {num_tracks}
Via - Number: {num_vias}
"""
        return board_info
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to get board info - {str(e)}"


async def ana_module_info(board: pcbnew.BOARD) -> str:
    try:
        module_info = []
        footprints = board.GetFootprints()
        
        for module in footprints:
            module_ref_i = module.GetReference()
            module_pos_x_i, module_pos_y_i = pcbnew.ToMM(module.GetPosition())
            module_angle_i = module.GetOrientationDegrees()

            footprint_name_i = module.GetFPID().GetLibItemName()
            footprint_w_i, footprint_h_i = await get_footprint_size(module)
            
            pad_info = []
            for pad in module.Pads():
                pad_num = pad.GetNumber()
                if pad.GetNetname() != "":
                    pad_net = pad.GetNetname() if pad.GetNetname() else "None"
                    pad_info.append(f"{pad_num}({pad_net})")
            
            pad_nets = ", ".join(pad_info) if pad_info else "No pads"
            module_info_i = f"Module - Ref: {module_ref_i}, Footprint: {footprint_name_i}, Size: {footprint_w_i:.2f} mm x {footprint_h_i:.2f} mm, Pads: {pad_nets}\n"

            module_info.append((module_ref_i, module_info_i))

        if not module_info:
            return ["Module Information:\nNo valid module found\n"]
        
        module_info.sort(key=lambda x: x[0])
        module_info = ["Module Information:\n"] + [info for _, info in module_info]
        
        return module_info
    
    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}\n"]
    except Exception as e:
        return [f"Error: Failed to get module info - {str(e)}\n"]


async def ana_net_info(board) -> str:
    try:
        net_info = []
        for net in board.GetNetsByName().values():
            net_code_i = net.GetNetCode()
            if net_code_i != 0:
                net_name_i = net.GetNetname()
                connected_pads = []
                for module in board.GetFootprints():
                    for pad in module.Pads():
                        if pad.GetNetCode() == net_code_i:
                            module_ref = module.GetReference()
                            pad_num = pad.GetNumber()
                            connected_pads.append(f"{module_ref}.{pad_num}")
            
                pads_str = ", ".join(connected_pads) if connected_pads else "No pads"
                net_info_i = f"Net - Code: {net_code_i}, Name: {net_name_i}, Connected Pads: {pads_str}\n"
                net_info.append((net_code_i, net_info_i))

        if not net_info:
            return ["Net Information:\nNo valid net found\n"]
    
        net_info.sort(key=lambda x: x[0])
        net_info = ["Net Information:\n"] + [info for _, info in net_info]

        return net_info

    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}\n"]
    except Exception as e:
        return [f"Error: Failed to get net info - {str(e)}\n"]


async def ana_track_info(board: pcbnew.BOARD) -> str:
    try:
        track_info = []
        for track in board.GetTracks():
            if isinstance(track, pcbnew.PCB_TRACK) and not isinstance(track, pcbnew.PCB_VIA):
                if track.GetNetname() == "":
                    net_i = "None"
                else:
                    net_i = track.GetNetname()
                start_x_i, start_y_i = pcbnew.ToMM(track.GetStart().x), pcbnew.ToMM(track.GetStart().y)
                end_x_i, end_y_i = pcbnew.ToMM(track.GetEnd().x), pcbnew.ToMM(track.GetEnd().y)
                width_i = pcbnew.ToMM(track.GetWidth())
                layer_i = track.GetLayerName()
                track_info_i = f"Track - Net: {net_i}, Start Position: ({start_x_i:.2f} mm, {start_y_i:.2f} mm), End Position: ({end_x_i:.2f} mm, {end_y_i:.2f} mm), Width: {width_i:.2f} mm, Layer: {layer_i}\n"
                track_info.append((net_i, track_info_i))

        if not track_info:
            return ["Track Information:\nNo valid track found\n"]

        track_info.sort(key=lambda x: (x[0]))
        track_info = ["Track Information:\n"] + [info for _, info in track_info]

        return track_info
    
    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}\n"]
    except Exception as e:
        return [f"Error: Failed to get track info - {str(e)}\n"]


async def ana_via_info(board: pcbnew.BOARD) -> str:
    try:
        via_info = []
        for via in board.GetTracks():
            if isinstance(via, pcbnew.PCB_VIA):
                net_i = via.GetNetname()
                pos_x_i, pos_y_i = pcbnew.ToMM(via.GetPosition().x), pcbnew.ToMM(via.GetPosition().y)
                diameter_i = pcbnew.ToMM(via.GetWidth(pcbnew.F_Cu))
                drill_i = pcbnew.ToMM(via.GetDrillValue())
                via_info_i = f"Via - Net: {net_i}, Position: ({pos_x_i:.2f} mm, {pos_y_i:.2f} mm), Diameter: {diameter_i:.2f} mm, Drill: {drill_i:.2f} mm\n"
                via_info.append((net_i, via_info_i))

        if not via_info:
            return ["Via Information:\nNo valid via found\n"]

        via_info.sort(key=lambda x: (x[0]))
        via_info = ["Via Information:\n"] + [info for _, info in via_info]

        return via_info
    
    except AttributeError as e:
        return [f"Error: Invalid board object or missing method - {str(e)}\n"]
    except Exception as e:
        return [f"Error: Failed to get via info - {str(e)}\n"]


async def save_pcb_image(file_path: str) -> str:
    try:
        board = pcbnew.LoadBoard(file_path)
        if not board:
            return f"Error: Could not load PCB from {file_path}"
        bounding_box = board.ComputeBoundingBox()
        if not bounding_box:
            return "Error: Could not compute bounding box from board"
        
        bbox_x = pcbnew.ToMM(bounding_box.GetX())
        bbox_y = pcbnew.ToMM(bounding_box.GetY())
        bbox_w = pcbnew.ToMM(bounding_box.GetWidth())
        bbox_h = pcbnew.ToMM(bounding_box.GetHeight())

        base_name = file_path.rsplit('.', 1)[0] + '.svg'
        output_dir = os.path.dirname(base_name)

        try:
            plot_controller = pcbnew.PLOT_CONTROLLER(board)
            plot_options = plot_controller.GetPlotOptions()
            plot_options.SetOutputDirectory(output_dir)
            plot_options.SetPlotFrameRef(False)
            plot_options.SetPlotValue(True)
            plot_options.SetPlotReference(True)
            plot_options.SetPlotMode(True)
            plot_options.SetColorSettings(pcbnew.GetSettingsManager().GetColorSettings("KiCad Default"))

            layers_to_plot = [pcbnew.F_Cu, pcbnew.F_SilkS, pcbnew.F_Mask, pcbnew.Edge_Cuts]
            plot_controller.OpenPlotfile("", pcbnew.PLOT_FORMAT_SVG, "")
            
            for layer in layers_to_plot:
                try:
                    plot_controller.SetLayer(layer)
                    plot_controller.SetColorMode(True)
                    plot_controller.PlotLayer()
                except Exception as e:
                    print(f"Warning: Error plotting layer {layer}: {str(e)}")
                    continue
            
            plot_controller.ClosePlot()
        except Exception as e:
            return f"Error: Failed to plot PCB: {str(e)}"

        if not os.path.exists(base_name):
            return f"Error: SVG file was not generated: {base_name}"

        try:
            tree = ET.parse(base_name)
            root = tree.getroot()
            root.set('viewBox', f"{bbox_x} {bbox_y} {bbox_w} {bbox_h}")
            root.set('width', f"{bbox_w}mm")
            root.set('height', f"{bbox_h}mm")
            tree.write(base_name, encoding='utf-8', xml_declaration=True)
        except ET.ParseError as e:
            return f"Error: Failed to parse SVG file: {str(e)}"
        except Exception as e:
            return f"Error: Failed to modify SVG file: {str(e)}"

        try:
            completed_file = f"{file_path.rsplit('.', 1)[0]}_{bbox_w:.2f}x{bbox_h:.2f}.svg"
            if os.path.exists(completed_file):
                os.remove(completed_file)
            os.rename(base_name, completed_file)
        except OSError as e:
            return f"Error: Failed to rename file: {str(e)}"

        return f"Success: Generating PCB SVG image: {completed_file}"
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to save PCB image - {str(e)}"