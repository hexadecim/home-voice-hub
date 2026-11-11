"""Finish the routed board: zones, stitching, silkscreen, fab notes, fill, save.

/usr/bin/python3 pcb_finish.py routed.kicad_pcb out.kicad_pcb
"""
import os, sys, math
os.environ.setdefault("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
import pcbnew
sys.path.insert(0, os.path.dirname(__file__))
from pcb_place import add_zone, P, OX, OY, W, H, mm
import router as RT

def text(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, angle=0, bold=False, justify=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    t.SetTextAngleDegrees(angle)
    if justify == "left": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Fab): t.SetMirrored(True)
    board.Add(t)
    return t

def finish(inp, outp):
    b = pcbnew.LoadBoard(inp)
    # remove old zones (keep rule areas inside footprints), then recreate
    _oldz = list(b.Zones())
    for z in _oldz:
        b.Remove(z)
    full = [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]
    add_zone(b, "GND", pcbnew.In1_Cu, full, 0, "GND_L2", thermal=False)
    add_zone(b, "+5V", pcbnew.In3_Cu, full, 0, "P5V_L4", thermal=False)
    add_zone(b, "GND", pcbnew.In4_Cu, full, 0, "GND_L5", thermal=False)
    add_zone(b, "GND", pcbnew.In2_Cu, full, 0, "GND_L3", thermal=False)
    add_zone(b, "GND", pcbnew.F_Cu, full, 0, "GND_TOP", thermal=False)
    add_zone(b, "GND", pcbnew.B_Cu, full, 0, "GND_BOT", thermal=False)
    for i, zp in enumerate(RT.P5V_ZONES + RT.P5V_EXTRA):
        add_zone(b, "+5V", pcbnew.F_Cu, zp, 2, f"P5V_TOP_{i}", clearance=0.2, thermal=False)
    # ---- silkscreen: references small, auto-placed away from pads; product markings
    place_refs(b)
    S = 1.0
    text(b, "HVH-1  Home Voice Hub", 30.0, 66.0, 1.4, bold=True, justify="left")
    text(b, "rev 1.0  CM5 carrier for Home Assistant", 30.0, 68.2, 0.9, justify="left")
    labels = [("5V USB-C", 12.5, 9.0 - 0.2), ("USB 2.0", 28.0, 17.0), ("ETHERNET", 63.0, 20.0 - 0.6),
              ("USB 3.0", 84.0, 16.7), ("PWR", 8.6, 79.2 - 0.2), ("ACT", 11.7, 79.2 - 0.2), ("ZB", 14.8, 79.2 - 0.2),
              ("MUTE", 17.9, 79.2 - 0.2), ("MIC", 30.6, 73.8 - 0.1), ("microSD", 49.0, 66.4)]
    for s, x, y in labels:
        text(b, s, x, y, 0.8)
    text(b, "CM5 Lite + Wi-Fi (e.g. CM5104000)", 76.0, 30.0 - 2.5, 1.0)
    text(b, "Zigbee/Thread", 7.6, 41.2, 0.8)
    # fab layer notes
    text(b, "Fab: 6L 1.6mm JLC06161H-3313, impedance control, ENIG, epoxy-filled capped vias (via-in-pad), green mask, white silk", 2.0, -6.0, 1.0, layer=pcbnew.Dwgs_User, justify="left")
    text(b, "Impedance: USB 90R diff 0.16/0.24 (L1 ref L2, L6 ref L5, L3 stripline), Ethernet 100R diff 0.14/0.26. L2/L5 GND, L4 +5V", 2.0, -4.0, 1.0, layer=pcbnew.Dwgs_User, justify="left")
    # bottom side test point legend
    for ref in [f"TP{i}" for i in range(1, 14)]:
        fp = b.FindFootprintByReference(ref)
        pos = fp.GetPosition()
        net = fp.Pads()[0].GetNetname()
        text(b, net.replace("_", ""), pcbnew.ToMM(pos.x) - OX, pcbnew.ToMM(pos.y) - OY + 1.5, 0.8, layer=pcbnew.B_SilkS)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(outp, b)
    print("saved", outp)

def bbox_mm(bb):
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))

def overlap(a, b, m=0.1):
    return not (a[2] + m <= b[0] or b[2] + m <= a[0] or a[3] + m <= b[1] or b[3] + m <= a[1])

def place_refs(b):
    """Put each reference designator next to its footprint where it doesn't collide with
    pads, footprint silk or other references; hide it (keep on F.Fab) if no room."""
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads.append(bbox_mm(p.GetBoundingBox()))
    edge = (OX + 0.4, OY + 0.4, OX + W - 0.4, OY + H - 0.4)
    taken = []
    for fp in b.GetFootprints():
        for item in fp.GraphicalItems():
            if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and item.GetClass() != "PCB_TEXT":
                taken.append(bbox_mm(item.GetBoundingBox()))
    hidden = 0
    fps = sorted(b.GetFootprints(), key=lambda f: -len(list(f.Pads())))
    for fp in fps:
        ref = fp.Reference()
        ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); ref.SetTextThickness(mm(0.13))
        ref.SetKeepUpright(True)
        fv = fp.Value(); fv.SetVisible(False)
        if fp.GetReference().startswith(("H", "FID", "M")):
            ref.SetVisible(False); continue
        cy = fp.GetCourtyard(fp.GetLayer() == pcbnew.F_Cu and pcbnew.F_CrtYd or pcbnew.B_CrtYd).BBox()
        c = bbox_mm(cy) if cy.GetWidth() > 0 else bbox_mm(fp.GetBoundingBox(False, False))
        cx, cyy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        n = len(fp.GetReference())
        tw, th = 0.7 * 0.75 * n + 0.2, 0.9
        cands = [(cx, c[1] - th / 2 - 0.1), (cx, c[3] + th / 2 + 0.1), (c[0] - tw / 2 - 0.15, cyy), (c[2] + tw / 2 + 0.15, cyy)]
        for dx in (0, -1.0, 1.0, -2.0, 2.0):
            for dy in (0, -0.8, 0.8):
                cands.append((cx + dx, c[1] - th / 2 - 0.1 + dy - 0.8)); cands.append((cx + dx, c[3] + th / 2 + 0.1 + dy + 0.8))
        ok = False
        for x, y in cands:
            box = (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)
            if not overlap(box, edge, -0.0) or box[0] < edge[0] or box[2] > edge[2] or box[1] < edge[1] or box[3] > edge[3]:
                continue
            if any(overlap(box, p, 0.15) for p in pads): continue
            if any(overlap(box, t, 0.05) for t in taken): continue
            ref.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            ref.SetTextAngleDegrees(0)
            taken.append(box); ok = True
            break
        if not ok:
            ref.SetVisible(False); hidden += 1
    print("references hidden (no room):", hidden)

if __name__ == "__main__":
    finish(sys.argv[1], sys.argv[2])
