import os
os.environ.setdefault("KICAD7_FOOTPRINT_DIR","/usr/share/kicad/footprints")
os.environ.setdefault("KICAD7_SYMBOL_DIR","/usr/share/kicad/symbols")
import pcbnew, sys, re, collections
b = pcbnew.LoadBoard(sys.argv[1])
if len(sys.argv) > 3 and sys.argv[3] == 'fill':
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.WriteDRCReport(b, sys.argv[2], pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(sys.argv[2]).read()
kinds = collections.Counter(re.findall(r'^\[(\w+)\]', txt, re.M))
print(kinds)
m = re.search(r'\*\* Found (\d+) DRC violations', txt); print(m.group(0) if m else '')
m = re.search(r'\*\* Found (\d+) unconnected pads', txt); print(m.group(0) if m else '')
