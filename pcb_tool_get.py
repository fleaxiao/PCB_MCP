import os
import re
import requests
import pcbnew
import xml.etree.ElementTree as ET

from logging import root
from typing import Optional
from bs4 import BeautifulSoup
from pcb_utility import *
from pcb_utility import *


async def spider_datasheet_info(url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        infos = []
        links = soup.find_all('a', attrs={
            'class': 'no-children',
            'data-navtitle': re.compile(r'(description|pin|layout guidelines)', re.IGNORECASE)
        })
        
        for link in links:
            href = link.get('href', '')
            section_title = link.get('data-navtitle', '')

            full_url = url if not href.startswith('http') else href
            if not href.startswith('http'):
                full_url = f"https:{href}" if href.startswith('/') else f"{url.rstrip('/')}/{href}"

            detail_response = requests.get(full_url, headers=headers, timeout=10)
            detail_response.raise_for_status()
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            content_div = detail_soup.find('div', {'class': 'subsection'})

            if content_div:
                all_subsections = detail_soup.find_all('div', {'class': 'subsection'})
                target_div = None
                
                for subsection in all_subsections:
                    header = subsection.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    
                    if header and section_title.lower() in header.get_text().lower():
                        target_div = subsection
                        break
                
                if target_div:
                    paragraphs_data = []
                    lists_data = []
                    tables_data = []
                    for p in target_div.find_all('p'):
                        text_info = p.get_text(separator=' ', strip=True)
                        text_info = re.sub(r'\s+', ' ', text_info)
                        text_info = text_info.strip()
                        if text_info:
                            paragraphs_data.append(text_info)
                    for li in target_div.find_all('li'):
                        text_info = li.get_text(separator=' ', strip=True)
                        text_info = re.sub(r'\s+', ' ', text_info)
                        text_info = text_info.strip()
                        if text_info:
                            lists_data.append(text_info)
                    for table in content_div.find_all('table'):
                        table_info = await extract_table(table)
                        if table_info:
                            tables_data.append(table_info)
                    info = {
                        'section': section_title,
                        'paragraphs': paragraphs_data,
                        'lists': lists_data,
                        'tables': tables_data
                    }
                    infos.append(info)

        return infos

    except Exception as e:
        print(f"Error reading page: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def ana_board_env(board: pcbnew.BOARD) -> str:
    try:
        board_courtyard = await get_board_courtyard(board)
        if not board_courtyard:
            courtyard_info = "The board courtyard has not been defined."
        else:
            courtyard_info = f"Center: ({pcbnew.ToMM(board_courtyard.GetCenter().x):.2f} mm, {pcbnew.ToMM(board_courtyard.GetCenter().y):.2f} mm), Size: {pcbnew.ToMM(board_courtyard.GetWidth()):.2f} mm x {pcbnew.ToMM(board_courtyard.GetHeight()):.2f} mm"

        bounding_box = board.ComputeBoundingBox()
        if not bounding_box:
            return "Error: Could not compute bounding box"
        BoundingBox_center = bounding_box.GetCenter()
        BoundingBox_size = bounding_box.GetSize()
        center_x, center_y = pcbnew.ToMM(BoundingBox_center.x), pcbnew.ToMM(BoundingBox_center.y)
        width, height = pcbnew.ToMM(BoundingBox_size.x), pcbnew.ToMM(BoundingBox_size.y)
        
        board_info = f"""Board Information:
Board Courtyard - {courtyard_info}
Module Bounding Box - Center: ({center_x:.2f} mm, {center_y:.2f} mm), Size: {width:.2f} mm x {height:.2f} mm
"""
        return board_info
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to get board info - {str(e)}"


async def ana_module_env(board: pcbnew.BOARD) -> str:
    try:
        module_info = []
        footprints = board.GetFootprints()
        
        for module in footprints:
            module_ref_i = module.GetReference()

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


async def ana_net_env(board) -> str:
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


async def ana_track_env(board: pcbnew.BOARD) -> str:
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


async def ana_via_env(board: pcbnew.BOARD) -> str:
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


async def export_pcb_image(file_path: str) -> str:
    try:
        board = pcbnew.LoadBoard(file_path)
        bounding_box = board.ComputeBoundingBox()

        bbox_x = pcbnew.ToMM(bounding_box.GetX())
        bbox_y = pcbnew.ToMM(bounding_box.GetY())
        bbox_w = pcbnew.ToMM(bounding_box.GetWidth())
        bbox_h = pcbnew.ToMM(bounding_box.GetHeight())

        base_name = file_path.rsplit('.', 1)[0] + '.svg'
        output_dir = os.path.dirname(base_name)

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

        tree = ET.parse(base_name)
        root = tree.getroot()
        root.set('viewBox', f"{bbox_x} {bbox_y} {bbox_w} {bbox_h}")
        root.set('width', f"{bbox_w}mm")
        root.set('height', f"{bbox_h}mm")
        tree.write(base_name, encoding='utf-8', xml_declaration=True)

        completed_name = f"{file_path.rsplit('.', 1)[0]}_{bbox_w:.2f}x{bbox_h:.2f}.svg"
        if os.path.exists(completed_name):
            os.remove(completed_name)
        os.rename(base_name, completed_name)

        return f"Success: Generating PCB SVG image: {completed_name}\n"
    
    except AttributeError as e:
        return f"Error: Invalid board object or missing method - {str(e)}"
    except Exception as e:
        return f"Error: Failed to save PCB image - {str(e)}"