"""Ink inference + contact sheet for every sheet_XX.zarr in a directory (a block from blockscan.py or one
sheet from bigsheet.py). All sheets are tiled into one mosaic zarr so each reader loads once; villa's
inference CLI runs both depth directions (forward = +depth axis, reverse); outputs are rescaled with
(p - 0.25) / 0.5 (ink_9um's label smoothing puts "no ink" at 0.25). Writes <dir>/ink_scores.json (per sheet and
reader: fraction > 0.5 and best 2 mm window, 48 px rim excluded), mosaic_<reader>[_reverse].tif, ink_sheet.png.
usage: infer_sheets.py <dir> [s42 s43 ftb sch rv2]"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
import tifffile
import zarr
from PIL import Image, ImageDraw
from scipy import ndimage

PY = sys.executable
# villa's ink_9um inference CLI (ScrollPrize/villa, vesuvius/src on the path) and the four readers
ENV = dict(os.environ, PYTHONPATH=os.environ.get('VILLA_SRC', 'villa/vesuvius/src'))
C = os.environ.get('INK9UM_CKPTS', 'models/ink_9um')
MODELS = {'s42': f'{C}/hybrid_3d2d-seed42/step-075000.pth',          # huggingface.co/scrollprize/ink_9um
          's43': f'{C}/hybrid_3d2d-seed43/step-075000.pth',
          'ftb': os.environ.get('FTB_CKPT', 'models/ink9um_native0139_ft6k.pth'),       # our native-9 um fine-tune
          'sch': os.environ.get('SCH_CKPT', 'models/ink9um_ft_s42_step12000.pth'),      # Chris Scheirer's fine-tune
          'rv2': os.environ.get('RV2_CKPT', 'models/reader-v2-step040000.pth')}         # KLAVIS Reader v2


def run(zp, name, ck):
    out = zp.replace('.zarr', f'_{name}.tif')
    if not os.path.exists(out):
        subprocess.call([PY, '-m', 'vesuvius.ink_detection.inference.infer', zp, ck, out, '--overlap', '0.5',
                         '--blend-mode', 'hann', '--batch-size', '8', '--direction', 'both', '--no-compile'],
                        env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    maps = []
    for p in (out, out.replace('.tif', '_reverse.tif')):
        if os.path.exists(p):
            a = tifffile.imread(p).astype(np.float32)
            a = a / 255 if a.max() > 1.5 else a
            maps.append(np.clip((a - 0.25) / 0.5, 0, 1))
    return np.max(maps, 0) if maps else None


def stats(m, valid, px_mm=8.64e-3, rim=48):
    # ignore a rim at the mesh edge (next to air / invalid) where every model fires on the boundary
    valid = ndimage.binary_erosion(valid, iterations=rim) if valid.any() else valid
    b = ((m > 0.5) & valid).astype(np.float32)
    w = max(3, int(round(2.0 / px_mm)))
    loc = ndimage.uniform_filter(b, w) if min(b.shape) > w else b
    return {'frac': round(float(b[valid].mean()) if valid.any() else 0, 4), 'best_2mm': round(float(loc.max()), 3)}


def main(block, models=None):
    """All sheets of the block are tiled side by side into one mosaic zarr (64 px gaps), so each model
    loads once per block; outputs are cut back into sheets."""
    models = {k: MODELS[k] for k in (models or MODELS)}
    zps = sorted(glob.glob(os.path.join(block, 'sheet_*.zarr')))
    arrs = [zarr.open_array(zp, mode='r') for zp in zps]
    L, H = arrs[0].shape[0], arrs[0].shape[1]
    gap = 64
    xs = np.cumsum([0] + [a.shape[2] + gap for a in arrs])
    mz = os.path.join(block, 'mosaic.zarr')
    if not os.path.exists(os.path.join(mz, '.zarray')):
        mos = zarr.open_array(mz, mode='w', shape=(L, H, int(xs[-1])), chunks=(L, 128, 128), dtype='u1',
                              zarr_format=2, compressor=None, fill_value=0)
        for a, x0 in zip(arrs, xs[:-1]):
            mos[:, :, int(x0):int(x0) + a.shape[2]] = a[:]
    maps = {n: run(mz, n, ck) for n, ck in models.items()}
    res = {}
    rows = []
    for zp, a, x0 in zip(zps, arrs, xs[:-1]):
        ct = np.asarray(a[13:15]).astype(np.float32).mean(0)
        valid = ct > 0
        lo, hi = np.percentile(ct[valid], [1, 99]) if valid.any() else (0, 1)
        row = [np.clip((ct - lo) / (hi - lo + 1e-6), 0, 1)]
        r = {}
        for n, M in maps.items():
            if M is None:
                continue
            m = M[:H, int(x0):int(x0) + a.shape[2]] * valid
            r[n] = stats(m, valid)
            row.append(m)
        res[os.path.basename(zp)] = r
        rows.append((os.path.basename(zp), row))
        print(os.path.basename(zp), r, flush=True)
    json.dump(res, open(os.path.join(block, 'ink_scores.json'), 'w'), indent=1)
    ds = 2
    H, W = rows[0][1][0].shape[0] // ds, rows[0][1][0].shape[1] // ds
    k = len(rows[0][1])
    cv = Image.new('L', (k * (W + 6), len(rows) * (H + 14) + 14), 255)
    d = ImageDraw.Draw(cv)
    for j, lab in enumerate(['CT', *models]):
        d.text((j * (W + 6) + 2, 1), lab, fill=0)
    for i, (n, row) in enumerate(rows):
        for j, a in enumerate(row):
            h, w = a.shape[0] // ds, a.shape[1] // ds
            im = Image.fromarray((a[:h * ds, :w * ds].reshape(h, ds, w, ds).mean((1, 3)) * 255).astype(np.uint8))
            cv.paste(im, (j * (W + 6), 14 + i * (H + 14)))
        d.text((2, 14 + i * (H + 14) + H + 1), n, fill=0)
    cv.save(os.path.join(block, 'ink_sheet.png'))
    print('sheet png', cv.size)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or None)
