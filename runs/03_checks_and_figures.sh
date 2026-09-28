#!/usr/bin/env bash
# All README numbers (results/announced_sheet_checks.json), the stroke count on the two 1447 sheets, and figures.
set -e; source runs/env.sh
python src/site_checks.py $OUT/announced $OUT/deeper results/announced_sheet_checks.json --box 12100 2510 2400 --point 12557 2742 4144
OUT_JSON=results/stroke_null_1447.json python src/stroke_null.py $OUT/announced $OUT/deeper
python src/figures.py $OUT/announced $OUT/deeper results/announced_sheet_checks.json figures
