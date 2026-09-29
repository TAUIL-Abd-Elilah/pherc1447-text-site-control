"""Every number in the README about the sheet through PHerc1447's announced text point.

usage: site_checks.py <announced sheet dir> <deeper sheet dir> <out.json> --box z0 y0 x0 --point z y x
  <announced sheet dir>: bigsheet.py output seeded at the announced point; shifted renders in <dir>_sh<k>.
  <deeper sheet dir>:    bigsheet.py output of the sheet that carries the arch shapes (for the no-merge check).

1. Geometry: depth of the tracked sheet at the announced (z, x) vs the announced y; the largest step of the
   height map along the straight path from the point to each stroke (a jump to a neighbouring sheet would be
   a step of ~14 voxels, the local sheet spacing); separation from the deeper sheet (the two never merge).
2. Which face is inward: the centroid of the scroll cross-section at z (level 4) vs the point.
3. Strokes: components of the forward-face s42 map found by the rule of stroke_null.py (> 0.6, >= 5000 px,
   elongation area / r^2 >= 15, not touching the rim, s43 mean > 0.5, other face mean < 0.2). For each: centre,
   size, elongation, distance to the point, and the contrast (mean on the component - mean on a ring 10-40 px
   around it) for every reader, both faces, at every shifted render.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zfetch as zf  # noqa: E402

VOX_MM = 8.64e-3
READERS = ('s42', 's43', 'ftb', 'sch', 'rv2')


def ink(d, n, rev=False, shape=None):
    p = os.path.join(d, f'mosaic_{n}{"_reverse" if rev else ""}.tif')
    if not os.path.exists(p):
        return None
    t = tifffile.imread(p).astype(np.float32)
    t = t / 255 if t.max() > 1.5 else t
    t = np.clip((t - 0.25) / 0.5, 0, 1)
    return t[:shape[0], :shape[1]] if shape else t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet'); ap.add_argument('deeper'); ap.add_argument('out')
    ap.add_argument('--box', type=int, nargs=3, required=True, help='z0 y0 x0 of the bigsheet box (L0)')
    ap.add_argument('--point', type=int, nargs=3, required=True, help='announced z y x (L0)')
    ap.add_argument('--volume', default='PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr')
    a = ap.parse_args()
    z0, y0, x0 = a.box
    pz, py, px = a.point
    H = np.load(os.path.join(a.sheet, 'sheet_00_h.npy')) + y0
    V = np.load(os.path.join(a.sheet, 'sheet_valid.npy'))
    shape = H.shape
    res = {'point_zyx': a.point, 'box_zyx0': a.box}
    iz, ix = pz - z0, px - x0
    res['sheet_y_at_point'] = round(float(H[iz, ix]), 2)
    res['sheet_minus_announced_y_vox'] = round(float(H[iz, ix] - py), 2)
    Hd = np.load(os.path.join(a.deeper, 'sheet_00_h.npy')) + y0
    Vd = np.load(os.path.join(a.deeper, 'sheet_valid.npy'))
    both = V & Vd
    sep = (Hd - H)[both]
    res['deeper_sheet_separation_vox'] = {'min': round(float(sep.min()), 1), 'median': round(float(np.median(sep)), 1),
                                          'max': round(float(sep.max()), 1), 'at_point': round(float(Hd[iz, ix] - H[iz, ix]), 1)}
    # inward face: centroid of the scroll cross-section at z (level 4)
    L, s = 4, 16
    m = zf.meta(a.volume, L)
    sl = zf.read_box(a.volume, L, (pz // s, 0, 0), (pz // s + 1, m['shape'][1], m['shape'][2]))[0] > 0
    cy, cx = ndimage.center_of_mass(sl)
    res['scroll_centroid_yx_at_z'] = [round(cy * s), round(cx * s)]
    res['forward_face_points_to_centre'] = bool((cy * s - py) * 1 > 0) if abs(cy * s - py) > abs(cx * s - px) else None
    # strokes, by the stroke_null.py rule
    valid = ndimage.binary_erosion(V, iterations=48)
    f42, f43, r42 = ink(a.sheet, 's42', False, shape), ink(a.sheet, 's43', False, shape), ink(a.sheet, 's42', True, shape)
    lab, n = ndimage.label((f42 * valid) > 0.6)
    shifts = sorted([(int(p.rsplit('_sh', 1)[1]), p) for p in glob.glob(a.sheet + '_sh*')] + [(0, a.sheet)])
    strokes = []
    for i, sl_ in enumerate(ndimage.find_objects(lab), 1):
        c = lab == i
        A = int(c.sum())
        if A < 5000:
            continue
        r = float(ndimage.distance_transform_edt(c[sl_]).max())
        e = A / r ** 2
        edge = bool((ndimage.binary_dilation(c, iterations=3) & ~valid).any())
        if e < 15 or edge or f43[c].mean() <= 0.5 or r42[c].mean() >= 0.2:
            continue
        ys, xs = np.where(c)
        ccz, ccx = float(ys.mean()), float(xs.mean())
        ring = ndimage.binary_dilation(c, iterations=40) & ~ndimage.binary_dilation(c, iterations=10) & valid
        con = {}
        for k, d in shifts:
            for n_ in READERS:
                for rev in (False, True):
                    t = ink(d, n_, rev, shape)
                    if t is not None:
                        con[f'{n_}_{"reverse" if rev else "forward"}_shift{k:+d}'] = round(float(t[c].mean() - t[ring].mean()), 3)
        dist = np.sqrt((ccz - iz) ** 2 + (ccx - ix) ** 2 + (H[int(ccz), int(ccx)] - H[iz, ix]) ** 2)
        strokes.append({'centre_zyx': [round(ccz + z0), round(float(H[int(ccz), int(ccx)]), 1), round(ccx + x0)],
                        'extent_mm_z_x': [round((np.ptp(ys) + 1) * VOX_MM, 2), round((np.ptp(xs) + 1) * VOX_MM, 2)],
                        'area_px': A, 'half_width_um': round(r * VOX_MM * 1000), 'elongation': round(e, 1),
                        's43_mean': round(float(f43[c].mean()), 2), 'reverse_face_s42_mean': round(float(r42[c].mean()), 2),
                        'distance_to_point_mm': round(float(dist) * VOX_MM, 2), 'contrast': con})
        # continuity of the height map along the straight path point -> stroke
        nn = 400
        zz = np.linspace(iz, ccz, nn).round().astype(int); xx = np.linspace(ix, ccx, nn).round().astype(int)
        h = H[zz, xx]
        strokes[-1]['path_max_step_vox'] = round(float(np.abs(np.diff(h)).max()), 2)
        strokes[-1]['path_sample_spacing_vox'] = round(float(np.hypot(ccz - iz, ccx - ix) / nn), 2)
    res['strokes'] = strokes
    res['sheet_area_cm2_rim_excluded'] = round(float(valid.sum()) * VOX_MM ** 2 / 100, 2)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'strokes'}, indent=1))
    for s_ in strokes:
        print({k: v for k, v in s_.items() if k != 'contrast'})
        for n_ in READERS:
            for face in ('forward', 'reverse'):
                row = [s_['contrast'].get(f'{n_}_{face}_shift{k:+d}') for k, _ in shifts]
                print(f'  {n_} {face}: ' + '  '.join(f'{k:+d}: {v:+.2f}' if v is not None else f'{k:+d}: -' for (k, _), v in zip(shifts, row)))


if __name__ == '__main__':
    main()
