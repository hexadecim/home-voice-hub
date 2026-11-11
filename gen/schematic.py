"""Generate KiCad 7 symbol library + hierarchical schematic from design.py."""
import os, sys, uuid, math, datetime
sys.path.insert(0, os.path.dirname(__file__))
import design as D

OUT = os.path.join(os.path.dirname(__file__), "..", "kicad")
PROJ = "hvh"
os.makedirs(OUT, exist_ok=True)
G = 2.54
def U(): return str(uuid.uuid4())
def q(s): return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
def snap(v): return round(round(v / 1.27) * 1.27, 2)

REV = "1.0"
DATE = datetime.date.today().isoformat()
TITLE = "HVH-1 Home Voice Hub (CM5 carrier)"

# ---------------------------------------------------------------- symbols
class Sym:
    """Generated symbol: name, pins [(num,name,type,side)], geometry."""
    def __init__(self, name, pins, ref="U", kind="box", power=False):
        self.name, self.pins, self.ref, self.kind, self.power = name, pins, ref, kind, power
        self.pinpos = {}   # num -> (x, y, angle) lib coords (connection point)
        self.build()

    def build(self):
        if self.kind == "box":
            L = [p for p in self.pins if p[3] == "L"]
            R = [p for p in self.pins if p[3] == "R"]
            B = [p for p in self.pins if p[3] == "B"]
            T = [p for p in self.pins if p[3] == "T"]
            n = max(len(L), len(R), 1)
            maxl = max([len(p[1]) for p in L] + [1]); maxr = max([len(p[1]) for p in R] + [1])
            w = max(math.ceil((maxl + maxr) * 1.27 * 0.62 / G + 2) * G, (max(len(B), len(T)) + 1) * G, 5 * G)
            if w % (2 * G): w += G
            h = (n + 1) * G
            self.w, self.h = w, h
            x0, y0 = -w / 2, h / 2
            self.body = (x0, y0, w / 2, -h / 2)
            for i, p in enumerate(L):
                self.pinpos[p[0]] = (x0 - G, y0 - G * (i + 1), 0)
            for i, p in enumerate(R):
                self.pinpos[p[0]] = (w / 2 + G, y0 - G * (i + 1), 180)
            nb = len(B)
            for i, p in enumerate(B):
                x = (i - (nb - 1) / 2) * G
                x = round(x / G) * G if nb % 2 else (round((x - G / 2) / G) * G + G / 2 if False else round(x / G) * G)
                self.pinpos[p[0]] = (x if nb > 1 else 0, -h / 2 - G, 90)
            # de-duplicate bottom pin x positions (stack along x on grid)
            if nb:
                xs = [(i - (nb // 2)) * G for i in range(nb)]
                for i, p in enumerate(B):
                    self.pinpos[p[0]] = (xs[i], -h / 2 - G, 90)
            for i, p in enumerate(T):
                xs = [(i - (len(T) // 2)) * G for i in range(len(T))]
                self.pinpos[p[0]] = (xs[i], h / 2 + G, 270)
        else:  # two-terminal vertical: pin1 top, pin2 bottom
            self.w, self.h = 2 * G, 2 * G
            self.pinpos = {"1": (0, 3.81, 270), "2": (0, -3.81, 90)}

    def bbox(self):
        xs = [p[0] for p in self.pinpos.values()] + [-self.w / 2, self.w / 2]
        ys = [p[1] for p in self.pinpos.values()] + [-self.h / 2, self.h / 2]
        return min(xs), min(ys), max(xs), max(ys)

    def lib(self):
        nm = self.name.split(":")[1]
        s = f'    (symbol {q(self.name)}'
        if self.power: s += ' (power)'
        if self.kind == "two": s += ' (pin_numbers hide) (pin_names (offset 0) hide)'
        elif self.power: s += ' (pin_names (offset 0) hide)'
        else: s += ' (pin_names (offset 0.762))'
        s += ' (in_bom yes) (on_board yes)\n'
        top = self.h / 2 + 1.27
        s += f'      (property "Reference" {q(self.ref)} (at {-self.w/2 if self.kind=="box" else 2.54} {top + (0.5 if self.kind=="box" else -2.5)} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        s += f'      (property "Value" {q(nm)} (at {-self.w/2 if self.kind=="box" else 2.54} {-top - (0.5 if self.kind=="box" else -2.5)} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        s += '      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        s += '      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        s += f'      (symbol "{nm}_0_1"\n'
        s += self.graphics()
        s += '      )\n'
        s += f'      (symbol "{nm}_1_1"\n'
        for num, name, typ, side in self.pins:
            x, y, a = self.pinpos[num]
            hide = " hide" if self.power else ""
            s += (f'        (pin {typ} line (at {x:.2f} {y:.2f} {a}) (length {0 if self.power else 2.54}){hide}\n'
                  f'          (name {q(name)} (effects (font (size 1.016 1.016))))\n'
                  f'          (number {q(num)} (effects (font (size 1.016 1.016)))))\n')
        s += '      )\n    )\n'
        return s

    def graphics(self):
        st = '(stroke (width 0.254) (type default))'
        if self.kind == "box":
            x0, y0, x1, y1 = self.body
            return f'        (rectangle (start {x0:.2f} {y0:.2f}) (end {x1:.2f} {y1:.2f}) {st} (fill (type background)))\n'
        g = self.glyph
        if g == "R":
            return f'        (rectangle (start -1.016 2.54) (end 1.016 -2.54) {st} (fill (type none)))\n        (polyline (pts (xy 0 2.54) (xy 0 1.27)) {st} (fill (type none)))\n'
        if g == "C":
            return (f'        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n'
                    f'        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n'
                    f'        (polyline (pts (xy 0 1.27) (xy 0 0.762)) {st} (fill (type none)))\n'
                    f'        (polyline (pts (xy 0 -0.762) (xy 0 -1.27)) {st} (fill (type none)))\n')
        if g == "LED":   # anode = pin 2 (bottom) ... drawn pointing to pin 1 (cathode, top)
            return (f'        (polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27) (xy 0 1.016) (xy -1.27 -1.27)) {st} (fill (type none)))\n'
                    f'        (polyline (pts (xy -1.27 1.016) (xy 1.27 1.016)) {st} (fill (type none)))\n'
                    f'        (polyline (pts (xy 1.778 0) (xy 3.048 0.762)) {st} (fill (type none)))\n'
                    f'        (polyline (pts (xy 1.778 -0.762) (xy 3.048 0)) {st} (fill (type none)))\n')
        if g == "TVS":
            return (f'        (polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27) (xy 0 1.016) (xy -1.27 -1.27)) {st} (fill (type none)))\n'
                    f'        (polyline (pts (xy -1.778 1.524) (xy -1.27 1.016) (xy 1.27 1.016) (xy 1.778 0.508)) {st} (fill (type none)))\n')
        if g == "FB":
            return f'        (polyline (pts (xy -1.6 0.4) (xy -0.4 2.2) (xy 1.6 -0.4) (xy 0.4 -2.2) (xy -1.6 0.4)) {st} (fill (type none)))\n'
        if g == "FLAG":
            return f'        (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) {st} (fill (type none)))\n'
        return ""

def two(name, glyph, ref, t1="passive", t2="passive"):
    s = Sym(name, [("1", "~", t1, "T"), ("2", "~", t2, "B")], ref, kind="two")
    s.glyph = glyph
    return s

SYMS = {}
for key, sd in D.SYM.items():
    pins = []
    for p in sd["pins"]:
        num, name, typ, side = p
        if key in ("CM5_A", "CM5_B") and name == "CM5_3V3_OUT":
            typ = "passive"
        pins.append((num, name, typ, side))
    SYMS[key] = Sym("hvh:" + key, pins, sd["ref"])
SYMS["R"] = two("hvh:R", "R", "R")
SYMS["C"] = two("hvh:C", "C", "C")
SYMS["LED"] = two("hvh:LED", "LED", "D")      # pin1 = K (top), pin2 = A (bottom)
SYMS["TVS"] = two("hvh:TVS", "TVS", "D")      # pin1 = K
SYMS["FB"] = two("hvh:FB", "FB", "FB")
flag = Sym("hvh:PWR_FLAG", [("1", "pwr", "power_out", "B")], "#FLG", kind="two", power=True)
flag.glyph = "FLAG"; flag.pinpos = {"1": (0, 0, 90)}; flag.h = 2.54
SYMS["PWR_FLAG"] = flag

def write_symlib():
    with open(os.path.join(OUT, "hvh.kicad_sym"), "w") as f:
        f.write('(kicad_symbol_lib (version 20220914) (generator hvh_gen)\n')
        for s in SYMS.values():
            f.write(s.lib().replace("    (symbol \"hvh:", "  (symbol \"", 1))
        f.write(')\n')

# ---------------------------------------------------------------- schematic
PAPERS = [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]
ROOT_UUID = U()
SHEET_UUIDS = {s: U() for s in D.SHEETS}
FILE_UUIDS = {s: U() for s in D.SHEETS}
PWR_FLAG_NETS = ["+5V", "GND", "+3V3", "+5V_AUD", "MIC_VDD_F", "MIC_VDD"]

def title_block(sheet_title, comment=""):
    return (f'  (title_block (title {q(TITLE)}) (date {q(DATE)}) (rev {q(REV)}) (company "Open hardware - generated design")\n'
            f'    (comment 1 {q(sheet_title)}) (comment 2 {q(comment)}))\n')

def label_len(net): return (len(net) + 3) * 1.27 * 0.8

def gen_sheet(sheet):
    comps = [c for c in D.COMPONENTS if c["sheet"] == sheet]
    # order: big ICs first
    comps.sort(key=lambda c: -len(c["pins"]))
    items = []
    used_syms = set()
    # flags for this sheet
    flags = [n for n in PWR_FLAG_NETS if any(n in c["pins"].values() for c in comps)]
    flagref = {"power": 100, "cm5": 200, "usb": 300, "audio": 400, "zigbee": 500, "eth_sd": 600, "ui": 700}[sheet]
    # layout cells
    cells = []
    for c in comps:
        s = SYMS[c["sym"]]
        x0, y0, x1, y1 = s.bbox()
        nets_l = [c["pins"].get(p[0], "NC") for p in s.pins if s.pinpos[p[0]][2] == 0]
        nets_r = [c["pins"].get(p[0], "NC") for p in s.pins if s.pinpos[p[0]][2] == 180]
        ll = max([label_len(n) for n in nets_l] + [0]) + G
        lr = max([label_len(n) for n in nets_r] + [0]) + G
        lb = 12.7 if s.kind == "box" else 0
        extra_tb = 0
        if s.kind == "two":
            nets_t = [c["pins"].get("1")]; ll = lr = max(label_len(n) for n in c["pins"].values()) / 2 + 3
            extra_tb = 6
        w = (x1 - x0) + ll + lr + 2 * G
        h = (y1 - y0) + lb + extra_tb + 4 * G + (2 * extra_tb)
        cells.append((c, s, w, h, ll, x0, y1))
    # shelf packing
    total_area = sum(w * h for _, _, w, h, _, _, _ in cells)
    maxw = max(w for _, _, w, _, _, _, _ in cells)
    target_w = max(maxw, math.sqrt(total_area * 1.6))
    placed = []
    x = y = 0; rowh = 0
    for cell in cells:
        c, s, w, h, ll, bx0, by1 = cell
        if x + w > target_w and x > 0:
            x = 0; y += rowh; rowh = 0
        placed.append((cell, x, y)); x += w; rowh = max(rowh, h)
    used_w = max(px + cell[2] for cell, px, py in placed)
    used_h = y + rowh + 30
    paper = next(p for p in PAPERS if p[1] - 40 >= used_w and p[2] - 50 >= used_h)
    ox, oy = 20, 25
    flag_items = []
    for cell, px, py in placed:
        c, s, w, h, ll, bx0, by1 = cell
        used_syms.add(c["sym"])
        sx = snap(ox + px + ll + G - bx0)
        sy = snap(oy + py + by1 + 2 * G + (6 if s.kind == "two" else 0))
        p = D.P[c["part"]]
        inbom = "yes" if p["bom"] else "no"
        fields = [("Reference", c["ref"]), ("Value", p["value"]), ("Footprint", p["fp"]), ("Datasheet", ""),
                  ("LCSC", p["lcsc"]), ("MPN", p["mpn"]), ("Manufacturer", p["mfr"]), ("Description", p["desc"])]
        if p["dist"]: fields.append(("Distributor", p["dist"]))
        bb = s.bbox()
        props = ""
        for i, (k, v) in enumerate(fields):
            if k == "Reference":
                at = (sx + bb[0] if s.kind == "box" else sx + 2.54, sy - bb[3] - 1.5 if s.kind == "box" else sy - 1.27)
                hide = ""
            elif k == "Value":
                at = (sx + bb[0] + 10.16 if s.kind == "box" else sx + 2.54, sy - bb[3] - 1.5 if s.kind == "box" else sy + 1.27)
                hide = ""
            else:
                at = (sx, sy); hide = " hide"
            props += f'    (property {q(k)} {q(v)} (at {at[0]:.2f} {at[1]:.2f} 0) (effects (font (size 1.27 1.27)) (justify left){hide}))\n'
        pins_txt = "".join(f'    (pin {q(n)} (uuid {U()}))\n' for n, _, _, _ in s.pins)
        items.append(f'  (symbol (lib_id {q(s.name)}) (at {sx} {sy} 0) (unit 1) (in_bom {inbom}) (on_board yes) (dnp no)\n'
                     f'    (uuid {U()})\n{props}{pins_txt}'
                     f'    (instances (project {q(PROJ)} (path {q("/" + ROOT_UUID + "/" + SHEET_UUIDS[sheet])} (reference {q(c["ref"])}) (unit 1)))))\n')
        # wires + labels
        for num, name, typ, side in s.pins:
            net = c["pins"].get(num, "NC")
            lx, ly, a = s.pinpos[num]
            px_, py_ = round(sx + lx, 2), round(sy - ly, 2)
            if net == "NC":
                items.append(f'  (no_connect (at {px_} {py_}) (uuid {U()}))\n')
                continue
            dx, dy, la, just = {0: (-G, 0, 180, "right"), 180: (G, 0, 0, "left"),
                                90: (0, G, 270, "right"), 270: (0, -G, 90, "left")}[a]
            ex, ey = round(px_ + dx, 2), round(py_ + dy, 2)
            items.append(f'  (wire (pts (xy {px_} {py_}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {U()}))\n')
            shape = "passive" if typ in ("passive", "power_in", "power_out", "no_connect") else \
                    {"input": "input", "output": "output", "bidirectional": "bidirectional", "open_collector": "output"}.get(typ, "passive")
            items.append(f'  (global_label {q(net)} (shape {shape}) (at {ex} {ey} {la}) (fields_autoplaced)\n'
                         f'    (effects (font (size 1.27 1.27)) (justify {just})) (uuid {U()})\n'
                         f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {ex} {ey} 0) (effects (font (size 1.27 1.27)) hide)))\n')
    # power flags in a row at the bottom
    fy = snap(oy + used_h - 18)
    for i, n in enumerate(flags):
        fx = snap(ox + 10 + i * 30)
        used_syms.add("PWR_FLAG")
        ref = f"#FLG0{flagref + i}"
        items.append(f'  (symbol (lib_id "hvh:PWR_FLAG") (at {fx} {fy} 0) (unit 1) (in_bom no) (on_board yes) (dnp no)\n'
                     f'    (uuid {U()})\n'
                     f'    (property "Reference" {q(ref)} (at {fx} {fy-4} 0) (effects (font (size 1.27 1.27)) hide))\n'
                     f'    (property "Value" "PWR_FLAG" (at {fx} {fy-4} 0) (effects (font (size 1.27 1.27))))\n'
                     f'    (property "Footprint" "" (at {fx} {fy} 0) (effects (font (size 1.27 1.27)) hide))\n'
                     f'    (property "Datasheet" "" (at {fx} {fy} 0) (effects (font (size 1.27 1.27)) hide))\n'
                     f'    (pin "1" (uuid {U()}))\n'
                     f'    (instances (project {q(PROJ)} (path {q("/" + ROOT_UUID + "/" + SHEET_UUIDS[sheet])} (reference {q(ref)}) (unit 1)))))\n')
        ex, ey = fx, round(fy + G, 2)
        items.append(f'  (wire (pts (xy {fx} {fy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {U()}))\n')
        items.append(f'  (global_label {q(n)} (shape passive) (at {ex} {ey} 270) (fields_autoplaced)\n'
                     f'    (effects (font (size 1.27 1.27)) (justify right)) (uuid {U()})\n'
                     f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {ex} {ey} 0) (effects (font (size 1.27 1.27)) hide)))\n')
    # notes
    notes = SHEET_NOTES.get(sheet, [])
    ny = snap(oy + used_h - 8)
    for i, t in enumerate(notes):
        items.append(f'  (text {q(t)} (at {ox + 150} {snap(ny - 4 * (len(notes) - i))} 0) (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid {U()}))\n')
    lib = "".join(SYMS[k].lib() for k in sorted(used_syms))
    s = (f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {FILE_UUIDS[sheet]})\n  (paper "{paper[0]}")\n'
         + title_block(D.SHEET_TITLES[sheet]) + f'  (lib_symbols\n{lib}  )\n' + "".join(items) + ')\n')
    with open(os.path.join(OUT, f"{sheet}.kicad_sch"), "w") as f:
        f.write(s)
    return paper[0]

SHEET_NAMES = {"power": "Power", "cm5": "CM5", "usb": "USB_Hub", "audio": "Audio", "zigbee": "Zigbee", "eth_sd": "Ethernet_SD", "ui": "UI_Mech"}
SHEET_NOTES = {
    "power": ["USB-C: CC1/CC2 go straight to the CM5 PMIC, which negotiates 5V/5A (Raspberry Pi 27W PSU).",
              "Other USB-C chargers give 5V/3A; set usb_max_current_enable=1 (done by the SD-card installer)."],
    "cm5": ["Use CM5 *Lite* (no eMMC) wireless variant, e.g. CM5104000. Boots from J5 microSD.",
            "DF40 pad geometry = HA Yellow / CM4IO. Antenna end of module must stay at board edge."],
    "usb": ["J3 = USB 3.0 (CM5 USB3-0). J4 = USB 2.0 via hub (port 1). Hub port 2 = audio codec,",
            "port 3 = Zigbee USB-UART, port 4 = test pads. FE1.1s has internal crystal load caps."],
    "audio": ["CM108B appears as a standard USB Audio Class device (snd-usb-audio, in HAOS).",
              "SW4 cuts microphone power (hardware privacy) and lights D5 when muted."],
    "zigbee": ["MGM210P wired exactly like Home Assistant Yellow (PA05 TX, PA06 RX, PD02 CTS, PC01 RTS,",
               "PB00 bootloader, PB01 LED) so official Yellow EmberZNet / OpenThread images apply."],
    "eth_sd": ["HR911130A LED pin polarity (11/14 anode) per LCSC land pattern - verify on first article.",
               "SD card supply switched by CM5 SD_PWR_ON (required for UHS reset)."],
    "ui": ["Fan header pinout matches Raspberry Pi CM5IO (1=5V 2=PWM 3=GND 4=TACH).",
           "TP1/TP2 = CM5 UART0 (GPIO14 TX / GPIO15 RX), 3.3V."],
}

def gen_root(papers):
    sheets = ""
    for i, s in enumerate(D.SHEETS):
        x, y = 25 + (i % 4) * 65, 40 + (i // 4) * 50
        sheets += (f'  (sheet (at {x} {y}) (size 50 25) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))\n'
                   f'    (uuid {SHEET_UUIDS[s]})\n'
                   f'    (property "Sheetname" {q(SHEET_NAMES[s])} (at {x} {y - 0.7} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
                   f'    (property "Sheetfile" {q(s + ".kicad_sch")} (at {x} {y + 25.6} 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
                   f'    (instances (project {q(PROJ)} (path {q("/" + ROOT_UUID)} (page {q(str(i + 2))})))))\n')
    txt = [
        "HVH-1 Home Voice Hub - Raspberry Pi Compute Module 5 carrier for Home Assistant OS + Claude voice assistant.",
        "Interfaces: USB-C power (5V/5A PD via CM5), 1x USB3.0-A, 1x USB2.0-A, Gigabit Ethernet, microSD boot,",
        "Wi-Fi 5 (2.4/5GHz) + BT5 on CM5, Zigbee/Thread MGM210P, USB audio (MEMS mic + 2.5W speaker amp).",
        "All nets are global labels. Generated from gen/design.py - edit there, then re-run gen/build.sh.",
    ]
    t = "".join(f'  (text {q(s)} (at 20 {130 + 6 * i} 0) (effects (font (size 2 2)) (justify left bottom)) (uuid {U()}))\n' for i, s in enumerate(txt))
    s = (f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {ROOT_UUID})\n  (paper "A3")\n'
         + title_block("Top level / sheet index") + '  (lib_symbols)\n' + sheets + t +
         '  (sheet_instances (path "/" (page "1")))\n)\n')
    with open(os.path.join(OUT, f"{PROJ}.kicad_sch"), "w") as f:
        f.write(s)

if __name__ == "__main__":
    write_symlib()
    papers = {s: gen_sheet(s) for s in D.SHEETS}
    gen_root(papers)
    with open(os.path.join(OUT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (lib (name "hvh")(type "KiCad")(uri "${KIPRJMOD}/hvh.kicad_sym")(options "")(descr "HVH-1 generated symbols"))\n)\n')
    with open(os.path.join(OUT, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n  (lib (name "hvh")(type "KiCad")(uri "${KIPRJMOD}/../lib/hvh.pretty")(options "")(descr "HVH-1 footprints"))\n)\n')
    print(papers)
