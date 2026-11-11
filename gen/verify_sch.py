"""Cross-check the KiCad-exported netlist against design.py + simplified ERC."""
import sys, os, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__))
import design as D
xmlp = sys.argv[1]
t = ET.parse(xmlp).getroot()
kn = {}
types = {}
for n in t.find('nets'):
    name = n.get('name').lstrip('/')
    nodes = sorted((x.get('ref'), x.get('pin')) for x in n)
    for x in n: types[(x.get('ref'), x.get('pin'))] = x.get('pintype')
    kn[name] = nodes
dn = {k: sorted(v) for k, v in D.nets().items()}
errs = 0
for k, v in dn.items():
    if kn.get(k) != v:
        errs += 1; print('NET MISMATCH', k, 'design', v, 'kicad', kn.get(k))
for k, v in kn.items():
    if k.startswith('unconnected-'):
        r, p = v[0]
        c = next(c for c in D.COMPONENTS if c['ref'] == r)
        if c['pins'].get(p) != 'NC': errs += 1; print('UNEXPECTED UNCONNECTED', k)
    elif k not in dn and not k.startswith('Net-('):
        errs += 1; print('EXTRA NET', k, v)
# simplified ERC
FLAGGED = {'+5V','GND','+3V3','+5V_AUD','MIC_VDD_F','MIC_VDD'}  # PWR_FLAG symbols in schematic (not exported to netlist)
for k, v in kn.items():
    if k.startswith('unconnected-'): continue
    ts = [types[x] for x in v]
    if ts.count('power_out') > 1: errs += 1; print('ERC power_out conflict', k)
    if ts.count('output') > 1: errs += 1; print('ERC output conflict', k, v)
    if 'output' in ts and 'power_out' in ts: errs += 1; print('ERC output/power conflict', k)
    if 'power_in' in ts and 'power_out' not in ts and k not in FLAGGED: errs += 1; print('ERC power_in not driven', k)
    if all(x in ('input',) for x in ts): errs += 1; print('ERC only inputs', k)
comps = {c.get('ref') for c in t.find('components')}
missing = {c['ref'] for c in D.COMPONENTS} - comps
if missing: errs += 1; print('missing comps', missing)
print('components', len(comps), 'nets', len([k for k in kn if not k.startswith('unconnected')]), 'errors', errs)
sys.exit(1 if errs else 0)
