"""Track ONE sheet over a large region from a seed point, render it, and run the ink models.

Region: z [z0, z1), depth axis y [y0, y1), x [x0, x1) (L0). The m7 mask and CT are read (from the cache
when already downloaded), the sheet is grown by sheet_grow.grow() from the seed column (zs, xs) at the run
centre nearest to depth ds, then snapped to the full-resolution run centres and rendered as a 28-layer stack along the depth axis (as
blockscan.py does). Writes <out>/sheet_00.zarr, sheet_00_h.npy, sheet_valid.npy and runs infer_sheets.py on it
with the readers in $READERS (default: s42 s43 ftb sch).
"""
import argparse
import os
import subprocess
import sys

import numpy as np
import zarr
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zfetch as zf  # noqa: E402
from fetch_pred import read_box as read_pred  # noqa: E402
from sheet_grow import fill_smooth, grow, run_centres  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('volume'); ap.add_argument('pred'); ap.add_argument('out')
    ap.add_argument('--box', type=int, nargs=6, required=True, help='z0 z1 y0 y1 x0 x1 (L0), depth axis = y')
    ap.add_argument('--seed', type=float, nargs=3, required=True, help='z x depth(y, L0 absolute)')
    ap.add_argument('--layers', type=int, default=28)
    ap.add_argument('--tol', type=float, default=4.0)
    ap.add_argument('--reuse-h', default=None, help='sheet_00_h.npy + sheet_valid.npy dir to reuse instead of tracking')
    ap.add_argument('--shift', type=float, default=0.0, help='render the stack centred at H + shift (depth voxels)')
    a = ap.parse_args()
    z0, z1, y0, y1, x0, x1 = a.box
    os.makedirs(a.out, exist_ok=True)
    ct = zf.read_box(a.volume, 0, (z0, y0, x0), (z1, y1, x1))
    m7 = read_pred(f'{a.pred}/0', (z0, y0, x0), (z1, y1, x1)) > 0
    print('region', ct.shape, 'MB downloaded', round(zf.downloaded() / 1e6), flush=True)
    M = m7.transpose(1, 0, 2); CT = ct.transpose(1, 0, 2)            # (depth, z, x)
    del ct, m7
    D, Z, X = M.shape
    if a.reuse_h:
        H = np.load(os.path.join(a.reuse_h, 'sheet_00_h.npy'))
        V = np.load(os.path.join(a.reuse_h, 'sheet_valid.npy'))
        vals = zz = None
    else:
        s = 4
        C = run_centres(M[:, ::s, ::s], kmax=64)
        zs, xs, ds = a.seed
        cy, cx = int(round((zs - z0) / s)), int(round((xs - x0) / s))
        col = C[:, cy, cx]
        col = col[np.isfinite(col)]
        sd = float(col[np.argmin(np.abs(col - (ds - y0)))])
        print('seed depth', ds - y0, '-> run centre', sd, flush=True)
        Hc = grow(C, (cy, cx), sd, tol=a.tol)
        print('coarse coverage', round(float(np.isfinite(Hc).mean()), 3), flush=True)
        F, validc = fill_smooth(Hc)
        h, w = Hc.shape
        Hf = ndimage.zoom(F, (Z / h, X / w), order=1)[:Z, :X]
        Hf = np.pad(Hf, ((0, Z - Hf.shape[0]), (0, X - Hf.shape[1])), mode='edge')
        V = ndimage.zoom(validc.astype(np.float32), (Z / h, X / w), order=0)[:Z, :X] > 0.5
        V = np.pad(V, ((0, Z - V.shape[0]), (0, X - V.shape[1])), mode='edge')
        ks = np.arange(-3, 4)
        zz = np.clip(np.rint(Hf)[None] + ks[:, None, None], 0, D - 1).astype(int)
        vals = np.take_along_axis(M, zz, 0).astype(np.float32)
        wsum = vals.sum(0)
        off = np.where(wsum > 0, (vals * ks[:, None, None]).sum(0) / np.maximum(wsum, 1), 0)
        H = ndimage.gaussian_filter(np.rint(Hf) + off, 1.5).astype(np.float32)
    del M, vals, zz
    half = a.layers // 2
    kk = np.arange(a.layers) - (a.layers - 1) / 2.0
    stack = np.zeros((a.layers, Z, X), np.uint8)
    for r0 in range(0, Z, 256):
        r1 = min(Z, r0 + 256)
        zg, xg = np.mgrid[r0:r1, 0:X].astype(np.float32)
        for i, k in enumerate(kk):
            stack[i, r0:r1] = np.clip(ndimage.map_coordinates(CT, [H[r0:r1] + a.shift + k, zg, xg], order=1, mode='constant'),
                                      0, 255).astype(np.uint8)
    inside = (V > 0) & (H + a.shift - half >= 0) & (H + a.shift + half < D)
    stack *= inside[None]
    zp = os.path.join(a.out, 'sheet_00.zarr')
    zarr.open_array(zp, mode='w', shape=stack.shape, chunks=(a.layers, 128, 128), dtype='u1', zarr_format=2,
                    compressor=None, fill_value=0)[:] = stack
    np.save(os.path.join(a.out, 'sheet_00_h.npy'), H)
    np.save(os.path.join(a.out, 'sheet_valid.npy'), inside)
    print('rendered', stack.shape, 'valid', round(float(inside.mean()), 3), flush=True)
    subprocess.call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'infer_sheets.py'),
                     a.out, *os.environ.get('READERS', 's42 s43 ftb sch').split()])


if __name__ == '__main__':
    main()
