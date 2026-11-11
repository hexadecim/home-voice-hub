"""Final copper fixes on a routed board (before zone fill):
  * U14 channel swap (ETH2 on pads 10/9, matching design.py) with short F.Cu stubs
  * remove the via-in-pad on U5.8 (too close to the NC pads) and give U5's GND a stub + via
  * GND stub + via for pads whose plane fan-out failed
  * +5V stitching vias inside the CM5 +5V copper area (J10 pins 77-87) to the In3 plane
  * drop vias / track stubs that connect to nothing (leftovers from re-routing)

usage: python3 postfix.py in.kicad_pcb out.kicad_pcb
"""
import sys, math
import pcbnew, shapely
from shapely.geometry import Point, LineString, box
import router as RT

inp, outp = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(inp)
_REMOVED = []
OX, OY = RT.OX, RT.OY
mm = lambda v: pcbnew.ToMM(v)
P = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x + OX), pcbnew.FromMM(y + OY))
nets = b.GetNetsByName()
CLR = 0.16
COPPER = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

def copper_geoms(exclude_net, layer=None):
    """shapely geometry of all copper of other nets (layer=None: any signal layer)."""
    gs = []
    for t in b.GetTracks():
        if t.GetNetname() == exclude_net: continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); gs.append(Point(mm(p.x) - OX, mm(p.y) - OY).buffer(mm(t.GetWidth()) / 2, 16))
        elif layer is None or t.GetLayer() == layer:
            s, e = t.GetStart(), t.GetEnd()
            a, c = (mm(s.x) - OX, mm(s.y) - OY), (mm(e.x) - OX, mm(e.y) - OY)
            gs.append((LineString([a, c]) if a != c else Point(a)).buffer(mm(t.GetWidth()) / 2, 8))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == exclude_net and pad.GetNetname(): continue
            if layer is not None and not pad.IsOnLayer(layer): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                c = pad.GetPosition(); gs.append(Point(mm(c.x) - OX, mm(c.y) - OY).buffer(mm(pad.GetDrillSize().x) / 2 + 0.1, 16)); continue
            poly = pad.GetEffectivePolygon()
            o = poly.Outline(0)
            pts = [(mm(o.CPoint(i).x) - OX, mm(o.CPoint(i).y) - OY) for i in range(o.PointCount())]
            if len(pts) >= 3: gs.append(shapely.Polygon(pts))
    return shapely.unary_union(gs)

def add_track(net, layer, a, c, w):
    t = pcbnew.PCB_TRACK(b); t.SetStart(P(*a)); t.SetEnd(P(*c)); t.SetWidth(pcbnew.FromMM(w))
    t.SetLayer(layer); t.SetNet(nets[net]); b.Add(t)

def add_via(net, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(pcbnew.FromMM(d)); v.SetDrill(pcbnew.FromMM(drill))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNet(nets[net]); b.Add(v)

def pad_xy(ref, num):
    p = b.FindFootprintByReference(ref).FindPadByNumber(num).GetPosition()
    return mm(p.x) - OX, mm(p.y) - OY

def stub_via(net, ref, num, w=0.25, rmax=2.2):
    """short straight F.Cu stub from a pad to a new through via, clear of other copper."""
    x0, y0 = pad_xy(ref, num)
    allc = copper_geoms(net); fcu = copper_geoms(net, pcbnew.F_Cu)
    best = None
    for r10 in range(6, int(rmax * 10) + 1):
        r = r10 / 10
        for k in range(24):
            a = 2 * math.pi * k / 24
            x, y = round(x0 + r * math.cos(a), 2), round(y0 + r * math.sin(a), 2)
            if allc.distance(Point(x, y)) < 0.3 + CLR: continue
            if fcu.distance(LineString([(x0, y0), (x, y)])) < w / 2 + CLR: continue
            best = (x, y); break
        if best: break
    if not best: print("  no stub/via spot for", ref, num); return False
    add_track(net, pcbnew.F_Cu, (x0, y0), best, w); add_via(net, *best)
    print(f"  {net} {ref}.{num}: stub + via at {best}"); return True

MODE = sys.argv[3] if len(sys.argv) > 3 else "fix"
if MODE == "swap":
    # ---- U14 channel swap (ETH2 on pads 10/9, matching design.py); the router re-routes ETH2 afterwards
    u14 = b.FindFootprintByReference("U14")
    for num, net in (("1", ""), ("2", ""), ("10", "ETH2_P"), ("9", "ETH2_N")):
        pad = u14.FindPadByNumber(num)
        if net: pad.SetNet(nets[net])
        else: pad.SetNetCode(0)
    pcbnew.SaveBoard(outp, b); print("saved", outp); sys.exit(0)
# ---- U5: NC pads 7/9 tied to GND (not connected inside the TPD4EUSB30) so the GND via-in-pad on pin 8 is legal
u5 = b.FindFootprintByReference("U5")
for num in ("7", "9"): u5.FindPadByNumber(num).SetNet(nets["GND"])
print("  U5 pads 7/9 -> GND")
def via_in_pad(net, ref, num, d, drill):
    fp = b.FindFootprintByReference(ref); pad = fp.FindPadByNumber(num)
    px, py = pad_xy(ref, num); c = fp.GetPosition(); cx, cy = mm(c.x) - OX, mm(c.y) - OY
    bb = pad.GetBoundingBox(); w, h = mm(bb.GetWidth()), mm(bb.GetHeight())
    if w >= h: x, y = px + math.copysign(w / 2 - d / 2, px - cx), py
    else: x, y = px, py + math.copysign(h / 2 - d / 2, py - cy)
    add_via(net, round(x, 3), round(y, 3), d, drill); print(f"  {net} {ref}.{num}: via-in-pad {d}/{drill} at ({x:.2f},{y:.2f})")
def resize_via(x, y, d, drill):
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            if math.hypot(mm(p.x) - OX - x, mm(p.y) - OY - y) < 0.02:
                t.SetWidth(pcbnew.FromMM(d)); t.SetDrill(pcbnew.FromMM(drill)); print(f"  via at ({x},{y}) -> {d}/{drill}")
u5x, u5y = pad_xy("U5", "8")
resize_via(u5x, u5y, 0.45, 0.2)
resize_via(12.9, 36.0, 0.55, 0.3)
# ---- 3. failed fan-outs
if not stub_via("GND", "U8", "28", w=0.25): via_in_pad("GND", "U8", "28", 0.35, 0.15)
# ---- 4. +5V stitching in the J10 +5V area
zone = box(55.0, 60.4, 57.75, 62.4)
allc = copper_geoms("+5V")
placed = []
for xi in range(551, 577, 1):
    for yi in range(605, 624, 1):
        x, y = xi / 10, yi / 10
        if not zone.buffer(-0.3).contains(Point(x, y)): continue
        if allc.distance(Point(x, y)) < 0.3 + CLR: continue
        if any(math.dist((x, y), q) < 1.0 for q in placed): continue
        placed.append((x, y))
for x, y in placed[:4]: add_via("+5V", x, y)
print(f"  +5V stitching vias in the J10 +5V area: {min(len(placed), 4)}")
# ---- 5. dangling leftovers: vias given as x,y list in argv[4] (board coordinates, from the DRC report)
if len(sys.argv) > 4 and sys.argv[4]:
    for xy in sys.argv[4].split(";"):
        x, y = (float(v) - 100.0 for v in xy.split(","))
        for t in list(b.GetTracks()):
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                if math.hypot(mm(p.x) - OX - x, mm(p.y) - OY - y) < 0.01:
                    r_ = mm(t.GetWidth()) / 2; net_ = t.GetNetname()
                    for o in list(b.GetTracks()):
                        if o.GetClass() == "PCB_VIA" or o.GetNetname() != net_: continue
                        for e in (o.GetStart(), o.GetEnd()):
                            ex, ey = mm(e.x) - OX, mm(e.y) - OY
                            dd = math.hypot(ex - x, ey - y)
                            if 0.005 < dd < r_: add_track(net_, o.GetLayer(), (ex, ey), (x, y), mm(o.GetWidth()))
                    _REMOVED.append(t); b.Remove(t); print("  removed dangling via", xy)

def prune(netnames):
    """remove track pieces with a free end (not on a pad, via or another track of the net)."""
    changed = True
    while changed:
        changed = False
        trs = [t for t in b.GetTracks() if t.GetNetname() in netnames]
        for t in trs:
            if t.GetClass() == "PCB_VIA": continue
            for e in (t.GetStart(), t.GetEnd()):
                ex, ey = mm(e.x), mm(e.y)
                hit = False
                for o in trs:
                    if o is t or o.GetNetname() != t.GetNetname(): continue
                    if o.GetClass() == "PCB_VIA":
                        p = o.GetPosition()
                        if math.hypot(mm(p.x) - ex, mm(p.y) - ey) < mm(o.GetWidth()) / 2: hit = True; break
                    elif o.GetLayer() == t.GetLayer():
                        q1, q2 = o.GetStart(), o.GetEnd()
                        seg = LineString([(mm(q1.x), mm(q1.y)), (mm(q2.x), mm(q2.y))]) if (q1.x, q1.y) != (q2.x, q2.y) else Point(mm(q1.x), mm(q1.y))
                        if seg.distance(Point(ex, ey)) < mm(o.GetWidth()) / 2: hit = True; break
                if not hit:
                    for fp in b.GetFootprints():
                        for pad in fp.Pads():
                            if pad.GetNetname() == t.GetNetname() and pad.IsOnLayer(t.GetLayer()) and pad.HitTest(e): hit = True; break
                        if hit: break
                if not hit:
                    _REMOVED.append(t); b.Remove(t); changed = True; print("  pruned", t.GetNetname(), round(ex - 100, 2), round(ey - 100, 2)); break
            if changed: break
if len(sys.argv) > 5: prune(set(sys.argv[5].split(",")))
pcbnew.SaveBoard(outp, b)
print("saved", outp)
