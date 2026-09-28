"""Screen one CT block of an eligible 8.64 / 9.36 um volume for ink: every sheet in the block.

1. Fetch the CT block at L0 (zfetch) and the m7 surface prediction for the same block (fetch_pred).
2. Depth axis = y or x (the block sits on that side of the scroll centre, so sheets run roughly
   perpendicular to it). Every sheet is tracked through the m7 mask by sheet_grow.track_sheets (best-first
   growth over the run centres of the mask, from a 3 x 3 grid of seed columns) and snapped to the mask centre
   line (the m7 masks are clean at L0, which is the precision a 9 um ink model needs).
3. For each sheet sample a 28-layer stack from the local CT block along the depth axis (tilts are
   small; layers are spaced along the axis, not the normal) -> zarr (28, H, W) for the stock CLI.
4. Duplicate sheets (two seeds landing on one sheet) are dropped by height-map overlap.
Writes <out>/<block>/sheet_XX.zarr + sheets.json. Inference and scoring: infer_sheets.py.
"""
import argparse
import json
import os
import sys

import numpy as np
import zarr
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zfetch as zf  # noqa: E402
from fetch_pred import read_box as read_pred  # noqa: E402
from sheet_grow import track_sheets  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('volume')                   # bucket-relative CT zarr (8.64 / 9.36 um)
    ap.add_argument('pred')                     # bucket-relative m7 surface prediction zarr (L0 group)
    ap.add_argument('out')
    ap.add_argument('--centre', type=int, nargs=3, required=True, help='block centre z y x (L0)')
    ap.add_argument('--size', type=int, nargs=3, default=[464, 464, 1152], help='block size along z, depth, width')
    ap.add_argument('--axis', choices=['y', 'x'], required=True, help='depth axis (roughly the sheet normal)')
    ap.add_argument('--layers', type=int, default=28)
    ap.add_argument('--tag', default='', help='suffix for the output block directory (e.g. _g for re-renders)')
    a = ap.parse_args()
    cz, cy, cx = a.centre
    sz, sd, sw = a.size
    if a.axis == 'y':
        lo = (cz - sz // 2, cy - sd // 2, cx - sw // 2); hi = (lo[0] + sz, lo[1] + sd, lo[2] + sw)
    else:
        lo = (cz - sz // 2, cy - sw // 2, cx - sd // 2); hi = (lo[0] + sz, lo[1] + sw, lo[2] + sd)
    name = f'b_z{cz}_y{cy}_x{cx}_{a.axis}{a.tag}'
    od = os.path.join(a.out, name)
    os.makedirs(od, exist_ok=True)
    ct = zf.read_box(a.volume, 0, lo, hi)
    m7 = read_pred(f'{a.pred}/0', lo, hi) > 0
    print(name, 'ct', ct.shape, 'm7 frac', round(float(m7.mean()), 3), 'MB', round(zf.downloaded() / 1e6), flush=True)
    # depth-first views: (depth, z, width)
    if a.axis == 'y':
        CT, M = ct.transpose(1, 0, 2), m7.transpose(1, 0, 2)
    else:
        CT, M = ct.transpose(2, 0, 1), m7.transpose(2, 0, 1)
    D = CT.shape[0]
    half = a.layers // 2
    sheets = []
    for hm, V in track_sheets(M):
        ks = np.arange(a.layers) - (a.layers - 1) / 2.0
        Hh, Ww = hm.shape
        zz, ww = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
        stack = np.zeros((a.layers, Hh, Ww), np.uint8)
        for i, k in enumerate(ks):
            stack[i] = np.clip(ndimage.map_coordinates(CT, [hm + k, zz, ww], order=1, mode='constant'), 0, 255).astype(np.uint8)
        inside = V & (hm - half >= 0) & (hm + half < D) &             (CT[np.clip(np.rint(hm).astype(int), 0, D - 1), zz.astype(int), ww.astype(int)] > 0)
        if inside.mean() < 0.15:
            continue
        stack *= inside[None]
        zp = os.path.join(od, f'sheet_{len(sheets):02d}.zarr')
        zarr.open_array(zp, mode='w', shape=stack.shape, chunks=(a.layers, 128, 128), dtype='u1',
                        zarr_format=2, compressor=None, fill_value=0)[:] = stack
        np.save(zp.replace('.zarr', '_h.npy'), hm.astype(np.float32))
        sheets.append({'valid': float(inside.mean()), 'depth_range': [float(hm.min()), float(hm.max())],
                       'zarr': os.path.basename(zp), 'tracker': 'sheet_grow'})
        print(f'  sheet {len(sheets) - 1}: valid {inside.mean():.2f} depth {hm.min():.0f}-{hm.max():.0f}', flush=True)
    json.dump({'volume': a.volume, 'pred': a.pred, 'lo_zyx': list(lo), 'hi_zyx': list(hi), 'axis': a.axis,
               'layers': a.layers, 'sheets': sheets}, open(os.path.join(od, 'sheets.json'), 'w'), indent=1)
    print('sheets', len(sheets), 'area cm2 ~', round(sum(s['valid'] for s in sheets) * sz * sw * (8.64e-4) ** 2, 2))


if __name__ == '__main__':
    main()
