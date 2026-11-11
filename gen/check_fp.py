import sys, pcbnew
sys.path.insert(0, '.')
import design as D
cache = {}
def fp(libname):
    if libname not in cache:
        lib, name = libname.split(':')
        path = '/home/claude/hvh/lib/hvh.pretty' if lib == 'hvh' else f'/usr/share/kicad/footprints/{lib}.pretty'
        cache[libname] = pcbnew.FootprintLoad(path, name)
    return cache[libname]
bad = 0
for c in D.COMPONENTS:
    p = D.P[c['part']]
    f = fp(p['fp'])
    pads = {pd.GetNumber() for pd in f.Pads() if pd.GetNumber()}
    pins = set(c['pins'].keys())
    if c['sym'] in D.SYM:
        sympins = {x[0] for x in D.SYM[c['sym']]['pins']}
    else:
        sympins = pins
    if pads != pins or sympins != pins:
        bad += 1
        print(c['ref'], p['fp'], 'pads-pins', sorted(pads - pins), 'pins-pads', sorted(pins - pads), 'sym-diff', sorted(sympins ^ pins))
print('mismatches', bad)
