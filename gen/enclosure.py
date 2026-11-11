"""HVH-1 enclosure (CadQuery). Two printed parts: base (tray) and lid.

Frame: X = board x, Y = -board y (board y grows towards the front edge), Z up.
Board outline is 100 x 80 mm, rear edge (y = 0) carries USB-C, USB-A x2 and RJ45;
front edge (y = 80) carries microSD, the mute slide, the LEDs, the mic and the power button.
"""
import os, sys
import cadquery as cq

OUT = sys.argv[1] if len(sys.argv) > 1 else "../enclosure"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- key dimensions (mm)
BW, BH, BR = 100.0, 80.0, 3.0           # PCB outline
GAP = 0.5                               # PCB edge to inner wall
WALL = 2.4
FLOOR = 2.0
BOSS_H = 4.5                            # space under the PCB (THT pins, test points)
PCB_T = 1.6
Z_PB = FLOOR + BOSS_H                   # PCB bottom
Z_T = Z_PB + PCB_T                      # PCB top = split plane
INNER_H = 17.0                          # PCB top to lid underside (RJ45 13.3, CM5 + heatsink ~14)
TOP_T = 2.0
Z_LID_IN = Z_T + INNER_H
Z_TOP = Z_LID_IN + TOP_T
SKIRT = 1.5                             # lid skirt overlaps the base wall by this much
FIT = 0.2                               # lid/base clearance

IX0, IY0, IX1, IY1 = -GAP, -GAP, BW + GAP, BH + GAP
OX0, OY0, OX1, OY1 = IX0 - WALL, IY0 - WALL, IX1 + WALL, IY1 + WALL
IR, OR = BR + GAP, BR + GAP + WALL

def P(x, y): return (x, -y)

def rrect(x0, y0, x1, y1, r, z0, z1):
    """rounded rectangle prism, board coords (y down)."""
    w, h = x1 - x0, y1 - y0
    s = (cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, -(y0 + y1) / 2)
         .rect(w, h).extrude(z1 - z0))
    return s.edges("|Z").fillet(r) if r > 0 else s

def box(cx, cy, sx, sy, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(cx, -cy).rect(sx, sy).extrude(z1 - z0)

def cyl(cx, cy, d, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(cx, -cy).circle(d / 2).extrude(z1 - z0)

# ---------------------------------------------------------------- board features (from hvh.kicad_pcb)
PCB_HOLES = [(3.5, 3.5), (96.5, 3.5), (3.5, 76.5), (3.5, 61.0)]          # M3, lid-to-base screws clamp the PCB
CM5_HOLES = [(59.5, 28.5), (92.5, 28.5), (59.5, 76.5), (92.5, 76.5)]     # M2.5, module screws
# rear connectors: (name, x centre, opening width, opening top above PCB, counterbore w, h)
REAR = [("USB-C", 12.5, 9.6, 3.8, 12.8, 6.8),
        ("USB-A (USB2)", 28.0, 14.2, 7.4, 17.0, 9.0),
        ("RJ45", 63.0, 16.6, 14.0, 0, 0),
        ("USB-A (USB3)", 84.0, 14.2, 7.4, 17.0, 9.0)]
SD = (49.0, 13.0, 2.4)            # microSD: x, width, height
SLIDE = (24.2, 7.0, 2.8)          # mute slide switch lever
LEDS = [8.6, 11.7, 14.8, 17.9]    # y = 77.8
LED_Y = 77.8
MIC = (30.6, 75.5)
PWR = (38.2, 75.6)
PINHOLES = [(51.0, 29.6, "rpiboot"), (8.0, 45.5, "Zigbee boot")]
SPK = (29.0, 51.0, 36.0)          # x, y, speaker diameter
SPK_DEPTH = 5.5
CM5_VENT = (60.0, 32.0, 92.0, 72.0)
SMA = (66.0, Z_T + 9.0)           # knock-out on the right wall: board y, z

# ---------------------------------------------------------------- base
def make_base():
    b = rrect(OX0, OY0, OX1, OY1, OR, 0, Z_T - SKIRT)
    ring_o = rrect(OX0 + WALL / 2 + FIT, OY0 + WALL / 2 + FIT, OX1 - WALL / 2 - FIT, OY1 - WALL / 2 - FIT,
                   OR - WALL / 2 - FIT, Z_T - SKIRT, Z_T)
    b = b.union(ring_o)
    b = b.cut(rrect(IX0, IY0, IX1, IY1, IR, FLOOR, Z_T + 1))
    # PCB support bosses
    for x, y in PCB_HOLES:
        b = b.union(cyl(x, y, 7.0, FLOOR - 0.01, Z_PB))
        b = b.cut(cyl(x, y, 3.4, -1, Z_PB + 1))                 # M3 clearance
        b = b.cut(cyl(x, y, 6.2, -1, 3.0))                      # socket-head counterbore from below
    for x, y in CM5_HOLES:
        b = b.union(cyl(x, y, 6.0, FLOOR - 0.01, Z_PB))
        b = b.cut(cyl(x, y, 3.4, Z_PB - 4.5, Z_PB + 1))         # M2.5 heat-set insert (OD 3.5-3.6)
    # extra PCB rests along the rear edge (connector insertion load)
    for x in (45.0, 75.0):
        b = b.union(box(x, 3.0, 4.0, 4.0, FLOOR - 0.01, Z_PB))
    # floor vents under the CM5 (chimney with the lid vents)
    for i in range(9):
        x = 62.0 + i * 3.6
        b = b.cut(box(x, 52.0, 1.8, 34.0, -1, FLOOR + 1))
    # rubber-foot recesses (10 mm bumpers)
    for x, y in ((14, 10), (86, 10), (14, 70), (86, 70)):
        b = b.cut(cyl(x, y, 10.4, -1, 0.8))
    # label
    b = b.cut(cq.Workplane("XY").workplane(offset=-0.01).center(30, -40)
              .text("HVH-1  Home Voice Hub", 5, 0.6, combine=False, halign="center", valign="center")
              .mirror("YZ", (30, 0, 0)))
    return b

# ---------------------------------------------------------------- lid
def make_lid():
    l = rrect(OX0, OY0, OX1, OY1, OR, Z_T, Z_TOP)
    skirt = rrect(OX0, OY0, OX1, OY1, OR, Z_T - SKIRT, Z_T).cut(
        rrect(OX0 + WALL / 2, OY0 + WALL / 2, OX1 - WALL / 2, OY1 - WALL / 2, OR - WALL / 2, Z_T - SKIRT - 1, Z_T + 1))
    l = l.union(skirt)
    l = l.cut(rrect(IX0, IY0, IX1, IY1, IR, Z_T - SKIRT - 1, Z_LID_IN))
    # pillars clamping the PCB, M3 heat-set inserts at the bottom
    for x, y in PCB_HOLES:
        l = l.union(cyl(x, y, 6.5, Z_T + 0.05, Z_LID_IN + 0.01))
        l = l.cut(cyl(x, y, 4.0, Z_T - 1, Z_T + 6.0))
    # rear openings (open towards the bottom so the lid drops over the connectors)
    yin, yout = IY0, OY0
    for name, x, w, h, cw, ch in REAR:
        l = l.cut(box(x, (yin + yout) / 2, w, WALL + 2, Z_T - SKIRT - 1, Z_T + h))
        if cw:
            zc = Z_T + h / 2
            l = l.cut(box(x, yout + 0.7, cw, 1.4 + 0.02, Z_T - SKIRT - 1, zc + ch / 2))
    # front openings
    fin, fout = IY1, OY1
    x, w, h = SD
    l = l.cut(box(x, (fin + fout) / 2, w, WALL + 2, Z_T - SKIRT - 1, Z_T + h))
    l = l.cut(cq.Workplane("XZ").workplane(offset=fout - 1.3).center(x, Z_T + 0.8).circle(6.0).extrude(-3))  # finger scallop
    x, w, h = SLIDE
    l = l.cut(box(x, (fin + fout) / 2, w, WALL + 2, Z_T - SKIRT - 1, Z_T + h))
    l = l.cut(box(x, fout - 0.95, 13.0, 1.9 + 0.02, Z_T - SKIRT - 1, Z_T + 5.0))       # thin the wall around the lever
    # LED light pipes: 2 mm acrylic rod in sleeves down to 1 mm above the LEDs
    for x in LEDS:
        l = l.union(cyl(x, LED_Y, 3.0, Z_T + 1.0, Z_LID_IN + 0.01))
    for x in LEDS:
        l = l.cut(cyl(x, LED_Y, 2.1, Z_T, Z_TOP + 1))
    # microphone: acoustic port + sealed tube to the top-port MEMS mic (0.8 mm foam gasket)
    mx, my = MIC
    l = l.union(cyl(mx, my, 4.4, Z_T + 1.0 + 0.8, Z_LID_IN + 0.01))
    l = l.cut(cyl(mx, my, 2.4, Z_T, Z_LID_IN - 0.4))
    l = l.cut(cyl(mx, my, 1.0, Z_LID_IN - 0.5, Z_TOP + 1))
    l = l.cut(cyl(mx, my, 2.2, Z_TOP - 0.6, Z_TOP + 1))      # shallow outer counterbore (mesh sticker)
    # power button: cantilever key cut from the lid top with a plunger to the tact switch
    px, py = PWR
    kw, kl, slot = 7.0, 9.0, 0.8
    u = (box(px, py - kl / 2 - slot / 2 + 1.0, kw + 2 * slot, slot, Z_LID_IN - 1, Z_TOP + 1)
         .union(box(px - kw / 2 - slot / 2, py + 1.0 - slot / 2, slot, kl, Z_LID_IN - 1, Z_TOP + 1))
         .union(box(px + kw / 2 + slot / 2, py + 1.0 - slot / 2, slot, kl, Z_LID_IN - 1, Z_TOP + 1)))
    l = l.cut(u)                                              # hinge on the front side
    l = l.union(cyl(px, py, 3.0, Z_T + 1.5 + 0.3, Z_LID_IN + 0.01))   # TS-1187A is 1.5 mm tall
    l = l.cut(cyl(px, py, 5.0, Z_TOP - 0.4, Z_TOP + 1))      # finger dimple
    # pinholes for the rpiboot / Zigbee bootloader buttons (paper clip)
    for x, y, _ in PINHOLES:
        l = l.union(cyl(x, y, 3.6, Z_T + 3.0, Z_LID_IN + 0.01))
        l = l.cut(cyl(x, y, 1.6, Z_T, Z_TOP + 1))
    # speaker: 36 mm round driver pressed into a ring under a hex grille
    sx, sy, sd = SPK
    ring = cyl(sx, sy, sd + 3.2, Z_LID_IN - SPK_DEPTH, Z_LID_IN + 0.01).cut(cyl(sx, sy, sd + 0.4, Z_LID_IN - SPK_DEPTH - 1, Z_LID_IN + 1))
    for k in range(3):     # snap tabs
        import math
        a = math.radians(90 + 120 * k)
        tx, ty = sx + (sd / 2 + 0.2) * math.cos(a), sy + (sd / 2 + 0.2) * math.sin(a)
        ring = ring.union(cyl(tx, ty, 2.0, Z_LID_IN - SPK_DEPTH, Z_LID_IN - SPK_DEPTH + 0.8))
    l = l.union(ring)
    pts = []
    pitch = 2.6
    import math
    r_max = sd / 2 - 3.0
    j = 0
    yv = -r_max
    while yv <= r_max + 1e-6:
        off = (pitch / 2) if j % 2 else 0
        xv = -r_max + off
        while xv <= r_max + 1e-6:
            if xv * xv + yv * yv <= r_max * r_max:
                pts.append((sx + xv, -(sy + yv)))
            xv += pitch
        yv += pitch * math.sqrt(3) / 2; j += 1
    l = l.cut(cq.Workplane("XY").workplane(offset=Z_LID_IN - 1).pushPoints(pts).circle(0.75).extrude(TOP_T + 2))
    # CM5 vents
    x0, y0, x1, y1 = CM5_VENT
    for i in range(10):
        x = x0 + 1.5 + i * (x1 - x0 - 3) / 9
        l = l.cut(box(x, (y0 + y1) / 2, 1.6, y1 - y0, Z_LID_IN - 1, Z_TOP + 1))
    # side vents (both short walls, upper half)
    for i in range(8):
        y = 20 + i * 5.0
        for xw in (OX0 + WALL / 2, OX1 - WALL / 2):
            if xw < 0 and 24 < y < 42: continue    # keep the Zigbee antenna wall solid (no slots near the antenna)
            l = l.cut(box(xw, y, WALL + 2, 1.8, Z_T + 7, Z_T + 14))
    # SMA knock-out on the right wall: 6.6 mm disc, 0.5 mm membrane left on the inside
    yk, zk = SMA
    l = l.cut(cq.Workplane("YZ").workplane(offset=OX1 + 0.5).center(-yk, zk).circle(3.3).extrude(-(WALL - 0.5 + 0.5)))
    # top label
    l = l.cut(cq.Workplane("XY").workplane(offset=Z_TOP - 0.5).center(76, -14)
              .text("HVH-1", 6, 1.0, combine=False, halign="center", valign="center"))
    return l

if __name__ == "__main__":
    base = make_base()
    lid = make_lid()
    for name, part, flip in (("hvh1_base", base, False), ("hvh1_lid", lid, True)):
        cq.exporters.export(part, f"{OUT}/{name}.step")
        pp = part.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_TOP)) if flip else part   # print orientation
        cq.exporters.export(pp, f"{OUT}/{name}.stl", tolerance=0.02, angularTolerance=0.15)
        cq.exporters.export(pp, f"{OUT}/{name}.3mf", tolerance=0.02, angularTolerance=0.15)
        bb = part.val().BoundingBox()
        print(name, "valid", part.val().isValid(), f"{bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm", f"vol {part.val().Volume() / 1000:.1f} cm3")
    asm = cq.Assembly()
    asm.add(base, name="base", color=cq.Color(0.2, 0.2, 0.22))
    asm.add(lid, name="lid", color=cq.Color(0.92, 0.92, 0.9, 0.6))
    asm.save(f"{OUT}/hvh1_enclosure_assembly.step")
    print("Z_T", Z_T, "Z_TOP", Z_TOP)
