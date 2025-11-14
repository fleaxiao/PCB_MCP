import re
import pcbnew


async def get_footprint_courtyard(module):
    courtyard_bbox = None

    for graphic in module.GraphicalItems():
        if graphic.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            graphic_bbox = graphic.GetBoundingBox()

            if courtyard_bbox is None:
                courtyard_bbox = graphic_bbox
            else:
                courtyard_bbox.Merge(graphic_bbox)

    return courtyard_bbox


async def get_footprint_size(module):

    courtyard_bbox = await get_footprint_courtyard(module)

    if courtyard_bbox is not None:
        w = pcbnew.ToMM(courtyard_bbox.GetWidth())
        h = pcbnew.ToMM(courtyard_bbox.GetHeight())
        angle_degrees = module.GetOrientationDegrees()
        if angle_degrees == 90 or angle_degrees == -90:
            return h, w
        else:
            return w, h
    else:
        return None, None

async def get_board_courtyard(board):

    courtyard_bbox = None

    for graphic in board.GetDrawings():
        if graphic.GetLayer() == pcbnew.Edge_Cuts:
            graphic_bbox = graphic.GetBoundingBox()

            if courtyard_bbox is None:
                courtyard_bbox = graphic_bbox
            else:
                courtyard_bbox.Merge(graphic_bbox)

    return courtyard_bbox

async def get_board_size(board):
    bbox = await get_board_courtyard(board)

    w = pcbnew.ToMM(bbox.GetWidth())
    h = pcbnew.ToMM(bbox.GetHeight())
    return w, h


async def extract_table(table):
    data = {
        'headers': [],
        'rows': []
    }
    
    thead = table.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            headers = header_row.find_all(['th', 'td'])
            data['headers'] = [re.sub(r'\s+', ' ', h.get_text(strip=True)) for h in headers]
    
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [re.sub(r'\s+', ' ', cell.get_text(strip=True)) for cell in cells]
            if any(row_data):
                data['rows'].append(row_data)
    
    return data if (data['headers'] or data['rows']) else None
