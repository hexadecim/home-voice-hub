"""Build the project footprint library lib/hvh.pretty (KiCad 7 format)."""
import os, re, shutil, uuid

LIB = os.path.join(os.path.dirname(__file__), "..", "lib", "hvh.pretty")
os.makedirs(LIB, exist_ok=True)
U = lambda: str(uuid.uuid4())

def write(name, body):
    with open(os.path.join(LIB, name + ".kicad_mod"), "w") as f:
        f.write(body)

def text(kind, val, x, y, layer, hide=False):
    return (f'  (fp_text {kind} "{val}" (at {x} {y}) (layer "{layer}"){" hide" if hide else ""}\n'
            f'    (effects (font (size 1 1) (thickness 0.15))))\n')

def line(x1, y1, x2, y2, layer, w=0.1):
    return f'  (fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width {w}) (type solid)) (layer "{layer}"))\n'

def rect(x1, y1, x2, y2, layer, w=0.1):
    return "".join([line(x1, y1, x2, y1, layer, w), line(x2, y1, x2, y2, layer, w),
                    line(x2, y2, x1, y2, layer, w), line(x1, y2, x1, y1, layer, w)])

# --------------------------------------------------------------------------
# 1. CM5 board-to-board receptacle, Hirose DF40C-100DS-0.4V(51)
#    Geometry identical to the Home Assistant Yellow / CM4IO carrier:
#    rows 3.08 mm apart, 0.4 mm pitch, pad 0.7 x 0.2 mm, odd pins at -x.
#    Origin = connector centre. Two instances: J10 (CM5 pins 1-100) at module
#    (-17.0, +2.5) and J11 (CM5 pins 101-200) at module (+17.0, +2.5).
# --------------------------------------------------------------------------
def df40():
    s = '(footprint "CM5_DF40C-100DS-0.4V" (version 20221018) (generator hvh_gen) (layer "F.Cu")\n'
    s += '  (descr "Hirose DF40C-100DS-0.4V(51) receptacle for Raspberry Pi CM4/CM5, 1.5mm stack. Pad geometry from HA Yellow / CM4IO")\n'
    s += '  (tags "DF40 CM5 CM4") (attr smd)\n'
    s += text("reference", "REF**", 0, -12.2, "F.SilkS") + text("value", "DF40C-100DS", 0, 12.2, "F.Fab")
    for n in range(1, 101):
        x = -1.54 if n % 2 else 1.54
        y = round(-9.8 + 0.4 * ((n - 1) // 2), 3)
        s += f'  (pad "{n}" smd rect (at {x} {y}) (size 0.7 0.2) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
    s += rect(-1.44, -11.3, 1.44, 11.3, "F.Fab")
    s += rect(-2.15, -11.55, 2.15, 11.55, "F.CrtYd", 0.05)
    # pin-1 marker + silk end brackets
    s += line(-2.1, -10.25, -2.1, -9.6, "F.SilkS", 0.12)
    s += line(-1.6, -11.45, 1.6, -11.45, "F.SilkS", 0.12) + line(-1.6, 11.45, 1.6, 11.45, "F.SilkS", 0.12)
    s += ')\n'
    write("CM5_DF40C-100DS-0.4V", s)

# --------------------------------------------------------------------------
# 2. CM5 module mechanical: 4x M2.5 holes, outline, antenna ground cut-out,
#    "no components under module" keep-outs (connectors excluded).
#    Module frame: x +/-20, y +/-27.5. Antenna edge is +y (pins 99/100 end),
#    on the J10 (pins 1-100) side: cut-out x -13..+3, y +21..+27.5, all copper
#    (from the official CM5IO layout: 16 x 6.5 mm copper-free area at the edge).
# --------------------------------------------------------------------------
def zone_keepout(pts, layers, name, tracks="not_allowed", vias="not_allowed", pads="not_allowed",
                 pour="not_allowed", footprints="allowed"):
    p = " ".join(f"(xy {x} {y})" for x, y in pts)
    return (f'  (zone (net 0) (net_name "") (layers {layers}) (name "{name}") (hatch edge 0.508)\n'
            f'    (connect_pads (clearance 0)) (min_thickness 0.254) (filled_areas_thickness no)\n'
            f'    (keepout (tracks {tracks}) (vias {vias}) (pads {pads}) (copperpour {pour}) (footprints {footprints}))\n'
            f'    (fill (thermal_gap 0.508) (thermal_bridge_width 0.508))\n'
            f'    (polygon (pts {p})))\n')

def cm5mech():
    s = '(footprint "CM5_Module_Mechanical" (version 20221018) (generator hvh_gen) (layer "F.Cu")\n'
    s += '  (descr "Raspberry Pi Compute Module 5 outline, M2.5 holes, antenna copper cut-out. Not assembled.")\n'
    s += '  (tags "CM5 CM4 module") (attr board_only exclude_from_pos_files exclude_from_bom)\n'
    s += text("reference", "REF**", 0, -29, "F.SilkS", hide=True) + text("value", "CM5", 0, 0, "F.Fab")
    for x in (-16.5, 16.5):
        for y in (-24, 24):
            s += f'  (pad "" np_thru_hole circle (at {x} {y}) (size 2.7 2.7) (drill 2.7) (layers "*.Cu" "*.Mask"))\n'
    s += rect(-20, -27.5, 20, 27.5, "F.Fab")
    s += rect(-20, -27.5, 20, 27.5, "Dwgs.User", 0.12)
    s += text("user", "CM5 ANTENNA - KEEP COPPER FREE", -5, 25.2, "Dwgs.User")
    # Antenna copper cut-out, every copper layer
    s += zone_keepout([(-13, 21), (3, 21), (3, 27.5), (-13, 27.5)], '"*.Cu"', "CM5_ANTENNA_CUTOUT",
                      footprints="not_allowed")
    # Components may not be placed under the module (1.5 mm stack, no clearance).
    # Areas: everything inside the outline except the two connector strips.
    regions = [((-20, -27.5), (-19.2, 27.5)),   # left of J10 courtyard
               ((-14.8, -27.5), (14.8, 27.5)),  # between connectors
               ((19.2, -27.5), (20, 27.5)),     # right of J11
               ((-19.2, -27.5), (-14.8, -9.1)), ((-19.2, 14.1), (-14.8, 27.5)),
               ((14.8, -27.5), (19.2, -9.1)), ((14.8, 14.1), (19.2, 27.5))]
    for i, ((x1, y1), (x2, y2)) in enumerate(regions):
        s += zone_keepout([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], '"F.Cu"', f"CM5_NO_PARTS_{i}",
                          tracks="allowed", vias="allowed", pads="allowed", pour="allowed", footprints="not_allowed")
    s += ')\n'
    write("CM5_Module_Mechanical", s)

# --------------------------------------------------------------------------
# 3. MGM210P from the open-source HA Yellow library (CERN-OHL-W)
# --------------------------------------------------------------------------
def mgm210p():
    src = "/home/claude/ext/yellow/Yellow.pretty/SiliconLabs_MGM210P.kicad_mod"
    s = open(src).read()
    s = s.replace('(descr "', '(descr "Source: NabuCasa/yellow (CERN-OHL-W). ', 1)
    s = s.rstrip().rstrip(')') + rect(-6.95, -7.6, 6.95, 7.6, "F.CrtYd", 0.05) + ')\n'
    write("SiliconLabs_MGM210P", s)

# --------------------------------------------------------------------------
# 4. HanRun HR911130A gigabit MagJack (LCSC C54408 EasyEDA land pattern,
#    two independent copies cross-checked). Pegs converted to NPTH.
#    Front (opening) at y = -12.9; pins at y +4.35 / +6.89.
# --------------------------------------------------------------------------
def hr911130a():
    src = "/home/claude/dl/fp/hr911130a_ato.kicad_mod"
    body = open(src).read()
    pads = re.findall(r'\(pad\s+"?([^"\s]*)"?\s+thru_hole\s+(\w+)\s+\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s+\(size ([-\d.]+) ([-\d.]+)\)\s+\(drill ([-\d.]+)\)', body)
    s = '(footprint "RJ45_HanRun_HR911130A" (version 20221018) (generator hvh_gen) (layer "F.Cu")\n'
    s += '  (descr "HanRun HR911130A 10/100/1000 RJ45 MagJack with LEDs, LCSC C54408 land pattern")\n'
    s += '  (tags "RJ45 magjack gigabit") (attr through_hole)\n'
    s += text("reference", "REF**", 0, 10.0, "F.SilkS") + text("value", "HR911130A", 0, 0, "F.Fab")
    for name, shape, x, y, w, h, d in pads:
        x = -float(x); y = -float(y)      # source had 180 deg pad rotation -> mirror both axes back
        if name == "":
            s += f'  (pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size 3.25 3.25) (drill 3.25) (layers "*.Cu" "*.Mask"))\n'
        else:
            sh = "rect" if name == "P1" else "circle"
            s += f'  (pad "{name}" thru_hole {sh} (at {x:.3f} {y:.3f}) (size {w} {h}) (drill {float(d):.2f}) (layers "*.Cu" "*.Mask"))\n'
    # body: original silk -8.02..8.02, -12.9..8.4 (before mirror) => after mirror y in [-8.4, 12.9]
    s += rect(-8.02, -8.4, 8.02, 12.9, "F.Fab")
    s += rect(-8.3, -8.7, 8.3, 13.2, "F.CrtYd", 0.05)
    s += line(-8.1, -8.5, 8.1, -8.5, "F.SilkS", 0.12)
    s += text("user", "FRONT", 0, 12.0, "F.Fab")
    s += ')\n'
    write("RJ45_HanRun_HR911130A", s)

# --------------------------------------------------------------------------
# 5. Amphenol GSB311131HR USB3.0 A (SnapEDA, cross-checked with 2nd library)
#    Mating face at y = +13.78.
# --------------------------------------------------------------------------
def gsb():
    src = "/home/claude/dl/fp/gsb_snap.kicad_mod"
    body = open(src).read()
    pads = re.findall(r'\(pad\s+"?([^"\s]*)"?\s+thru_hole\s+(\w+)\s+\(at ([-\d.]+) ([-\d.]+)\)\s+\(size ([-\d.]+) ([-\d.]+)\)\s+\(drill ([-\d.]+)\)', body)
    s = '(footprint "USB3_A_Amphenol_GSB311131HR" (version 20221018) (generator hvh_gen) (layer "F.Cu")\n'
    s += '  (descr "Amphenol GSB311131HR USB 3.0 Type-A receptacle, right angle THT")\n'
    s += '  (tags "USB3 Type-A") (attr through_hole)\n'
    s += text("reference", "REF**", -4.5, -4.2, "F.SilkS") + text("value", "GSB311131HR", 0, 8, "F.Fab")
    for name, shape, x, y, w, h, d in pads:
        sh = "rect" if name == "1" else "circle"
        s += f'  (pad "{name}" thru_hole {sh} (at {x} {y}) (size {w} {h}) (drill {d}) (layers "*.Cu" "*.Mask"))\n'
    s += rect(-6.95, -2.72, 6.95, 13.78, "F.Fab")
    s += rect(-8.5, -2.97, 8.5, 14.03, "F.CrtYd", 0.05)
    s += line(-6.95, -2.72, 6.95, -2.72, "F.SilkS", 0.12)
    s += text("user", "FRONT", 0, 12.5, "F.Fab")
    s += ')\n'
    write("USB3_A_Amphenol_GSB311131HR", s)

# --------------------------------------------------------------------------
# 6. ZILLTEK ZTS6216 analog MEMS mic, 2.75 x 1.85 mm, top port
#    (LCSC C481302 land pattern). 1 OUT, 2 GND, 3 GND, 4 VDD.
# --------------------------------------------------------------------------
def zts6216():
    s = '(footprint "MIC_ZTS6216" (version 20221018) (generator hvh_gen) (layer "F.Cu")\n'
    s += '  (descr "ZILLTEK ZTS6216 analog MEMS microphone, top port, 2.75x1.85mm (LCSC C481302)")\n'
    s += '  (tags "MEMS microphone") (attr smd)\n'
    s += text("reference", "REF**", 0, -2.3, "F.SilkS") + text("value", "ZTS6216", 0, 2.3, "F.Fab")
    for n, (x, y) in {"1": (-0.53, -0.99), "2": (-0.53, 0.99), "3": (0.53, 0.99), "4": (0.53, -0.99)}.items():
        s += f'  (pad "{n}" smd rect (at {x} {y}) (size 0.6 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))\n'
    s += rect(-0.925, -1.375, 0.925, 1.375, "F.Fab")
    s += rect(-1.2, -1.65, 1.2, 1.65, "F.CrtYd", 0.05)
    s += line(-1.1, -1.55, -0.6, -1.55, "F.SilkS", 0.12)
    s += f'  (fp_circle (center 0 0) (end 0.35 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.Fab"))\n'
    s += ')\n'
    write("MIC_ZTS6216", s)

if __name__ == "__main__":
    df40(); cm5mech(); mgm210p(); hr911130a(); gsb(); zts6216()
    print(sorted(os.listdir(LIB)))
