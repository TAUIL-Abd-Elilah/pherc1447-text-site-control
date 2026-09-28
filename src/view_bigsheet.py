"""View a bigsheet.py sheet: CT | each model fwd | each model reverse, half resolution, with a marked point;
plus the forward s42 map at every shifted render (<dir>_sh<k>) around the point.
usage: view_bigsheet.py <sheet dir> <out prefix> --box z0 x0 --point z x [--models s42 s43 ftb]"""
import argparse, glob, os
import numpy as np, tifffile, zarr
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('d'); ap.add_argument('out')
ap.add_argument('--box', type=int, nargs=2, required=True, help='z0 x0 of the bigsheet box (L0)')
ap.add_argument('--point', type=int, nargs=2, required=True, help='z x (L0) to mark')
ap.add_argument('--models', nargs='+', default=['s42', 's43', 'ftb'])
a = ap.parse_args()
pz, px = a.point[0] - a.box[0], a.point[1] - a.box[1]


def ink(d, n, rev=False):
    p = os.path.join(d, f'mosaic_{n}{"_reverse" if rev else ""}.tif')
    if not os.path.exists(p):
        return None
    t = tifffile.imread(p).astype(np.float32); t = t / 255 if t.max() > 1.5 else t
    return np.clip((t - 0.25) / 0.5, 0, 1)


def ct_of(d):
    s = zarr.open_array(os.path.join(d, 'sheet_00.zarr'), mode='r')
    c = np.asarray(s[13:15]).astype(np.float32).mean(0); v = c > 0
    lo, hi = np.percentile(c[v], [1, 99])
    return np.clip((c - lo) / (hi - lo + 1e-6), 0, 1) * v, v


def canvas(tiles, labels, ncol, scale, mark):
    tiles = [t[::scale, ::scale] for t in tiles]
    h, w = tiles[0].shape
    nrow = -(-len(tiles) // ncol)
    cv = Image.new('L', (ncol * (w + 6), nrow * (h + 16)), 255); dr = ImageDraw.Draw(cv)
    for i, (t, lab) in enumerate(zip(tiles, labels)):
        x, y = (i % ncol) * (w + 6), (i // ncol) * (h + 16)
        dr.text((x + 2, y + 2), lab, fill=0)
        cv.paste(Image.fromarray((t * 255).astype(np.uint8)), (x, y + 14))
        if mark:
            mx, my = x + mark[1] // scale, y + 14 + mark[0] // scale
            dr.ellipse((mx - 8, my - 8, mx + 8, my + 8), outline=128, width=2)
    return cv


ct, v = ct_of(a.d)
H, W = ct.shape
tiles, labs = [ct], ['CT (centre layers)']
for rev in (False, True):
    for n in a.models:
        m = ink(a.d, n, rev)
        if m is not None:
            tiles.append(m[:H, :W] * v); labs.append(f'{n} {"reverse" if rev else "forward"} face')
canvas(tiles, labs, 2, 2, (pz, px)).save(a.out + '_sheet.png')
# shift series around the point (+-6 mm window)
r = 700
ys, xs = slice(max(0, pz - r // 2), pz + r // 2), slice(max(0, px - r), px + r)
tiles, labs = [ct[ys, xs]], ['CT shift 0']
shifts = sorted([(int(p.rsplit('_sh', 1)[1]), p) for p in glob.glob(a.d + '_sh*')] + [(0, a.d)])
for k, p in shifts:
    for rev in (False, True):
        m = ink(p, 's42', rev)
        if m is not None:
            vv = ct_of(p)[1]
            tiles.append((m[:H, :W] * vv)[ys, xs]); labs.append(f's42 {"rev" if rev else "fwd"} shift {k:+d} vox')
canvas(tiles, labs, 2, 1, (pz - ys.start, px - xs.start)).save(a.out + '_shifts.png')
print('wrote', a.out + '_sheet.png', a.out + '_shifts.png')
