"""Numba-compiled A* core for router.py (8-connected, direction state, vias)."""
import heapq
import numpy as np
from numba import njit

DI = np.array([1, 1, 0, -1, -1, -1, 0, 1], np.int64)
DJ = np.array([0, 1, 1, 1, 0, -1, -1, -1], np.int64)

@njit(cache=True)
def _h(i, j, tcx, tcy, hw):
    best = 1e18
    for k in range(tcx.shape[0]):
        dx = abs(i - tcx[k]); dy = abs(j - tcy[k])
        m = dx if dx < dy else dy
        v = (dx + dy) + (1.41421 - 2.0) * m
        if v < best:
            best = v
    return best * hw

@njit(cache=True)
def astar_core(freeb, viab, bonus, use_bonus, penalty, use_pen, src, tmask, tcx, tcy,
               i0, j0, i1, j1, NX, NC, via_cost, hw, max_exp, allow_via, NL, gbuf, pbuf, DI, DJ):
    gbuf[:] = np.inf
    heap = [(0.0, 0.0, np.int64(0))]
    heap.pop()
    for s in src:
        L = s // NC; r = s - L * NC; j = r // NX; i = r - j * NX
        if i < i0 or i > i1 or j < j0 or j > j1:
            continue
        key = s * 9 + 8
        gbuf[key] = 0.0; pbuf[key] = -1
        heapq.heappush(heap, (_h(i, j, tcx, tcy, hw), 0.0, key))
    exp = 0
    TP = (0.0, 0.4, 1.5)
    while len(heap) > 0:
        f, gc, key = heapq.heappop(heap)
        if gbuf[key] < gc - 1e-9:
            continue
        cellf = key // 9; d = key - cellf * 9
        if tmask[cellf]:
            # reconstruct
            n = 0; k = key
            while k != -1:
                n += 1; k = pbuf[k]
            out = np.empty(n, np.int64)
            k = key; idx = n - 1
            while k != -1:
                out[idx] = k // 9; idx -= 1; k = pbuf[k]
            return out
        exp += 1
        if exp > max_exp:
            break
        L = cellf // NC; r = cellf - L * NC; j = r // NX; i = r - j * NX
        for nd in range(8):
            tp = 0.0
            if d != 8:
                turn = (nd - d) % 8
                if turn > 4:
                    turn = 8 - turn
                if turn >= 3:
                    continue
                tp = TP[turn]
            di = DI[nd]; dj = DJ[nd]
            ni = i + di; nj = j + dj
            if ni < i0 or ni > i1 or nj < j0 or nj > j1:
                continue
            nc = L * NC + nj * NX + ni
            if freeb[nc] == 0:
                continue
            step = 1.0
            if di != 0 and dj != 0:
                if freeb[L * NC + j * NX + ni] == 0 or freeb[L * NC + nj * NX + i] == 0:
                    continue
                step = 1.41421
            if use_bonus:
                if bonus[nc]:
                    step *= 0.3
                else:
                    step *= 1.6
            if use_pen and penalty[nc]:
                step *= 6.0
            ng = gc + step + tp
            nk = nc * 9 + nd
            if ng < gbuf[nk] - 1e-9:
                gbuf[nk] = ng; pbuf[nk] = key
                heapq.heappush(heap, (ng + _h(ni, nj, tcx, tcy, hw), ng, nk))
        if allow_via and viab[cellf]:
            for L2 in range(NL):
                if L2 == L:
                    continue
                oc = L2 * NC + r
                if freeb[oc]:
                    nk = oc * 9 + 8
                    ng = gc + via_cost
                    if ng < gbuf[nk] - 1e-9:
                        gbuf[nk] = ng; pbuf[nk] = key
                        heapq.heappush(heap, (ng + _h(i, j, tcx, tcy, hw), ng, nk))
    return np.empty(0, np.int64)
