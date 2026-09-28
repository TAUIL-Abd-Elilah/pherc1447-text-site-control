#!/usr/bin/env bash
# A sheet ~100 voxels (0.8 mm) deeper, seeded where the arch shapes are (used for figure 3 and the no-merge check).
set -e; source runs/env.sh
python src/bigsheet.py $VOL $PRED $OUT/deeper --box $BOX --seed 12700 3900 2779.5
