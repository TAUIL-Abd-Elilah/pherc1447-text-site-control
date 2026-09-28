#!/usr/bin/env bash
# The comparison set: the 66 survey blocks of runs/survey_blocks.txt (22 First Letters scrolls), every sheet tracked
# and rendered by blockscan.py, readers s42 + s43 (all the rule needs), then the stroke rule.
# ~30 GB of CT chunks and several GPU hours.
set -e; source runs/env.sh
grep -v '^#' runs/survey_blocks.txt | while read vol pred z y x ax; do
  python src/blockscan.py $vol $pred $OUT/survey --centre $z $y $x --axis $ax < /dev/null
  python src/infer_sheets.py $OUT/survey/b_z${z}_y${y}_x${x}_${ax} s42 s43 < /dev/null
done
OUT_JSON=results/stroke_null_survey.json python src/stroke_null.py $OUT/survey/b_*
