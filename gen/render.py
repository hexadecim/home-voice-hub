import sys, subprocess, os, cairosvg
from PIL import Image
pcb, out = sys.argv[1], sys.argv[2]
layers = sys.argv[3] if len(sys.argv) > 3 else "F.Cu,B.Cu,Edge.Cuts,F.Fab"
crop = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else None   # board-local x0,y0,x1,y1
env = dict(os.environ, KICAD7_FOOTPRINT_DIR="/usr/share/kicad/footprints")
subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "0", "--exclude-drawing-sheet",
                "-o", "/tmp/_r.svg", pcb], check=True, env=env, capture_output=True)
# page mode 0 => full A4 sheet, 1 svg unit = 1 mm? use cairosvg at known dpi
scale = 20  # px per mm
cairosvg.svg2png(url="/tmp/_r.svg", write_to="/tmp/_r.png", dpi=25.4 * scale, background_color="white")
im = Image.open("/tmp/_r.png")
if crop:
    x0, y0, x1, y1 = crop
    im = im.crop((int((100 + x0) * scale), int((100 + y0) * scale), int((100 + x1) * scale), int((100 + y1) * scale)))
im.save(out); print(im.size)
