#!/usr/bin/env bash
# The sheet through the announced text point (x 4144, y 2742, z 12557): track it over the box from that seed,
# render 28 layers, run the readers; then the same height map shifted by -8, -4, +4, +8 voxels along depth.
set -e; source runs/env.sh
python src/bigsheet.py $VOL $PRED $OUT/announced --box $BOX --seed 12557 4144 2742
for sh in -8 -4 4 8; do
  python src/bigsheet.py $VOL $PRED $OUT/announced_sh$sh --box $BOX --seed 12557 4144 2742 --reuse-h $OUT/announced --shift $sh
done
