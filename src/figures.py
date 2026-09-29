"""README figures from the bigsheet.py outputs and results/announced_sheet_checks.json.
usage: figures.py <announced sheet dir> <deeper sheet dir> <checks.json> <figures dir>"""
import json
import os
import sys

import numpy as np
import tifffile
import zarr
from PIL import Image, ImageDraw

VOX_MM = 8.64e-3


def ink(d, n, rev=False):
    p = os.path.join(d, f'mosaic_{n}{"_reverse" if rev else ""}.tif')
    t = tifffile.imread(p).astype(np.float32)
    t = t / 255 if t.max() > 1.5 else t
    return np.clip((t - 0.25) / 0.5, 0, 1)


def ct(d):
    s = zarr.open_array(os.path.join(d, 'sheet_00.zarr'), mode='r')
    c = np.asarray(s[13:15]).astype(np.float32).mean(0)
    v = c > 0
    lo, hi = np.percentile(c[v], [1, 99])
    return np.clip((c - lo) / (hi - lo + 1e-6), 0, 1) * v, v


def img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGB')


def scalebar(dr, x, y, px_per_mm, mm=5, colour=(255, 200, 0)):
    dr.rectangle((x, y, x + px_per_mm * mm, y + 5), fill=colour)
    dr.text((x, y + 8), f'{mm} mm', fill=colour)


def overview(d, title, out, mark_point=None, boxes=(), ds=2):
    c, v = ct(d)
    H, W = c.shape
    m = ink(d, 's42')[:H, :W] * v
    tiles = [(c, 'CT, centre layers of the 28-layer render'), (m, 'released ink_9um seed 42, forward (inward) face')]
    w, h = W // ds, H // ds
    cv = Image.new('RGB', (w, 2 * (h + 18) + 18), (255, 255, 255))
    dr = ImageDraw.Draw(cv)
    dr.text((4, 2), title, fill=(0, 0, 0))
    for i, (t, lab) in enumerate(tiles):
        y = 18 + i * (h + 18)
        dr.text((4, y + 2), lab, fill=(0, 0, 0))
        cv.paste(img(t[::ds, ::ds]), (0, y + 16))
        if mark_point:
            pz, px = mark_point[0] // ds, mark_point[1] // ds
            dr.ellipse((px - 10, y + 16 + pz - 10, px + 10, y + 16 + pz + 10), outline=(255, 60, 60), width=3)
        for (z0, x0, z1, x1) in boxes:
            dr.rectangle((x0 // ds, y + 16 + z0 // ds, x1 // ds, y + 16 + z1 // ds), outline=(80, 200, 255), width=3)
        scalebar(dr, 12, y + 16 + h - 24, 1 / VOX_MM / ds)
    cv.save(out)


def main():
    sheet, deeper, checks, fig = sys.argv[1:5]
    os.makedirs(fig, exist_ok=True)
    r = json.load(open(checks))
    z0, y0, x0 = r['box_zyx0']
    pz, px = r['point_zyx'][0] - z0, r['point_zyx'][2] - x0
    st = r['strokes'][0]
    cz, cx = st['centre_zyx'][0] - z0, st['centre_zyx'][2] - x0
    hz, hx = 330, 420
    overview(sheet, f'PHerc1447, the sheet through the announced text point (red circle); stroke (blue box). '
             f'z {z0}-{z0 + 1200}, x {x0}-{x0 + 2800}', os.path.join(fig, '01_announced_sheet.png'),
             (pz, px), [(cz - hz // 2, cx - hx // 2, cz + hz // 2, cx + hx // 2)])
    # stroke: readers x shifts, both faces
    c, v = ct(sheet)
    Hs, Ws = c.shape
    win = (slice(max(0, cz - hz), cz + hz), slice(max(0, cx - hx), cx + hx))
    shifts = [-12, -8, -4, 0, 4, 8, 12]
    cols = [(k, False) for k in shifts] + [(0, True)]
    ds = 2
    th, tw = (win[0].stop - win[0].start) // ds, (win[1].stop - win[1].start) // ds
    readers = [('s42', 'ink_9um s42'), ('s43', 'ink_9um s43'), ('ftb', 'ft_b (ours)'), ('sch', 'Scheirer ft_s42'),
               ('rv2', 'Reader v2 (KLAVIS)')]
    cv = Image.new('RGB', ((len(cols) + 1) * (tw + 6), (len(readers)) * (th + 18) + 34), (255, 255, 255))
    dr = ImageDraw.Draw(cv)
    dr.text((4, 2), f"Stroke at z {st['centre_zyx'][0]}, y {st['centre_zyx'][1]:.0f}, x {st['centre_zyx'][2]}: "
                    f"{st['extent_mm_z_x'][1]} x {st['extent_mm_z_x'][0]} mm, {st['distance_to_point_mm']} mm from the "
                    f"announced point. Columns: render shifted along depth (1 voxel = 8.64 um; neighbouring sheets ~14 voxels away), forward = inward face.",
            fill=(0, 0, 0))
    for j, (k, rev) in enumerate(cols):
        dr.text(((j + 1) * (tw + 6) + 4, 18), f'{"reverse" if rev else "forward"} {k:+d} vox', fill=(0, 0, 0))
    for i, (n, lab) in enumerate(readers):
        y = 34 + i * (th + 18)
        if i == 0:
            cv.paste(img(c[win][::ds, ::ds]), (0, y + 14))
            dr.text((4, y), 'CT', fill=(0, 0, 0))
        else:
            dr.text((4, y + th // 2), lab, fill=(0, 0, 0))
        for j, (k, rev) in enumerate(cols):
            d = sheet if k == 0 else f'{sheet}_sh{k}'
            m = ink(d, n, rev)[:Hs, :Ws]
            vv = ct(d)[1]
            cv.paste(img((m * vv)[win][::ds, ::ds]), ((j + 1) * (tw + 6), y + 14))
            if j == 0:
                dr.text(((j + 1) * (tw + 6) + 4, y + 16), lab, fill=(255, 200, 0))
            key = f'{n}_{"reverse" if rev else "forward"}_shift{k:+d}'
            dr.text(((j + 1) * (tw + 6) + 4, y + th), f"contrast {st['contrast'][key]:+.2f}", fill=(255, 200, 0))
    cv.save(os.path.join(fig, '02_stroke_depth_and_face.png'))
    overview(deeper, 'PHerc1447, a sheet ~100 voxels (0.8 mm) deeper than the announced one (red circle: the announced z, x): arch shapes, unconfirmed',
             os.path.join(fig, '03_deeper_sheet.png'), (pz, px))
    print('figures ->', fig)


if __name__ == '__main__':
    main()
