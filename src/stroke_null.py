"""False-positive rate of stroke-shaped components: every rendered sheet of every scanned block, both faces,
released ink_9um s42 (rescaled (p-0.25)/0.5), threshold 0.6, 48 px rim excluded; flags whether a
component touches the rim/invalid area and the mean s42 on the OTHER face over it (real ink is one-sided). Component elongation =
area / r^2 (r = largest inscribed radius; the formula of villa#1907; a disc is 3.14). Reports components with
area >= AMIN px and elongation >= 15 / 20, the area screened, and whether s43 agrees (mean > 0.5 on the component)."""
import glob, json, os, sys
import numpy as np, tifffile, zarr
from scipy import ndimage
AMIN = 5000
out = []
area_cm2 = 0.0
dirs = sys.argv[1:]
for b in dirs:
    zps = sorted(glob.glob(os.path.join(b, 'sheet_*.zarr')))
    if not zps or not os.path.exists(os.path.join(b, 'mosaic_s42.tif')):
        continue
    arrs = [zarr.open_array(z, mode='r') for z in zps]
    sj = os.path.join(b, 'sheets.json')          # blockscan.py blocks record their volume; bigsheet dirs are 8.64 um
    vox_mm = 9.362e-3 if os.path.exists(sj) and '9.362um' in json.load(open(sj))['volume'] else 8.64e-3
    xs = np.cumsum([0] + [a.shape[2] + 64 for a in arrs])
    M2 = {}
    for rev, oth in (('', '_reverse'), ('_reverse', '')):
        t = tifffile.imread(os.path.join(b, f'mosaic_s42{oth}.tif')).astype(np.float32); t = t / 255 if t.max() > 1.5 else t
        M2[rev] = np.clip((t - 0.25) / 0.5, 0, 1)
    for rev in ('', '_reverse'):
        M = {}
        for n in ('s42', 's43'):
            t = tifffile.imread(os.path.join(b, f'mosaic_{n}{rev}.tif')).astype(np.float32); t = t / 255 if t.max() > 1.5 else t
            M[n] = np.clip((t - 0.25) / 0.5, 0, 1)
        for zp, a, x0 in zip(zps, arrs, xs[:-1]):
            ct = np.asarray(a[13:15]).astype(np.float32).mean(0)
            valid = ndimage.binary_erosion(ct > 0, iterations=48)
            if rev == '':
                area_cm2 += float(valid.sum()) * vox_mm ** 2 / 100
            m = M['s42'][:a.shape[1], int(x0):int(x0) + a.shape[2]] * valid
            m43 = M['s43'][:a.shape[1], int(x0):int(x0) + a.shape[2]]
            lab, n = ndimage.label(m > 0.6)
            if n == 0:
                continue
            objs = ndimage.find_objects(lab)
            for i, sl in enumerate(objs, 1):
                c = lab[sl] == i
                A = int(c.sum())
                if A < AMIN:
                    continue
                r = float(ndimage.distance_transform_edt(np.pad(c, 1))[1:-1, 1:-1].max())
                e = A / r ** 2
                if e < 15:
                    continue
                full = np.zeros(lab.shape, bool); full[sl] = c
                edge = bool((ndimage.binary_dilation(full, iterations=3) & ~valid).any())
                other = M2[rev][:a.shape[1], int(x0):int(x0) + a.shape[2]]
                out.append({'block': os.path.basename(b), 'sheet': os.path.basename(zp), 'face': 'rev' if rev else 'fwd',
                            'area_px': A, 'elong': round(e, 1), 'z': int(sl[0].start), 'x': int(sl[1].start),
                            's43_mean': round(float(m43[sl][c].mean()), 2), 'touches_edge': edge,
                            'other_face_mean': round(float(other[full].mean()), 2)})
cm2 = area_cm2
print(f'screened {cm2:.1f} cm2 (valid, rim-excluded, per face), {len(out)} components with area>={AMIN} px and elongation>=15')
for thr in (15, 20):
    s = [o for o in out if o['elong'] >= thr]
    s2 = [o for o in s if o['s43_mean'] > 0.5 and not o['touches_edge']]
    s3 = [o for o in s2 if o['other_face_mean'] < 0.2]
    print(f'  elong>={thr}: {len(s)}; + s43 agrees (>0.5) + not touching the rim: {len(s2)}; + other face quiet (<0.2): {len(s3)} '
          f'({len(s3)/max(cm2,1e-9):.3f} per cm2)')
json.dump({'cm2': cm2, 'components': out}, open(os.environ.get('OUT_JSON', 'stroke_null.json'), 'w'), indent=1)
