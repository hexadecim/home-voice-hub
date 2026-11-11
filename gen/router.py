"""
HVH-1 grid router (0.1 mm grid, 3 signal layers F/In2/B + 3 plane layers).

* Obstacle maps are exact: for every routing class k a per-layer int32 map stores
  which net "owns" each grid cell within (w_k/2 + clearance) of copper:
  0 = free, n>0 = only net n nearby, -1 = blocked for everyone.
* A* with direction state (45-degree routing, turn penalties), vias between F/B.
* Plane nets (GND -> In1/In4, +5V -> In3) are connected by pad fan-out vias.
* Differential pairs: P routed first, N rewarded for running at pitch w+gap.
Run with KiCad python: /usr/bin/python3 router.py in.kicad_pcb out.kicad_pcb
"""
import os, sys, math, heapq, time, json
os.environ.setdefault("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import design as D

G = 0.1
OX, OY = 100.0, 100.0
W, H = 100.0, 80.0
NX, NY = int(round(W / G)) + 1, int(round(H / G)) + 1
NC = NX * NY
EPS = 1e-4
VIA_D, VIA_DRILL = 0.6, 0.3

CLASSES = {  # name: (track width, clearance)
    "Default": (0.15, 0.15), "USB2": (0.16, 0.15), "USB3": (0.16, 0.15), "ETH": (0.14, 0.15),
    "P3V3": (0.3, 0.15), "VBUS": (0.6, 0.2), "SPK": (0.4, 0.2), "GND": (0.25, 0.15), "P5V": (0.3, 0.2),
    "VIA": (VIA_D, 0.15),
    # "fat" classes: centre-line of the first trace of a pair must leave room for the partner
    "USB2_FAT": (0.16 + 2 * 0.40, 0.15), "USB3_FAT": (0.16 + 2 * 0.40, 0.15), "ETH_FAT": (0.14 + 2 * 0.40, 0.15),
}
def net_class(net):
    for name, (p, n, cls) in D.DIFF_PAIRS.items():
        if net in (p, n): return cls
    if net == "GND": return "GND"
    if net == "+5V": return "P5V"
    if net in ("USB1_VBUS", "USB2_VBUS"): return "VBUS"
    if net in ("+3V3", "+3V3A", "SD_VDD", "HUB_3V3", "+5V_AUD", "CODEC_REGV", "MIC_VDD", "MIC_VDD_F"): return "P3V3"
    if net in ("SPK_P", "SPK_N"): return "SPK"
    return "Default"
PLANE_NETS = {"GND": pcbnew.In1_Cu, "+5V": pcbnew.In3_Cu}
KL = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu]   # router layer index -> KiCad layer
NL = len(KL)
ALL = list(range(NL))
OUTER_ONLY = {"USB3", "ETH", "USB3_FAT", "ETH_FAT", "VBUS", "SPK", "P5V"}   # USB2 may use In2 (stripline, 90R target)
PAIR_PITCH = 0.40
NOFAT = {"USB3A_DP", "USB3A_DN"}   # pins sit in separate gaps of the USB3-A SS pin row
HIGH_SPEED = {"USB2", "USB3", "ETH"}

def L2(v): return pcbnew.ToMM(v)

class Router:
    def __init__(self, board):
        self.b = board
        self.netid = {}
        for name, ni in board.GetNetsByName().items():
            s = str(name)
            if s: self.netid[s] = ni.GetNetCode()
        self.netname = {v: k for k, v in self.netid.items()}
        self.knames = list(CLASSES.keys())
        self.maps = {k: [np.zeros((NY, NX), np.int32) for _ in range(NL)] for k in self.knames}
        xs = np.arange(NX) * G; ys = np.arange(NY) * G
        self.X, self.Y = np.meshgrid(xs, ys)
        self.tracks = []   # (net, layer, (x1,y1), (x2,y2), w)
        self.vias = []     # (net, x, y)
        self.nc_id = 1000000
        self.log = []
        self.extra_obstacles = []   # (geom, layers, netid, clr) persistent (e.g. planned zones)
        self.fail_pts = {}
        self.fanout_fail = []

    # ------------------------------------------------------------ obstacles
    def add_geom(self, geom, layers, net, clr):
        """Mark copper geometry (shapely, board-local mm) of `net` on layers (0=F,1=B)."""
        minx, miny, maxx, maxy = geom.bounds
        rmax = max(w / 2 + max(c, clr) for w, c in CLASSES.values()) + 0.05
        i0 = max(0, int(math.floor((minx - rmax) / G))); i1 = min(NX - 1, int(math.ceil((maxx + rmax) / G)))
        j0 = max(0, int(math.floor((miny - rmax) / G))); j1 = min(NY - 1, int(math.ceil((maxy + rmax) / G)))
        if i1 < i0 or j1 < j0: return
        xs = self.X[j0:j1 + 1, i0:i1 + 1]; ys = self.Y[j0:j1 + 1, i0:i1 + 1]
        d = shapely.distance(geom, shapely.points(xs.ravel(), ys.ravel())).reshape(xs.shape)
        for k, (w, c) in CLASSES.items():
            r = w / 2 + max(c, clr) - EPS
            m = d < r
            if not m.any(): continue
            for L in layers:
                sub = self.maps[k][L][j0:j1 + 1, i0:i1 + 1]
                free = (sub == 0) & m
                other = (sub != 0) & (sub != net) & m
                sub[free] = net
                sub[other] = -1

    def add_hard(self, mask_fn):
        for k, (w, c) in CLASSES.items():
            m = mask_fn(w)
            for L in ALL:
                self.maps[k][L][m] = -1

    def load_obstacles(self):
        b = self.b
        # board outline -> edge clearance 0.3 mm
        ps = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps)
        ol = ps.Outline(0)
        pts = [(L2(ol.CPoint(i).x) - OX, L2(ol.CPoint(i).y) - OY) for i in range(ol.PointCount())]
        self.board_poly = Polygon(pts)
        allp = shapely.points(self.X.ravel(), self.Y.ravel())
        inside = shapely.contains(self.board_poly, allp).reshape(self.X.shape)
        dedge = shapely.distance(self.board_poly.exterior, allp).reshape(self.X.shape)
        self.add_hard(lambda w: (~inside) | (dedge < 0.3 + w / 2 - EPS))
        # keep-out rule areas (tracks not allowed)
        for z in list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]:
            if not z.GetIsRuleArea() or not z.GetDoNotAllowTracks(): continue
            o = z.Outline().Outline(0)
            poly = Polygon([(L2(o.CPoint(i).x) - OX, L2(o.CPoint(i).y) - OY) for i in range(o.PointCount())])
            dz = shapely.distance(poly, allp).reshape(self.X.shape)
            layers = [L for L, kl in enumerate(KL) if z.IsOnLayer(kl)]
            for k, (w, c) in CLASSES.items():
                m = dz < w / 2 + 0.05
                for L in layers: self.maps[k][L][m] = -1
        # pads
        self.pads = {}   # net -> list of dict(geom, layers, center, ref, num)
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                attr = pad.GetAttribute()
                layers = [L for L, kl in enumerate(KL) if pad.IsOnLayer(kl)]
                pos = pad.GetPosition(); cx, cy = L2(pos.x) - OX, L2(pos.y) - OY
                if attr == pcbnew.PAD_ATTRIB_NPTH:
                    r = L2(pad.GetDrillSize().x) / 2
                    geom = Point(cx, cy).buffer(r, 16)
                    self.add_geom(geom, ALL, -5, 0.25)
                    continue
                if not layers: continue
                eps = pad.GetEffectivePolygon()
                o = eps.Outline(0)
                geom = Polygon([(L2(o.CPoint(i).x) - OX, L2(o.CPoint(i).y) - OY) for i in range(o.PointCount())])
                if not geom.is_valid: geom = geom.buffer(0)
                net = pad.GetNetname()
                if net:
                    nid = self.netid[net]; clr = CLASSES[net_class(net)][1]
                else:
                    self.nc_id += 1; nid = self.nc_id; clr = 0.15
                self.add_geom(geom, layers, nid, clr)
                if attr == pcbnew.PAD_ATTRIB_PTH:
                    pass
                if net:
                    self.pads.setdefault(net, []).append(dict(geom=geom, layers=layers, c=(cx, cy),
                                                              ref=fp.GetReference(), num=pad.GetNumber(), tht=(attr == pcbnew.PAD_ATTRIB_PTH)))

    # ------------------------------------------------------------ helpers
    def cell(self, x, y): return int(round(x / G)), int(round(y / G))
    def pad_cells(self, pad, freeb, layer):
        g = pad["geom"]
        minx, miny, maxx, maxy = g.bounds
        i0, j0 = int(math.ceil(minx / G)), int(math.ceil(miny / G))
        i1, j1 = int(math.floor(maxx / G)), int(math.floor(maxy / G))
        cells = []
        if i1 >= i0 and j1 >= j0:
            xs = self.X[j0:j1 + 1, i0:i1 + 1]; ys = self.Y[j0:j1 + 1, i0:i1 + 1]
            inside = shapely.contains_xy(g, xs.ravel(), ys.ravel()).reshape(xs.shape)
            for jj, ii in zip(*np.nonzero(inside)):
                c = layer * NC + (j0 + jj) * NX + (i0 + ii)
                if freeb[c]: cells.append(c)
        if not cells:
            i, j = self.cell(*pad["c"]); c = layer * NC + j * NX + i
            cells = [c]
        return cells

    def free_bytes(self, k, net):
        parts = []
        for L, m in enumerate(self.maps[k]):
            if L >= 2 and k in OUTER_ONLY: parts.append(np.zeros(NC, bool))
            else: parts.append(((m == 0) | (m == net)).ravel())
        return np.concatenate(parts).astype(np.uint8).tobytes()

    def via_bytes(self, net):
        f = np.ones((NY, NX), bool)
        for m in self.maps["VIA"]: f &= (m == 0) | (m == net)
        return np.tile(f.ravel(), NL).astype(np.uint8).tobytes()

    def reachable(self, sources, targets, freeb, viab):
        from scipy import ndimage
        f = np.frombuffer(freeb, np.uint8).reshape(NL, NY, NX)
        v = np.frombuffer(viab, np.uint8)[:NC].reshape(NY, NX)
        st = np.ones((3, 3), int)
        labs = []; off = 0
        for L in range(NL):
            l, n = ndimage.label(f[L], st)
            labs.append(np.where(l > 0, l + off, 0)); off += n
        parent = list(range(off + 1))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        pl = []
        for La in range(NL):
            for Lb in range(La + 1, NL):
                m = (v > 0) & (labs[La] > 0) & (labs[Lb] > 0)
                if m.any(): pl.append(np.stack([labs[La][m], labs[Lb][m]], 1))
        pairs = np.unique(np.concatenate(pl), axis=0) if pl else []
        for a, b in pairs:
            ra, rb = find(int(a)), find(int(b))
            if ra != rb: parent[ra] = rb
        def comp(c):
            L, r = divmod(int(c), NC); j, i = divmod(r, NX)
            lab = labs[L][j, i]
            return find(int(lab)) if lab else None
        sc = {comp(c) for c in sources} - {None}
        return any(comp(c) in sc for c in targets)

    # ------------------------------------------------------------ A*
    DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    _gbuf = None
    def astar(self, sources, targets, freeb, viab, window, via_cost=15.0, layers_ok=(0, 1),
              bonus=None, max_exp=20_000_000, target_fn=None, penalty=None, hw=1.6, tmask=None):
        """sources/targets: iterables of flat cells (L*NC + j*NX + i). Returns path (list of flat cells)."""
        import nbastar
        if Router._gbuf is None:
            Router._gbuf = np.empty(NL * NC * 9, np.float64)
            Router._pbuf = np.empty(NL * NC * 9, np.int64)
        i0, j0, i1, j1 = window
        if tmask is None:
            tmask = np.zeros(NL * NC, np.uint8)
            tl = np.fromiter(targets, np.int64)
            tmask[tl] = 1
        else:
            tl = np.nonzero(tmask)[0]
        if len(tl) == 0: return None
        samp = tl[:: max(1, len(tl) // 60)]
        rr = samp % NC
        tcx = (rr % NX).astype(np.float64); tcy = (rr // NX).astype(np.float64)
        fb = np.frombuffer(freeb, np.uint8); vb = np.frombuffer(viab, np.uint8)
        bb = np.frombuffer(bonus, np.uint8) if bonus is not None else np.zeros(1, np.uint8)
        gp = getattr(self, "global_pen", None)
        if gp is not None:
            pb = gp | (np.frombuffer(penalty, np.uint8) if penalty is not None else 0)
            penalty = True
        else:
            pb = np.frombuffer(penalty, np.uint8) if penalty is not None else np.zeros(1, np.uint8)
        src = np.array(list(sources), np.int64)
        path = nbastar.astar_core(fb, vb, bb, bonus is not None, pb, penalty is not None, src, tmask, tcx, tcy,
                                  i0, j0, i1, j1, NX, NC, float(via_cost), float(hw), int(max_exp), len(layers_ok) >= 2, NL,
                                  Router._gbuf, Router._pbuf, nbastar.DI, nbastar.DJ)
        if len(path) == 0: return None
        return [int(c) for c in path]

    # ------------------------------------------------------------ commit
    def commit_path(self, net, path, w, clr):
        nid = self.netid[net]
        segs = []
        pts = [(c // NC, (c % NC) % NX, (c % NC) // NX) for c in path]
        # split into layer runs, record vias
        run = [pts[0]]
        for p in pts[1:]:
            if p[0] != run[-1][0]:
                self.vias.append((net, float(p[1] * G), float(p[2] * G)))
                g = Point(p[1] * G, p[2] * G).buffer(VIA_D / 2, 16)
                self.add_geom(g, ALL, nid, clr)
                segs.append(run); run = [p]
            else:
                run.append(p)
        segs.append(run)
        for run in segs:
            if len(run) < 2: continue
            # compress collinear
            out = [run[0]]
            for a, bb, c in zip(run, run[1:], run[2:]):
                if (bb[1] - a[1], bb[2] - a[2]) != (c[1] - bb[1], c[2] - bb[2]):
                    out.append(bb)
            out.append(run[-1])
            L = run[0][0]
            for a, bb in zip(out, out[1:]):
                p1 = (a[1] * G, a[2] * G); p2 = (bb[1] * G, bb[2] * G)
                if p1 == p2: continue
                self.tracks.append((net, L, (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1])), w))
                geom = LineString([p1, p2]).buffer(w / 2, 8)
                self.add_geom(geom, [L], nid, clr)

    def window_for(self, pads, margin):
        xs = [p["c"][0] for p in pads]; ys = [p["c"][1] for p in pads]
        i0 = max(0, int((min(xs) - margin) / G)); i1 = min(NX - 1, int((max(xs) + margin) / G))
        j0 = max(0, int((min(ys) - margin) / G)); j1 = min(NY - 1, int((max(ys) + margin) / G))
        return (i0, j0, i1, j1)

    # ------------------------------------------------------------ net routing
    def snapshot(self):
        return ({k: [m.copy() for m in v] for k, v in self.maps.items()}, len(self.tracks), len(self.vias))
    def restore(self, snap):
        maps, nt, nv = snap
        self.maps = maps; del self.tracks[nt:]; del self.vias[nv:]

    def reserve_bytes(self, net, radius=0.55):
        pads = self.pads.get(net, [])
        if not pads: return None
        geoms = shapely.unary_union([p["geom"] for p in pads])
        d = self.wdist(geoms, radius + 0.2)
        m = (d < radius) & (d > 0)
        return np.tile(m.ravel(), NL).astype(np.uint8).tobytes()

    def wdist(self, geom, maxd):
        """distance field from geom, evaluated only within bbox+maxd (inf elsewhere)."""
        d = np.full(self.X.shape, np.inf)
        minx, miny, maxx, maxy = geom.bounds
        i0 = max(0, int((minx - maxd) / G)); i1 = min(NX - 1, int((maxx + maxd) / G) + 1)
        j0 = max(0, int((miny - maxd) / G)); j1 = min(NY - 1, int((maxy + maxd) / G) + 1)
        xs = self.X[j0:j1 + 1, i0:i1 + 1]; ys = self.Y[j0:j1 + 1, i0:i1 + 1]
        d[j0:j1 + 1, i0:i1 + 1] = shapely.distance(geom, shapely.points(xs.ravel(), ys.ravel())).reshape(xs.shape)
        return d

    def near_bytes(self, nets, radius):
        geoms = shapely.unary_union([p["geom"] for n in nets for p in self.pads.get(n, [])])
        return self.wdist(geoms, radius + 0.2) < radius

    def route_net(self, net, bonus=None, via_cost=None, penalty=None, fat=None, hw=1.6):
        cls = net_class(net); w, clr = CLASSES[cls]
        nid = self.netid[net]
        pads = self.pads.get(net, [])
        if len(pads) < 2: return True
        freeb = self.free_bytes(cls, nid); viab = self.via_bytes(nid)
        if fat is not None:   # (fat class name, near-pad mask)
            fk, near = fat
            parts = []
            for L in range(NL):
                if L >= 2 and fk in OUTER_ONLY: parts.append(np.zeros(NC, bool)); continue
                m = self.maps[fk][L]; n = self.maps[cls][L]
                parts.append((((m == 0) | (m == nid)) | (((n == 0) | (n == nid)) & near)).ravel())
            freeb = np.concatenate(parts).astype(np.uint8).tobytes()
        vc = via_cost if via_cost is not None else (40.0 if cls in HIGH_SPEED and not net.startswith("USBC_") else 12.0)
        # group pads that already touch (e.g. ESD flow-through pins) into terminals
        remaining = list(range(len(pads)))
        # start with pad farthest from centroid
        cx = sum(p["c"][0] for p in pads) / len(pads); cy = sum(p["c"][1] for p in pads) / len(pads)
        start = max(remaining, key=lambda i: (pads[i]["c"][0] - cx) ** 2 + (pads[i]["c"][1] - cy) ** 2)
        tree = []
        for L in pads[start]["layers"]:
            tree += self.pad_cells(pads[start], freeb, L)
        remaining.remove(start)
        partial = False
        while remaining:
            tgt = {}
            for pi in remaining:
                for L in pads[pi]["layers"]:
                    for c in self.pad_cells(pads[pi], freeb, L):
                        tgt[c] = pi
            path = None
            unreach = [pi for pi in remaining if not self.reachable(tree, [c for c, v in tgt.items() if v == pi], freeb, viab)]
            if unreach:
                self.log.append(f"FAIL {net}: unreachable {[pads[i]['ref']+'.'+pads[i]['num'] for i in unreach]}")
                self.fail_pts.setdefault(net, []).extend(pads[i]["c"] for i in unreach)
                for pi in unreach: remaining.remove(pi)
                tgt = {c: v for c, v in tgt.items() if v not in unreach}
                partial = True
                if not remaining: return False
            for margin in (6.0, 15.0, 120.0):
                win = self.window_for([pads[i] for i in remaining] + [pads[start]], margin)
                # include whole tree in window
                path = self.astar(tree, tgt.keys(), freeb, viab, win, via_cost=vc, bonus=bonus, penalty=penalty, hw=hw)
                if path: break
            if not path:
                self.log.append(f"FAIL {net}: {len(remaining)} pads unrouted ({[pads[i]['ref']+'.'+pads[i]['num'] for i in remaining]})")
                self.fail_pts.setdefault(net, []).extend(pads[i]["c"] for i in remaining)
                return False
            hit = tgt[path[-1]]
            self.commit_path(net, path, w, clr)
            # refresh free maps (own copper doesn't block itself, but other nets unaffected)
            tree += path
            for L in pads[hit]["layers"]:
                tree += self.pad_cells(pads[hit], freeb, L)
            remaining.remove(hit)
            # pads that the new copper already overlaps count as connected
            pg = shapely.unary_union([LineString([(pp[1] * G, pp[2] * G) for pp in [(c // NC, (c % NC) % NX, (c % NC) // NX) for c in path]]).buffer(w / 2)]) if len(path) > 1 else None
            if pg is not None:
                for pi in list(remaining):
                    if pg.intersects(pads[pi]["geom"]):
                        remaining.remove(pi)
                        for L in pads[pi]["layers"]: tree += self.pad_cells(pads[pi], freeb, L)
        return not partial

    def bonus_bytes(self, net):
        cls = net_class(net); w, clr = CLASSES[cls]
        pitch = PAIR_PITCH
        pl = [t for t in self.tracks if t[0] == net]
        if not pl: return None
        lines = shapely.unary_union([LineString([t[2], t[3]]) for t in pl])
        d = self.wdist(lines, pitch + 0.3)
        band = (d >= pitch - 0.06) & (d <= pitch + 0.06)
        return np.tile(band.ravel(), NL).astype(np.uint8).tobytes()

    def route_pair(self, pnet, nnet):
        cls = net_class(pnet)
        near = self.near_bytes([pnet, nnet], 1.3)
        for a, b in ((pnet, nnet), (nnet, pnet)):
            for use_fat in ((False,) if {pnet, nnet} & NOFAT else (True, False)):
                snap = self.snapshot(); nlog = len(self.log)
                ok = self.route_net(a, penalty=self.reserve_bytes(b), fat=(cls + "_FAT", near) if use_fat else None)
                if ok:
                    ok = self.route_net(b, bonus=self.bonus_bytes(a), hw=1.0)
                if ok:
                    self.fail_pts.pop(pnet, None); self.fail_pts.pop(nnet, None)
                    return True
                self.restore(snap); del self.log[nlog:]
        self.log.append(f"FAIL pair {pnet}/{nnet}")
        return False

    def fanout(self, net, pad, plane_layer_name):
        """Connect an SMD pad of a plane net to the plane with a short stub + via."""
        nid = self.netid[net]; cls = net_class(net); w, clr = CLASSES[cls]
        freeb = self.free_bytes(cls, nid); viab = self.via_bytes(nid)
        L = pad["layers"][0]
        src = self.pad_cells(pad, freeb, L)
        pg = pad["geom"]
        win = self.window_for([pad], 3.0)
        i0, j0, i1, j1 = win
        tm = np.zeros(NL * NC, np.uint8)
        vb = np.frombuffer(viab, np.uint8)[L * NC:(L + 1) * NC].reshape(NY, NX)
        sub = vb[j0:j1 + 1, i0:i1 + 1].astype(bool)
        xs = self.X[j0:j1 + 1, i0:i1 + 1]; ys = self.Y[j0:j1 + 1, i0:i1 + 1]
        dd = shapely.distance(pg, shapely.points(xs.ravel(), ys.ravel())).reshape(xs.shape)
        sub &= dd >= 0.32
        full = np.zeros((NY, NX), bool); full[j0:j1 + 1, i0:i1 + 1] = sub
        tm[L * NC:(L + 1) * NC] = full.ravel()
        if not hasattr(self, "_foreign_pad_d"):
            allp = shapely.unary_union([p["geom"] for n, pl in self.pads.items() for p in pl])
            self._allpads = allp
        others = [p["geom"] for n, pl in self.pads.items() if n != net for p in pl
                  if p["geom"].distance(pg) < 3.5]
        pen = None
        if others:
            dd2 = shapely.distance(shapely.unary_union(others), shapely.points(xs.ravel(), ys.ravel())).reshape(xs.shape)
            pm = np.zeros((NY, NX), bool); pm[j0:j1 + 1, i0:i1 + 1] = dd2 < 0.9
            pen = np.tile(pm.ravel(), NL).astype(np.uint8).tobytes()
        path = self.astar(src, None, freeb, viab, win, via_cost=1e9, layers_ok=(L,), tmask=tm, max_exp=400000, penalty=pen, hw=1.0)
        if not path and self.via_in_pad(net, pad):
            return True
        if not path:
            self.log.append(f"FANOUT FAIL {net} {pad['ref']}.{pad['num']}")
            self.fanout_fail.append((net, pad))
            return False
        last = path[-1]; r = last % NC; j, i = divmod(r, NX)
        if len(path) > 1:
            self.commit_path(net, path, w, clr)
        self.vias.append((net, float(i * G), float(j * G)))
        self.add_geom(Point(i * G, j * G).buffer(VIA_D / 2, 16), ALL, nid, clr)
        return True

    SMALL_VIA = (0.45, 0.2)
    def via_in_pad(self, net, pad):
        """Fallback plane connection: a filled 0.45/0.2 mm via inside the pad (JLC 6-layer boards
        get epoxy-filled, capped vias at no extra cost). Exposed pads get a 2x2 array."""
        g = pad["geom"]; cx, cy = g.centroid.x, g.centroid.y
        minx, miny, maxx, maxy = g.bounds
        pts = [(cx, cy)]
        if (maxx - minx) > 2.0 and (maxy - miny) > 2.0:
            dx, dy = (maxx - minx) / 4, (maxy - miny) / 4
            pts = [(cx - dx, cy - dy), (cx + dx, cy - dy), (cx - dx, cy + dy), (cx + dx, cy + dy)]
        need = self.SMALL_VIA[0] / 2 + 0.15
        foreign = [p["geom"] for n, pl in self.pads.items() if n != net for p in pl if p["geom"].distance(g) < 1.5]
        foreign += [LineString([t[2], t[3]]).buffer(t[4] / 2) if t[2] != t[3] else Point(t[2]).buffer(t[4] / 2)
                    for t in self.tracks if t[0] != net and min(Point(t[2]).distance(g), Point(t[3]).distance(g), LineString([t[2], t[3]]).distance(g) if t[2] != t[3] else 9) < 1.5]
        foreign += [Point(v[1], v[2]).buffer(VIA_D / 2) for v in self.vias if v[0] != net and Point(v[1], v[2]).distance(g) < 1.5]
        fu = shapely.unary_union(foreign) if foreign else None
        ok = [p for p in pts if fu is None or fu.distance(Point(p)) >= need]
        if not ok: return False
        if not hasattr(self, "small_vias"): self.small_vias = []
        nid = self.netid[net]
        for x, y in ok:
            self.small_vias.append((net, float(x), float(y)))
            self.add_geom(Point(x, y).buffer(self.SMALL_VIA[0] / 2, 16), ALL, nid, 0.15)
        self.log.append(f"via-in-pad {net} {pad['ref']}.{pad['num']} x{len(ok)}")
        return True

    # ------------------------------------------------------------ rip-up support
    def rebuild(self):
        self.maps = {k: [np.zeros((NY, NX), np.int32) for _ in range(NL)] for k in self.knames}
        saved_pads = self.pads
        self.nc_id = 1000000
        self.load_obstacles()
        self.pads = saved_pads
        for g, layers, nid, clr in self.extra_obstacles:
            self.add_geom(g, layers, nid, clr)
        for net, L, p1, p2, w in self.tracks:
            nid = self.netid[net]; clr = CLASSES[net_class(net)][1]
            g = LineString([p1, p2]).buffer(w / 2, 8) if p1 != p2 else Point(p1).buffer(w / 2, 8)
            self.add_geom(g, [L], nid, clr)
        for net, x, y in self.vias:
            self.add_geom(Point(x, y).buffer(VIA_D / 2, 16), ALL, self.netid[net], CLASSES[net_class(net)][1])
        for net, x, y in getattr(self, "small_vias", []):
            self.add_geom(Point(x, y).buffer(self.SMALL_VIA[0] / 2, 16), ALL, self.netid[net], 0.15)

    def soft_blockers(self, net, exclude):
        """Route `net` treating other nets' (non-fixed) tracks/vias as expensive but passable;
        return the nets whose copper the cheapest such route runs through."""
        if not hasattr(self, "static"): return set()
        cls = net_class(net); nid = self.netid[net]
        pads = self.pads.get(net, [])
        if len(pads) < 2: return set()
        cur_f = np.frombuffer(self.free_bytes(cls, nid), np.uint8)
        cur_v = np.frombuffer(self.via_bytes(nid), np.uint8)
        maps_bak = self.maps; self.maps = self.static
        st_f = np.frombuffer(self.free_bytes(cls, nid), np.uint8)
        st_v = np.frombuffer(self.via_bytes(nid), np.uint8)
        self.maps = maps_bak
        pen = (st_f.astype(bool) & ~cur_f.astype(bool)).astype(np.uint8)
        gp = getattr(self, "global_pen", None); self.global_pen = None
        cells = []
        try:
            src = []
            for L in pads[0]["layers"]: src += self.pad_cells(pads[0], st_f.tobytes(), L)
            for p in pads[1:]:
                tg = []
                for L in p["layers"]: tg += self.pad_cells(p, st_f.tobytes(), L)
                win = self.window_for([pads[0], p], 15.0)
                path = self.astar(src, tg, st_f.tobytes(), st_v.tobytes(), win, via_cost=12.0, penalty=pen.tobytes(), hw=1.2)
                if path: cells += [c for c in path if pen[c]]
        finally:
            self.global_pen = gp
        pts = [(((c % NC) % NX) * G, ((c % NC) // NX) * G) for c in cells[::2]]
        return self.nets_near(pts, 0.45, exclude) if pts else set()

    def remove_nets(self, nets):
        keep_fixed = getattr(self, "fixed_tracks", set())
        self.tracks = [t for i, t in enumerate(self.tracks) if t[0] not in nets or id(t) in keep_fixed]
        kv = getattr(self, "fixed_vias", set())
        self.vias = [v for v in self.vias if v[0] not in nets or id(v) in kv]

    def nets_near(self, pts, radius, exclude):
        out = set()
        for net, L, p1, p2, w in self.tracks:
            if net in exclude or net in PLANE_NETS: continue
            ls = LineString([p1, p2]) if p1 != p2 else Point(p1)
            for p in pts:
                if ls.distance(Point(p)) < radius:
                    out.add(net); break
        for net, x, y in self.vias:
            if net in exclude or net in PLANE_NETS: continue
            for p in pts:
                if math.hypot(p[0] - x, p[1] - y) < radius:
                    out.add(net); break
        return out

    # ------------------------------------------------------------ output
    def merge_vias(self):
        """Same-net vias closer than a drill spacing allows: keep one, join the other's tracks to it."""
        keep = []
        for v in self.vias:
            near = next((k for k in keep if k[0] == v[0] and math.hypot(k[1] - v[1], k[2] - v[2]) < VIA_D + 0.05), None)
            if near is None: keep.append(v); continue
            d = math.hypot(near[1] - v[1], near[2] - v[2])
            if d > 1e-6:
                for L in ALL:
                    if any(t[0] == v[0] and t[1] == L and (math.hypot(t[2][0] - v[1], t[2][1] - v[2]) < 1e-3 or math.hypot(t[3][0] - v[1], t[3][1] - v[2]) < 1e-3) for t in self.tracks):
                        self.tracks.append((v[0], L, (v[1], v[2]), (near[1], near[2]), 0.3))
        n = len(self.vias) - len(keep)
        self.vias = keep
        return n

    def write(self, board):
        nets = board.GetNetsByName()
        nm = self.merge_vias()
        if nm: self.log.append(f"merged {nm} duplicate/near vias")
        for net, L, p1, p2, w in self.tracks:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0] + OX), pcbnew.FromMM(p1[1] + OY)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p2[0] + OX), pcbnew.FromMM(p2[1] + OY)))
            t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(KL[L])
            t.SetNet(nets[net]); board.Add(t)
        for net, x, y in getattr(self, "small_vias", []):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x + OX), pcbnew.FromMM(y + OY)))
            v.SetWidth(pcbnew.FromMM(self.SMALL_VIA[0])); v.SetDrill(pcbnew.FromMM(self.SMALL_VIA[1]))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNet(nets[net]); board.Add(v)
        for net, x, y in self.vias:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x + OX), pcbnew.FromMM(y + OY)))
            v.SetWidth(pcbnew.FromMM(VIA_D)); v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNet(nets[net]); board.Add(v)


P5V_EXTRA = []
P5V_ZONES = [  # planned +5V copper on F.Cu (board-local mm); also created as real zones by pcb_finish.py
    [(54.9, 60.3), (57.85, 60.3), (57.85, 62.5), (54.9, 62.5)],        # CM5 +5V pins 77..87
]

def df40_gnd(r, b):
    """CM5 connectors: every GND pin gets a short stub into the channel between the two
    pin rows (under the connector body), a GND spine runs along the channel centre and
    vias drop from the spine to the In1 GND plane. Signal escape lanes stay untouched."""
    nid = r.netid["GND"]; n = 0
    for ref in ("J10", "J11"):
        fp = b.FindFootprintByReference(ref)
        cx = L2(fp.GetPosition().x) - OX
        ys = []
        for p in fp.Pads():
            if p.GetNetname() != "GND": continue
            px, py = L2(p.GetPosition().x) - OX, L2(p.GetPosition().y) - OY
            p1, p2 = (px, py), (cx, py)
            r.tracks.append(("GND", 0, p1, p2, 0.15))
            r.add_geom(LineString([p1, p2]).buffer(0.075, 8), [0], nid, 0.15)
            ys.append(py)
            r.pads["GND"] = [q for q in r.pads["GND"] if not (q["ref"] == ref and q["num"] == p.GetNumber())]
        ys.sort()
        # the channel between the two pin rows belongs to GND only (no foreign tracks/vias on F.Cu)
        ch = Polygon([(cx - 1.05, ys[0] - 0.6), (cx + 1.05, ys[0] - 0.6), (cx + 1.05, ys[-1] + 0.6), (cx - 1.05, ys[-1] + 0.6)])
        r.extra_obstacles.append((ch, [0], nid, 0.0)); r.add_geom(ch, [0], nid, 0.0)
        # soft keep-clear strips beside both pin rows: tracks should leave the rows perpendicularly
        USE_PEN = False
        if USE_PEN and getattr(r, "global_pen", None) is None: r.global_pen = np.zeros(NL * NC, np.uint8)
        y0, y1 = ys[0] - 0.4, ys[-1] + 0.4
        for xa, xb in ((cx - 1.9 - 1.6, cx - 1.9), (cx + 1.9, cx + 1.9 + 1.6)):
            i0, i1 = int(round((xa) / G)), int(round((xb) / G)); j0, j1 = int(round(y0 / G)), int(round(y1 / G))
            for L in (range(NL) if USE_PEN else ()):
                v = r.global_pen[L * NC:(L + 1) * NC].reshape(NY, NX); v[j0:j1 + 1, i0:i1 + 1] = 1
        r.tracks.append(("GND", 0, (cx, ys[0]), (cx, ys[-1]), 0.3))
        r.add_geom(LineString([(cx, ys[0]), (cx, ys[-1])]).buffer(0.15, 8), [0], nid, 0.15)
        y = ys[0]; last = -9
        while y <= ys[-1] + 1e-6:
            if y - last >= 1.2:
                r.vias.append(("GND", cx, round(y, 2)))
                r.add_geom(Point(cx, y).buffer(VIA_D / 2, 16), ALL, nid, 0.15)
                last = y; n += 1
            y += 0.4
    return n

ESC_CLASSES = {"Default", "P3V3"}
ESC_FORCE = {"LED_ACT_N", "FAN_PWM", "ETH_LED3_N"}   # dog-bone even though the destination is on the escape side (frees the FAN_PWM lane)
DEBUG_ESC = False
def df40_escapes(r, b):
    """Planned dog-bone escapes for CM5 connector pins whose net has to cross to the other side
    of the connector: short F.Cu stub straight out of the row, then a via, positions chosen so
    that neighbouring escapes all fit. The via becomes the net's terminal for normal routing."""
    r.fixed_tracks = getattr(r, "fixed_tracks", set()); r.fixed_vias = getattr(r, "fixed_vias", set())
    jobs = []
    for ref in ("J10", "J11"):
        fp = b.FindFootprintByReference(ref)
        cx = L2(fp.GetPosition().x) - OX
        for p in fp.Pads():
            net = p.GetNetname()
            if not net or net in PLANE_NETS or net_class(net) not in ESC_CLASSES or net not in r.pads: continue
            px, py = L2(p.GetPosition().x) - OX, L2(p.GetPosition().y) - OY
            side = 1 if px > cx else -1
            others = [q for q in r.pads[net] if not (q["ref"] == ref and q["num"] == p.GetNumber())]
            if not others: continue
            if net not in ESC_FORCE and all((q["c"][0] - cx) * side > 0 for q in others): continue   # destination on the escape side already
            jobs.append((ref, p.GetNumber(), net, px, py, side))
    jobs.sort(key=lambda j: (j[0], j[5], j[4]))
    vg = []   # placed (geom of via, net)
    n_ok = 0
    def cand_list(job):
        ref, num, net, px, py, side = job
        nid = r.netid[net]; w, clr = CLASSES[net_class(net)]
        fb = np.frombuffer(r.free_bytes(net_class(net), nid), np.uint8)
        vb = np.frombuffer(r.via_bytes(nid), np.uint8)
        edge = px + side * 0.35
        out = []
        for k in range(5, 32):
            xv = round(edge + side * k * 0.1, 2)
            for dy10 in (0, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6):
                yv = round(py + dy10 * 0.1, 2)
                xb = xv - side * abs(dy10) * 0.1
                if (xb - edge) * side < 0.15: continue
                pts = [(px, py), (xb, py), (xv, yv)]
                cells = []
                ok = True
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    nstep = max(1, int(round(max(abs(x2 - x1), abs(y2 - y1)) / G)))
                    for t in range(nstep + 1):
                        x = x1 + (x2 - x1) * t / nstep; y = y1 + (y2 - y1) * t / nstep
                        i, j = r.cell(x, y)
                        if not fb[j * NX + i]: ok = False; break
                    if not ok: break
                if not ok: continue
                i, j = r.cell(xv, yv)
                if not vb[j * NX + i]: continue
                out.append((abs(xv - edge) + 0.6 * abs(dy10) * 0.1, pts, xv, yv))
        out.sort(key=lambda c: c[0])
        return out
    # cluster neighbouring escapes (same row, chained within 1.3 mm) and solve each cluster by DFS
    groups = []
    for jb in jobs:
        if groups and groups[-1][-1][0] == jb[0] and groups[-1][-1][5] == jb[5] and abs(groups[-1][-1][4] - jb[4]) < 1.3:
            groups[-1].append(jb)
        else:
            groups.append([jb])
    def place(job, pts, xv, yv):
        ref, num, net, px, py, side = job
        nid = r.netid[net]; w, clr = CLASSES[net_class(net)]
        mine = []
        for p1, p2 in zip(pts, pts[1:]):
            if p1 == p2: continue
            t = (net, 0, (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1])), w)
            r.tracks.append(t); mine.append(t)
            r.add_geom(LineString([p1, p2]).buffer(w / 2, 8), [0], nid, clr)
        v = (net, float(xv), float(yv)); r.vias.append(v)
        r.add_geom(Point(xv, yv).buffer(VIA_D / 2, 16), ALL, nid, clr)
        return mine, v
    budget = [0]
    def dfs(grp, k, wj0, wj1, chosen):
        if k == len(grp): return True
        for cost, pts, xv, yv in cand_list(grp[k])[:24]:
            budget[0] += 1
            if budget[0] > 20000: return False
            snap = ({kk: [m[wj0:wj1].copy() for m in v] for kk, v in r.maps.items()}, len(r.tracks), len(r.vias))
            mine, v = place(grp[k], pts, xv, yv)
            chosen.append((grp[k], mine, v, xv, yv))
            if dfs(grp, k + 1, wj0, wj1, chosen): return True
            chosen.pop()
            for kk, vv in snap[0].items():
                for L, sub in enumerate(vv): r.maps[kk][L][wj0:wj1] = sub
            del r.tracks[snap[1]:]; del r.vias[snap[2]:]
        return False
    for grp in groups:
        ys = [j[4] for j in grp]
        wj0, wj1 = r.cell(0, min(ys) - 3.5)[1], r.cell(0, max(ys) + 3.5)[1]
        # if the whole cluster cannot be solved, drop its hardest member(s) and retry
        todo = list(grp)
        while todo:
            budget[0] = 0; chosen = []
            if dfs(todo, 0, wj0, wj1, chosen):
                for (ref, num, net, px, py, side), mine, v, xv, yv in chosen:
                    for t in mine: r.fixed_tracks.add(id(t))
                    r.fixed_vias.add(id(v))
                    r.pads[net] = [q for q in r.pads[net] if not (q["ref"] == ref and q["num"] == num)] + [
                        dict(geom=Point(xv, yv).buffer(VIA_D / 2, 16), layers=ALL, c=(xv, yv), ref=ref + "v", num=num, tht=True)]
                    n_ok += 1
                break
            drop = todo.pop(len(todo) // 2)
            r.log.append(f"ESCAPE FAIL {drop[2]} {drop[0]}.{drop[1]}")
    return n_ok, len(jobs)

def setup(b):
    r = Router(b)
    t0 = time.time()
    r.load_obstacles()
    print(f"obstacles loaded {time.time() - t0:.1f}s", flush=True)
    # planned +5V zones are obstacles for everyone else
    for z in P5V_ZONES:
        g = Polygon(z); r.extra_obstacles.append((g, [0], r.netid["+5V"], 0.2)); r.add_geom(g, [0], r.netid["+5V"], 0.2)
    # TPD4EUSB30: tie GND pins 3 and 8 under the package
    for fp in b.GetFootprints():
        if fp.GetValue() != "TPD4EUSB30": continue
        p3 = fp.FindPadByNumber("3"); p8 = fp.FindPadByNumber("8")
        a = (L2(p3.GetPosition().x) - OX, L2(p3.GetPosition().y) - OY); c = (L2(p8.GetPosition().x) - OX, L2(p8.GetPosition().y) - OY)
        r.tracks.append(("GND", 0, a, c, 0.25))
        r.add_geom(LineString([a, c]).buffer(0.125, 8), [0], r.netid["GND"], 0.15)
        r.pads["GND"] = [p for p in r.pads["GND"] if not (p["ref"] == fp.GetReference() and p["num"] == "3")]
    nv = df40_gnd(r, b)
    print(f"CM5 connector GND channel vias {nv}", flush=True)
    ne = df40_escapes(r, b)
    print(f"CM5 connector dog-bone escapes {ne[0]}/{ne[1]}", [l for l in r.log if l.startswith("ESCAPE")], flush=True)
    # +5V pads covered by a planned zone don't need their own fan-out
    zp = shapely.unary_union([Polygon(z) for z in P5V_ZONES])
    r.pads["+5V"] = [p for p in r.pads["+5V"] if not p["geom"].intersects(zp)]
    r.static = {k: [m.copy() for m in v] for k, v in r.maps.items()}   # fixed copper only (for rip-up analysis)
    return r

def main(inp, outp, only=None):
    b = pcbnew.LoadBoard(inp)
    _keep = list(b.GetTracks())
    for t in _keep: b.Remove(t)
    r = setup(b)
    # short critical nets first
    done = set()
    PAIR_ORDER = ["USB3A_RX", "USB3A_D", "USB3A_TX", "ETH3", "ETH2", "ETH1", "ETH0", "HUB_UP", "USB2A_D", "AUD_USB", "ZB_USB", "USBC_D"]
    for name in PAIR_ORDER:
        p, n, cls = D.DIFF_PAIRS[name]
        t0 = time.time()
        ok = r.route_pair(p, n)
        print(f"pair {name}: {'ok' if ok else 'FAIL'} {time.time() - t0:.1f}s", flush=True)
        done |= {p, n}
    first = ["SD_PWR_ON", "SD_D2", "SD_D1", "SD_D0", "SD_CMD", "SD_D3", "SD_CLK", "SD_VDD",
             "CC1", "CC2", "VBAT", "PWR_BUT", "GPIO_VREF", "FAN_TACH", "ETH_LED2_N", "ETH_LED3_N",
             "DBG_RX", "DBG_TX", "ZB_TXD", "ZB_RXD", "ZB_SWDIO", "ZB_SWCLK", "ZB_SWO", "ZB_RST_N", "ZB_CTS", "ZB_RTS",
             "HUB_D4_P", "HUB_D4_N", "CP_VBUS", "LED_ACT_N", "VBUS_EN", "FAN_PWM", "HUB_XOUT", "HUB_XIN", "CP_RST_N"]
    for n in first:
        ok = r.route_net(n); print(f"net {n}: {'ok' if ok else 'FAIL'}", flush=True)
    done |= set(first)
    rest = [n for n in r.pads if n not in done and n not in PLANE_NETS and len(r.pads[n]) >= 2]
    def span(n):
        xs = [p["c"][0] for p in r.pads[n]]; ys = [p["c"][1] for p in r.pads[n]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    rest.sort(key=lambda n: (net_class(n) not in ("VBUS", "P3V3", "SPK"), span(n)))
    for n in rest:
        t0 = time.time()
        ok = r.route_net(n)
        print(f"net {n}: {'ok' if ok else 'FAIL'} {time.time() - t0:.1f}s", flush=True)
    # remaining plane fan-outs
    for net in PLANE_NETS:
        for pad in r.pads.get(net, []):
            if pad["tht"]: continue
            r.fanout(net, pad, net)
    # ---------------- rip-up and re-route
    pair_of = {}
    for name, (p, n, cls) in D.DIFF_PAIRS.items():
        pair_of[p] = (p, n); pair_of[n] = (p, n)
    for it in range(8):
        failed = list(r.fail_pts.keys())
        ffan = list(r.fanout_fail)
        if not failed and not ffan: break
        print(f"rip-up iteration {it}: {len(failed)} nets, {len(ffan)} fan-outs", flush=True)
        for net in failed:
            pts = r.fail_pts.get(net, [])
            if not pts: continue
            group = set(pair_of.get(net, (net,)))
            blockers = r.nets_near(pts, 1.6, group) | r.soft_blockers(net, group | set(PLANE_NETS))
            bl = set()
            for x in blockers: bl |= set(pair_of.get(x, (x,)))
            r.remove_nets(group | bl)
            r.rebuild()
            for g in group | bl: r.fail_pts.pop(g, None)
            # re-route in the global priority order (pairs keep the order that is known to work)
            prs = {pair_of[x] for x in (group | bl) if x in pair_of}
            prio = {}
            for i, nm in enumerate(PAIR_ORDER):
                pp, nn, _ = D.DIFF_PAIRS[nm]; prio[(pp, nn)] = i
            okf = True
            for pr in sorted(prs, key=lambda q: prio.get(q, 99)):
                ok = r.route_pair(*pr)
                if net in pr: okf = ok
            singles = [x for x in (group | bl) if x not in pair_of]
            singles.sort(key=lambda x: (x != net, x))
            for x in singles:
                ok = r.route_net(x)
                if x == net: okf = ok
            print(f"  {net}: {'ok' if okf else 'FAIL'}; re-routed {sorted(bl - group)}", flush=True)
        r.fanout_fail = []
        for net, pad in ffan:
            r.fanout(net, pad, net)
    r.log.append("FINAL failed nets: " + ", ".join(sorted(r.fail_pts)))
    r.log.append("FINAL failed fan-outs: " + ", ".join(f"{n} {p['ref']}.{p['num']}" for n, p in r.fanout_fail))
    r.write(b)
    pcbnew.SaveBoard(outp, b)
    print("\n".join(r.log[-2:]))
    json.dump(r.log, open(outp + ".routelog.json", "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None)
