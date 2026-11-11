"""Hide reference designators / drop helper labels that the DRC reports as overlapping
(the assembly drawings on F.Fab/B.Fab keep every reference). usage: silkfix.py board drc_report"""
import sys, re, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); rep = open(sys.argv[2]).read()
refs, texts = set(), set()
for blk in re.split(r"\n(?=\[)", rep):
    if not blk.startswith("[silk"): continue
    refs |= set(re.findall(r"Reference '([^']+)'", blk))
    texts |= set(re.findall(r"PCB Text '([^']+)'", blk))
keep_titles = {"HVH-1  Home Voice Hub"}
n = 0
for fp in b.GetFootprints():
    if fp.GetReference() in refs: fp.Reference().SetVisible(False); n += 1
_rm = []
for d in list(b.GetDrawings()):
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText().startswith(tuple(t[:30].rstrip(".") for t in texts)) and d.GetText() not in keep_titles:
        _rm.append(d)
for d in _rm: b.Remove(d)
# title: move to a free area if it collides
for d in b.GetDrawings():
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() in keep_titles and d.GetText() in texts:
        d.SetLayer(pcbnew.F_Fab)
pcbnew.SaveBoard(sys.argv[1], b)
print("hidden refs", n, "removed labels", len(_rm))
# optional (--edge): footprint silk lines of edge-mounted parts that reach the board edge
if '--edge' not in sys.argv: sys.exit(0)
b = pcbnew.LoadBoard(sys.argv[1]); _rm2 = []
for fp in b.GetFootprints():
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS) or isinstance(g, pcbnew.PCB_TEXT): continue
        bb = g.GetBoundingBox()
        y0, y1 = pcbnew.ToMM(bb.GetY()) - 100, pcbnew.ToMM(bb.GetBottom()) - 100
        x0, x1 = pcbnew.ToMM(bb.GetX()) - 100, pcbnew.ToMM(bb.GetRight()) - 100
        if y0 < 0.9 or y1 > 79.1 or x0 < 0.9 or x1 > 99.1: _rm2.append((fp, g))
for fp, g in _rm2: fp.Remove(g)
pcbnew.SaveBoard(sys.argv[1], b); print("edge silk removed", len(_rm2))
