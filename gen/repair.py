"""Continue from a routed board: import its copper, then hill-climb on the remaining failures.
Each attempt rips up the failed net plus the nets in its way, re-routes them, and is kept only
if the total number of failed nets goes down (otherwise the previous state is restored).

usage: python3 repair.py <routed.kicad_pcb> <out.kicad_pcb> [max_attempts]
"""
import sys, json, random, time, re
import numpy as np, pcbnew, shapely
from shapely.geometry import LineString, Point
import router as RT
import design as D

inp, outp = sys.argv[1], sys.argv[2]
MAXA = int(sys.argv[3]) if len(sys.argv) > 3 else 60
random.seed(7)
txt = open(inp).read()
netnames = {int(m.group(1)): m.group(2) for m in re.finditer(r'^  \(net (\d+) "([^"]*)"\)', txt, re.M)}
LNAME = {"F.Cu": 0, "B.Cu": 1, "In2.Cu": 2}
board_tr, board_v = [], []
for m in re.finditer(r'^  \(segment \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\) \(width ([-\d.]+)\) \(layer "([^"]+)"\) \(net (\d+)\)', txt, re.M):
    x1, y1, x2, y2, w = (float(m.group(i)) for i in range(1, 6))
    board_tr.append((netnames[int(m.group(7))], LNAME[m.group(6)], (round(x1 - RT.OX, 3), round(y1 - RT.OY, 3)),
                     (round(x2 - RT.OX, 3), round(y2 - RT.OY, 3)), w))
for m in re.finditer(r'^  \(via \(at ([-\d.]+) ([-\d.]+)\).*?\(net (\d+)\)', txt, re.M):
    board_v.append((netnames[int(m.group(3))], round(float(m.group(1)) - RT.OX, 3), round(float(m.group(2)) - RT.OY, 3)))
print(len(board_tr), "segments", len(board_v), "vias in file", flush=True)
b = pcbnew.LoadBoard(inp)
_keep = list(b.GetTracks())
for t in _keep: b.Remove(t)
r = RT.setup(b)
key = lambda t: (t[0], t[1], (round(t[2][0], 2), round(t[2][1], 2)), (round(t[3][0], 2), round(t[3][1], 2)))
have = {key(t) for t in r.tracks}; havev = {(v[0], round(v[1], 2), round(v[2], 2)) for v in r.vias}
for t in board_tr:
    if key(t) in have: continue
    t = (t[0], t[1], (float(t[2][0]), float(t[2][1])), (float(t[3][0]), float(t[3][1])), float(t[4]))
    r.tracks.append(t)
    g = LineString([t[2], t[3]]).buffer(t[4] / 2, 8) if t[2] != t[3] else Point(t[2]).buffer(t[4] / 2, 8)
    r.add_geom(g, [t[1]], r.netid[t[0]], RT.CLASSES[RT.net_class(t[0])][1])
for v in board_v:
    if (v[0], round(v[1], 2), round(v[2], 2)) in havev: continue
    r.vias.append((v[0], float(v[1]), float(v[2])))
    r.add_geom(Point(v[1], v[2]).buffer(RT.VIA_D / 2, 16), RT.ALL, r.netid[v[0]], RT.CLASSES[RT.net_class(v[0])][1])
log = json.load(open(inp + ".routelog.json"))
fl = next(l for l in log if l.startswith("FINAL failed nets:")).split(":", 1)[1]
failed = [n.strip() for n in fl.split(",") if n.strip()]
ff = next(l for l in log if l.startswith("FINAL failed fan-outs:")).split(":", 1)[1]
fan = [x.strip() for x in ff.split(",") if x.strip()]
print("imported", len(r.tracks), "tracks", len(r.vias), "vias; failed:", failed, "fan-outs:", fan, flush=True)
FORCE = [n for n in (sys.argv[4].split(",") if len(sys.argv) > 4 else []) if n]
fixed_geo = [(t[0], t[1], LineString([t[2], t[3]]).buffer(t[4] / 2 + 0.16)) for t in r.tracks if id(t) in r.fixed_tracks and t[2] != t[3]]
fixed_geo += [(v[0], None, Point(v[1], v[2]).buffer(RT.VIA_D / 2 + 0.16)) for v in r.vias if id(v) in r.fixed_vias]
for t in r.tracks:
    if id(t) in r.fixed_tracks or t[0] in RT.PLANE_NETS: continue
    g = LineString([t[2], t[3]]).buffer(t[4] / 2) if t[2] != t[3] else Point(t[2]).buffer(t[4] / 2)
    for n, L, fg in fixed_geo:
        if n != t[0] and (L is None or L == t[1]) and fg.intersects(g):
            FORCE.append(t[0]); break
for v in r.vias:
    if id(v) in r.fixed_vias or v[0] in RT.PLANE_NETS: continue
    g = Point(v[1], v[2]).buffer(RT.VIA_D / 2)
    if any(n != v[0] and fg.intersects(g) for n, L, fg in fixed_geo): FORCE.append(v[0])
FORCE = sorted(set(FORCE)); print("force re-route:", FORCE, flush=True)
if FORCE:
    r.remove_nets(set(FORCE)); r.rebuild()
    for n in FORCE:
        if not r.route_net(n): failed.append(n)
    failed = sorted(set(failed))
r.fail_pts = {n: [p["c"] for p in r.pads[n]] for n in failed}

pair_of = {}
for name, (p, n, cls) in D.DIFF_PAIRS.items(): pair_of[p] = (p, n); pair_of[n] = (p, n)
PAIR_ORDER = ["USB3A_RX", "USB3A_D", "USB3A_TX", "ETH3", "ETH2", "ETH1", "ETH0", "HUB_UP", "USB2A_D", "AUD_USB", "ZB_USB", "USBC_D"]
prio = {}
for i, nm in enumerate(PAIR_ORDER):
    pp, nn, _ = D.DIFF_PAIRS[nm]; prio[(pp, nn)] = i

def snapshot():
    return ({k: [m.copy() for m in v] for k, v in r.maps.items()}, list(r.tracks), list(r.vias),
            {k: list(v) for k, v in r.fail_pts.items()}, set(r.fixed_tracks), set(r.fixed_vias))
def restore(s):
    r.maps = s[0]; r.tracks = s[1]; r.vias = s[2]; r.fail_pts = s[3]

t0 = time.time()
for att in range(MAXA):
    if not r.fail_pts: break
    net = random.choice(sorted(r.fail_pts))
    before = len(r.fail_pts)
    snap = snapshot()
    group = set(pair_of.get(net, (net,)))
    pts = r.fail_pts.get(net) or [p["c"] for p in r.pads[net]]
    rad = random.choice([1.0, 1.6, 2.5])
    bl0 = r.nets_near(pts, rad, group) | r.soft_blockers(net, group | set(RT.PLANE_NETS))
    if random.random() < 0.3 and len(bl0) > 2:     # sometimes rip only a subset
        bl0 = set(random.sample(sorted(bl0), max(1, len(bl0) // 2)))
    bl = set()
    for x in bl0: bl |= set(pair_of.get(x, (x,)))
    r.remove_nets(group | bl); r.rebuild()
    for g in group | bl: r.fail_pts.pop(g, None)
    prs = sorted({pair_of[x] for x in (group | bl) if x in pair_of}, key=lambda q: prio.get(q, 99))
    for pr in prs: r.route_pair(*pr)
    singles = [x for x in (group | bl) if x not in pair_of]
    random.shuffle(singles); singles.sort(key=lambda x: x != net)
    for x in singles: r.route_net(x)
    after = len(r.fail_pts)
    if after < before:
        r2 = list(r.tracks); v2 = list(r.vias)
        bb = pcbnew.LoadBoard(inp); _k = list(bb.GetTracks())
        for t in _k: bb.Remove(t)
        sv = (r.tracks, r.vias); r.write(bb); r.tracks, r.vias = r2, v2
        pcbnew.SaveBoard(outp, bb)
        json.dump(r.log + ["FINAL failed nets: " + ", ".join(sorted(r.fail_pts)), "FINAL failed fan-outs: " + ", ".join(fan)], open(outp + ".routelog.json", "w"), indent=1)
        print("  checkpoint saved", flush=True)
    if after < before or (after == before and net not in r.fail_pts and random.random() < 0.5):
        print(f"[{att}] {net}: kept, failures {before} -> {after} {sorted(r.fail_pts)} ({time.time() - t0:.0f}s)", flush=True)
    else:
        restore(snap)
        print(f"[{att}] {net}: reverted ({after} would remain)", flush=True)

# fan-outs: retry with the final copper
r.fanout_fail = []
for item in fan:
    m = re.match(r"(\S+) (\S+)\.(\S+)", item)
    if not m: continue
    net, ref, num = m.groups()
    pad = next((p for p in r.pads.get(net, []) if p["ref"] == ref and p["num"] == num), None)
    if pad: r.fanout(net, pad, net)
r.log.append("FINAL failed nets: " + ", ".join(sorted(r.fail_pts)))
r.log.append("FINAL failed fan-outs: " + ", ".join(f"{n} {p['ref']}.{p['num']}" for n, p in r.fanout_fail))
r.write(b); pcbnew.SaveBoard(outp, b)
print("\n".join(r.log[-2:]))
json.dump(r.log, open(outp + ".routelog.json", "w"), indent=1)
