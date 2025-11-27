import subprocess
import pcbnew

from pathlib import Path


def run_freerouting(file_path: str, jar_path: str, keep_connections: list = None) -> str:
    """
    Run FreeRouting on the given PCB file.

    Args:
        file_path (str): Path to the PCB file.
        jar_path (str): Path to the FreeRouting JAR file.
        keep_connections (list): List of tuples specifying pads to keep.
    """

    board = pcbnew.LoadBoard(file_path)
    pcb_file = Path(file_path).resolve()
    jar_file = Path(jar_path).resolve()
    dsn_file = pcb_file.with_suffix('.dsn')
    ses_file = dsn_file.with_suffix('.ses')

    original_nets = {}
    original_track_nets = {}
    
    if keep_connections:
        for footprint in board.GetFootprints():
            footprint_ref = footprint.GetReference()
            for pad in footprint.Pads():
                pad_num = pad.GetNumber()
                if (footprint_ref, pad_num) not in keep_connections:
                    original_nets[(footprint_ref, pad_num)] = pad.GetNetCode()
                    pad.SetNetCode(0)

        # for i, track in enumerate(board.GetTracks()):
        #     net_code = track.GetNetCode()
        #     original_track_nets[i] = net_code
        #     track.SetNetCode(0)

    pcbnew.ExportSpecctraDSN(board, str(dsn_file))

    if original_nets:
        for footprint in board.GetFootprints():
            footprint_ref = footprint.GetReference()
            for pad in footprint.Pads():
                pad_num = pad.GetNumber()
                if (footprint_ref, pad_num) in original_nets:
                    pad.SetNetCode(original_nets[(footprint_ref, pad_num)])
    
    # if original_track_nets:
    #     for i, track in enumerate(board.GetTracks()):
    #         if i in original_track_nets:
    #             track.SetNetCode(original_track_nets[i])


    cmd = [
        "java",
        "-jar", str(jar_file),
        # "--gui.enabled=false",
        "-de", str(dsn_file),
        "-do", str(ses_file),
        "-random_seed", "2",
        # "-mp", "100",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    pcbnew.ImportSpecctraSES(board, str(ses_file))
    pcbnew.SaveBoard(str(pcb_file), board)

    msg = f"FreeRouting completed. SES file saved at: {ses_file}"
    print(msg)
    return str(ses_file)


if __name__ == "__main__":
    pcb_path = r"test_board\test.kicad_pcb"
    freerouting_path = r"freerouting-2.1.0.jar"

    keep_conns = [
        ("C1", "1"), ("U1", "1")
        # ("L1", "2"), ("C2", "1"), ("J2", "1")
    ]

    ses_file = run_freerouting(
        pcb_path, 
        freerouting_path,
        keep_connections=keep_conns
    )