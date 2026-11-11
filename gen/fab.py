"""HVH-1 fabrication outputs: Gerbers + drill (zip), JLCPCB BOM + CPL, full BOM with sourcing,
STEP, schematic PDF, assembly drawings, netlist.

usage: python3 fab.py <board.kicad_pcb> <schematic root .kicad_sch> <outdir>
"""
import csv, os, re, subprocess, sys, zipfile, collections
import pcbnew
import design as D

PCB, SCH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
GER = os.path.join(OUT, "gerbers"); os.makedirs(GER, exist_ok=True)
STOCK_DB = "/home/claude/tools/parts2.tsv"

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode != 0: print(" ".join(a)); print(r.stdout[-800:], r.stderr[-800:]); sys.exit(1)
    return r.stdout

LAYERS = "F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
run("kicad-cli", "pcb", "export", "gerbers", "--output", GER + "/", "--layers", LAYERS,
    "--subtract-soldermask", "--use-drill-file-origin", PCB)
run("kicad-cli", "pcb", "export", "drill", "--output", GER + "/", "--format", "excellon", "--drill-origin", "plot",
    "--excellon-units", "mm", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", PCB)
zp = os.path.join(OUT, "HVH-1_gerbers_drill.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(GER)): z.write(os.path.join(GER, f), f)
run("kicad-cli", "pcb", "export", "step", "--output", os.path.join(OUT, "HVH-1_pcb.step"), "--subst-models", "--force", PCB)
run("kicad-cli", "sch", "export", "pdf", "--output", os.path.join(OUT, "HVH-1_schematic.pdf"), SCH)
run("kicad-cli", "sch", "export", "netlist", "--output", os.path.join(OUT, "HVH-1.net"), SCH)
run("kicad-cli", "pcb", "export", "pdf", "--output", os.path.join(OUT, "HVH-1_assembly_top.pdf"),
    "--layers", "F.Fab,F.SilkS,Edge.Cuts", "--include-border-title", PCB)
run("kicad-cli", "pcb", "export", "pdf", "--output", os.path.join(OUT, "HVH-1_assembly_bottom.pdf"),
    "--layers", "B.Fab,B.SilkS,Edge.Cuts", "--mirror", "--include-border-title", PCB)

# ---------------- BOM
stock = {}
if os.path.exists(STOCK_DB):
    for ln in open(STOCK_DB, encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) >= 5: stock[f[0]] = (f[2], f[3], f[4])
groups = collections.OrderedDict()
for c in D.COMPONENTS:
    p = D.P[c["part"]]
    groups.setdefault(c["part"], []).append(c["ref"])
def natkey(r): m = re.match(r"([A-Z]+)(\d+)", r); return (m.group(1), int(m.group(2))) if m else (r, 0)
with open(os.path.join(OUT, "HVH-1_BOM_JLCPCB.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for k, refs in groups.items():
        p = D.P[k]
        if not p["bom"]: continue
        w.writerow([p["value"], ",".join(sorted(refs, key=natkey)), p["fp"].split(":")[-1], p["lcsc"]])
rows = []
with open(os.path.join(OUT, "HVH-1_BOM_full.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Qty", "Designators", "Value", "Description", "Manufacturer", "MPN", "LCSC", "JLC type", "LCSC stock (snapshot)",
                "Unit price USD (LCSC, qty 1 tier)", "Alternate source", "Assembly", "Note"])
    for k, refs in groups.items():
        p = D.P[k]
        st = stock.get(p["lcsc"], ("", "", ""))
        asm = "JLC SMT/THT" if p["bom"] else "not assembled"
        if k == "CM5MECH": asm = "customer fits CM5 module"
        w.writerow([len(refs), " ".join(sorted(refs, key=natkey)), p["value"], p["desc"], p["mfr"], p["mpn"], p["lcsc"],
                    st[2], st[0], st[1], p["dist"], asm, p["note"]])
        rows.append((k, len(refs), p, st))

# ---------------- CPL (JLC rotation conventions differ from KiCad for some packages)
ROT_FIX = [(r"^SOT-23", 180), (r"^SOT-223", 180), (r"^SOT-353", 180), (r"^SOT-363", 180), (r"^QFN-", 270),
           (r"^LQFP-", 270), (r"^TQFP-", 270), (r"^TSSOP-", 270), (r"^SOIC-", 270), (r"^SOP-", 270), (r"^MSOP-", 270),
           (r"^USON-10", 270)]
b = pcbnew.LoadBoard(PCB)
bomrefs = {c["ref"] for c in D.COMPONENTS if D.P[c["part"]]["bom"]}
ox = oy = 100.0
with open(os.path.join(OUT, "HVH-1_CPL_JLCPCB.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for fp in sorted(b.GetFootprints(), key=lambda x: natkey(x.GetReference())):
        ref = fp.GetReference()
        if ref not in bomrefs: continue
        pos = fp.GetPosition()
        x = pcbnew.ToMM(pos.x) - ox; y = -(pcbnew.ToMM(pos.y) - oy)
        rot = fp.GetOrientationDegrees(); name = str(fp.GetFPID().GetLibItemName())
        for pat, add in ROT_FIX:
            if re.search(pat, name): rot += add; break
        bottom = fp.GetLayer() == pcbnew.B_Cu
        w.writerow([ref, f"{x:.3f}mm", f"{y:.3f}mm", "Bottom" if bottom else "Top", f"{rot % 360:.1f}"])
print("outputs in", OUT)
low = [(k, n, p["lcsc"], st[0]) for k, n, p, st in rows if p["bom"] and p["lcsc"] and st[0] and int(st[0]) < 50 * n]
print("parts with LCSC stock < 50 boards:", low)
