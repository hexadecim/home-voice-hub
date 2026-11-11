"""Create hvh.kicad_pcb: outline, stack-up, footprints with nets, placement, zones.

Run with KiCad's python:  /usr/bin/python3 pcb_place.py
Board-local coordinates (mm): x right, y down, origin = rear-left corner.
Rear edge (y=0) carries the I/O connectors; front edge (y=80) carries the
CM5 antenna end, microphone, LEDs, buttons and microSD.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import pcbnew
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.join(HERE, "..", "kicad")
PCB = os.path.join(KDIR, "hvh.kicad_pcb")
OX, OY = 100.0, 100.0          # sheet offset
W, H, RC = 100.0, 80.0, 3.0    # board size, corner radius
mm = pcbnew.FromMM
def P(x, y): return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))

# --------------------------------------------------------------------------
# placement: ref -> (x, y, rotation_deg, side)   side 'F' or 'B'
# --------------------------------------------------------------------------
PLACE = {
    # rear-edge I/O (connector fronts protrude 1.0 mm past the edge)
    "J1": (12.5, 2.65, 180, "F"),   "J4": (28.0, 12.78, 180, "F"),
    "J2": (63.0, 11.90, 180, "F"),  "J3": (84.0, 12.78, 180, "F"),
    # CM5 (module 56..96 x 25..80; antenna end on the front edge)
    "M1": (76.0, 52.5, 0, "F"), "J10": (59.0, 55.0, 0, "F"), "J11": (93.0, 55.0, 0, "F"),
    # power input
    "D1": (9.5, 10.0, 0, "F"), "C1": (9.5, 13.2, 0, "F"), "C2": (9.5, 16.2, 0, "F"),
    "U1": (14.8, 10.6, 0, "F"), "C3": (14.8, 13.8, 0, "F"),
    "U2": (46.0, 20.5, 0, "F"), "C4": (42.7, 20.5, 90, "F"), "C5": (49.4, 20.5, 90, "F"), "C6": (51.3, 20.5, 90, "F"),
    # USB-A #2 (hub port 1) support
    "U4": (40.5, 8.5, 0, "F"), "R3": (40.5, 12.0, 0, "F"), "C15": (45.2, 8.5, 90, "F"), "C16": (47.8, 8.5, 90, "F"),
    "U15": (28.0, 18.2, 90, "F"),
    # USB-A #1 (USB3) support
    "U3": (74.2, 22.0, 0, "F"), "R2": (74.2, 18.6, 0, "F"), "C12": (78.6, 21.8, 90, "F"),
    "U5": (93.5, 19.6, 0, "F"), "U6": (84.0, 18.6, 90, "F"),
    "C13": (82.5, 23.3, 0, "F"), "C14": (86.5, 23.3, 0, "F"),
    # Ethernet support (band between RJ45 and module)
    "U14": (59.2, 22.8, 90, "F"), "U13": (65.5, 22.8, 90, "F"),
    "C42": (68.3, 22.0, 0, "F"), "C43": (68.3, 23.7, 0, "F"),
    "R23": (73.6, 4.2, 90, "F"), "R24": (52.6, 4.2, 90, "F"),
    # hub
    "U7": (40.0, 31.5, 0, "F"), "Y1": (34.0, 28.5, 90, "F"), "R4": (35.0, 36.0, 0, "F"),
    "C20": (45.6, 28.3, 0, "F"), "C19": (45.2, 30.0, 0, "F"), "C21": (45.2, 31.4, 0, "F"), "C18": (45.6, 33.0, 0, "F"),
    "R5": (45.2, 34.6, 0, "F"), "C17": (45.2, 35.8, 0, "F"), "R6": (45.2, 37.0, 0, "F"), "R7": (45.2, 38.2, 0, "F"),
    "R8": (45.2, 26.2, 0, "F"),
    # Zigbee radio (antenna at the left edge) + USB-UART
    "U11": (7.6, 33.0, 90, "F"), "U10": (21.5, 30.5, 0, "F"),
    "R17": (26.5, 28.5, 0, "F"), "R18": (26.5, 30.0, 0, "F"), "R19": (21.5, 36.2, 0, "F"),
    "C38": (20.0, 34.6, 0, "F"), "C39": (22.4, 34.6, 0, "F"),
    "C40": (16.8, 36.0, 90, "F"), "C41": (16.8, 33.2, 90, "F"),
    "R20": (5.7, 24.5, 0, "F"), "R21": (3.3, 41.5, 90, "F"), "SW3": (8.0, 45.5, 0, "F"),
    # audio codec
    "U8": (24.0, 47.5, 0, "F"), "Y2": (15.0, 49.0, 90, "F"), "R10": (12.2, 51.0, 90, "F"),
    "C22": (15.0, 44.8, 0, "F"), "C23": (15.0, 53.2, 0, "F"),
    "R9": (23.8, 40.0, 0, "F"), "C25": (27.5, 40.0, 0, "F"), "C29": (30.6, 40.0, 0, "F"),
    "C26": (31.2, 44.4, 0, "F"), "FB1": (34.6, 44.4, 0, "F"),
    "C27": (31.0, 46.6, 0, "F"), "C28": (31.0, 47.8, 0, "F"), "C24": (31.0, 49.6, 0, "F"), "C32": (31.0, 51.0, 0, "F"),
    # amplifier + speaker connector
    "U9": (36.5, 56.0, 0, "F"), "R14": (35.0, 52.6, 0, "F"), "C33": (37.6, 52.6, 0, "F"),
    "C34": (28.4, 54.8, 0, "F"), "R15": (30.9, 54.8, 0, "F"), "C35": (28.4, 56.6, 0, "F"), "R16": (30.9, 56.6, 0, "F"),
    "C36": (36.5, 59.6, 0, "F"), "C37": (40.6, 56.0, 90, "F"),
    "J6": (44.0, 51.6, 0, "F"),
    # microphone + privacy switch + front LEDs + power button
    "MK1": (30.6, 75.5, 0, "F"), "R11": (24.2, 73.6, 0, "F"), "R12": (27.4, 73.6, 0, "F"),
    "C30": (30.6, 72.2, 0, "F"), "C31": (33.6, 72.2, 0, "F"), "SW4": (24.2, 77.6, 0, "F"),
    "D2": (8.6, 77.8, 180, "F"), "D3": (11.7, 77.8, 180, "F"), "D4": (14.8, 77.8, 180, "F"), "D5": (17.9, 77.8, 180, "F"),
    "R26": (8.6, 75.4, 180, "F"), "R27": (11.7, 75.4, 180, "F"), "R22": (14.8, 75.4, 180, "F"), "R13": (17.9, 75.4, 180, "F"),
    "SW1": (38.2, 75.6, 0, "F"),
    # microSD (card enters from the front edge)
    "J5": (49.0, 73.6, 0, "F"), "U12": (45.5, 64.5, 0, "F"), "R25": (42.2, 64.5, 90, "F"),
    "C44": (49.2, 64.5, 90, "F"), "C45": (50.9, 64.5, 90, "F"), "C46": (45.5, 61.2, 0, "F"),
    # CM5 power decoupling (outside the module edge, next to J10 power pins)
    "C7": (40.0, 62.2, 0, "F"), "C8": (39.4, 65.6, 0, "F"),
    "C10": (54.6, 51.2, 90, "F"), "C11": (54.6, 53.6, 90, "F"), "R1": (52.6, 53.6, 90, "F"),
    # UI / mech
    "SW2": (51.0, 29.6, 0, "F"), "J7": (51.0, 38.5, 270, "F"), "R28": (45.2, 39.4, 0, "F"),
    "J8": (51.0, 46.5, 270, "F"),
    "H1": (3.5, 3.5, 0, "F"), "H2": (96.5, 3.5, 0, "F"), "H3": (3.5, 76.5, 0, "F"), "H4": (3.5, 61.0, 0, "F"),
    "FID1": (2.2, 22.5, 0, "F"), "FID2": (2.2, 66.5, 0, "F"), "FID3": (98.3, 72.0, 0, "F"),
    # test points: bottom side, next to the signals they probe
    "TP1": (52.6, 50.6, 0, "B"), "TP2": (52.6, 48.4, 0, "B"), "TP3": (70.0, 40.0, 0, "B"),
    "TP4": (72.6, 40.0, 0, "B"), "TP5": (75.2, 40.0, 0, "B"), "TP6": (41.0, 68.4, 0, "B"),
    "TP7": (5.0, 42.0, 0, "B"), "TP8": (7.4, 42.0, 0, "B"), "TP9": (5.7, 24.0, 0, "B"),
    "TP10": (9.8, 42.0, 0, "B"), "TP11": (12.2, 42.0, 0, "B"), "TP12": (35.4, 22.6, 0, "B"), "TP13": (37.8, 22.6, 0, "B"),
}

def lib_path(lib):
    return os.path.join(HERE, "..", "lib", "hvh.pretty") if lib == "hvh" else f"/usr/share/kicad/footprints/{lib}.pretty"

def write_project():
    classes = [
        dict(name="Default", clearance=0.15, track_width=0.15, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.2, diff_pair_gap=0.15),
        dict(name="Power", clearance=0.15, track_width=0.8, via_diameter=0.8, via_drill=0.4, diff_pair_width=0.2, diff_pair_gap=0.15),
        dict(name="Power3V3", clearance=0.15, track_width=0.4, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.2, diff_pair_gap=0.15),
        dict(name="USB3", clearance=0.15, track_width=0.16, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.16, diff_pair_gap=0.15),
        dict(name="USB2", clearance=0.15, track_width=0.16, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.16, diff_pair_gap=0.15),
        dict(name="ETH", clearance=0.15, track_width=0.14, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.14, diff_pair_gap=0.15),
        dict(name="Ground", clearance=0.15, track_width=0.25, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.2, diff_pair_gap=0.15),
        dict(name="Speaker", clearance=0.2, track_width=0.5, via_diameter=0.6, via_drill=0.3, diff_pair_width=0.2, diff_pair_gap=0.15),
    ]
    for c in classes:
        c.update(microvia_diameter=0.3, microvia_drill=0.1, wire_width=6, bus_width=12, line_style=0,
                 pcb_color="rgba(0, 0, 0, 0.000)", schematic_color="rgba(0, 0, 0, 0.000)")
    assign = {}
    for name, (p, n, cls) in D.DIFF_PAIRS.items():
        assign[p] = cls; assign[n] = cls
    for net in ("+5V", "USB1_VBUS", "USB2_VBUS"): assign[net] = "Power"
    assign["GND"] = "Ground"
    for net in ("+3V3", "+3V3A", "SD_VDD", "HUB_3V3", "+5V_AUD", "CODEC_REGV", "MIC_VDD", "MIC_VDD_F"): assign[net] = "Power3V3"
    for net in ("SPK_P", "SPK_N"): assign[net] = "Speaker"
    pro = {
        "board": {"design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                         "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.15,
                         "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
            "rules": {"min_clearance": 0.1, "min_track_width": 0.1, "min_via_diameter": 0.3, "min_via_annular_width": 0.1,
                      "min_through_hole_diameter": 0.15, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.2,
                      "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_text_height": 0.8,
                      "min_text_thickness": 0.12, "solder_mask_to_copper_clearance": 0.0, "max_error": 0.005,
                      "use_height_for_length_calcs": True, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
                      "allow_blind_buried_vias": False, "allow_microvias": False},
            "track_widths": [0.0, 0.15, 0.2, 0.25, 0.4, 0.8, 1.2],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}],
            "diff_pair_dimensions": [{"gap": 0.0, "via_gap": 0.0, "width": 0.0}, {"gap": 0.15, "via_gap": 0.25, "width": 0.25},
                                     {"gap": 0.15, "via_gap": 0.25, "width": 0.2}],
            "meta": {"version": 2}}},
        "net_settings": {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                         "netclass_assignments": assign, "netclass_patterns": []},
        "meta": {"filename": "hvh.kicad_pro", "version": 1},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [], "text_variables": {},
        "pcbnew": {"page_layout_descr_file": ""},
    }
    with open(os.path.join(KDIR, "hvh.kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
    return assign

def outline(board):
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    def arc(c, start, angle):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(P(*c)); s.SetStart(P(*start)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    r = RC
    seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
    arc((W - r, r), (W - r, 0), 90); arc((W - r, H - r), (W, H - r), 90)
    arc((r, H - r), (r, H), 90); arc((r, r), (0, r), 90)

def add_zone(board, net, layer, pts, priority=0, name="", clearance=0.25, min_w=0.25, thermal=True):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net is not None:
        z.SetNet(board.FindNet(net))
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(min_w))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name: z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts: ol.Append(mm(OX + x), mm(OY + y))
    board.Add(z)
    return z

def build():
    assign = write_project()
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(6)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    # nets
    nets = D.nets()
    for n in sorted(nets):
        board.Add(pcbnew.NETINFO_ITEM(board, n))
    # footprints
    cache = {}
    for c in D.COMPONENTS:
        p = D.P[c["part"]]
        lib, name = p["fp"].split(":")
        fp = pcbnew.FootprintLoad(lib_path(lib), name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c["ref"]); fp.SetValue(p["value"])
        for k in ("lcsc", "mpn", "mfr"):
            if p[k]: fp.SetProperty({"lcsc": "LCSC", "mpn": "MPN", "mfr": "Manufacturer"}[k], p[k])
        if not p["bom"]:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp)
        x, y, rot, side = PLACE[c["ref"]]
        fp.SetPosition(P(x, y))
        if side == "B":
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            num = pad.GetNumber()
            net = c["pins"].get(num)
            if net and net != "NC":
                pad.SetNet(board.FindNet(net))
    # outline
    outline(board)
    # zones: L2 In1 = solid GND, L3 In2 = low-speed signals, L4 In3 = +5V plane, L5 In4 = solid GND, outer layers GND fill
    full = [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]
    add_zone(board, "GND", pcbnew.In1_Cu, full, 0, "GND_L2", thermal=False)
    add_zone(board, "+5V", pcbnew.In3_Cu, full, 0, "P5V_L4", thermal=False)
    add_zone(board, "GND", pcbnew.In4_Cu, full, 0, "GND_L5", thermal=False)
    add_zone(board, "GND", pcbnew.F_Cu, full, 0, "GND_TOP")
    add_zone(board, "GND", pcbnew.B_Cu, full, 0, "GND_BOT")
    pcbnew.SaveBoard(PCB, board)
    print("placed", len(D.COMPONENTS), "footprints;", len(nets), "nets")

if __name__ == "__main__":
    build()
