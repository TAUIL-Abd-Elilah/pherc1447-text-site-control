# pherc1447-text-site-control

Does the released `ink_9um` draw strokes on the eligible 1.2 m scan type? PHerc1447's public volume is an
8.64 µm / 1.2 m / 116 keV scan, the configuration of PHerc0800 and other First Letters volumes. The organisers
found text in it with a new recipe; their 24 Sep announcement places it at x 4144, y 2742, z 12557. This
repository tracks the papyrus sheet that passes through that point and runs four public 9 µm readers on it.

**Result.** On that sheet, the released `ink_9um` (both seeds) draws **one stroke-shaped mark, 4.8 mm from the
announced point**: a U-shaped stroke 3.1 x 1.4 mm with a dot beside it (figures 1, 2).
- **Inward face only.** It is there on the face towards the scroll centre, where papyrus is written, and not on the other face.
- **Depth-localised.** It is present with the render moved anywhere from 35 µm outward to 69 µm inward, and gone at 69 µm outward.
- **Seen by all four readers.** Both released seeds, our native-9 µm fine-tune and Chris Scheirer's fine-tune draw it, each only on the inward face.
- **Rare elsewhere.** By one fixed rule (below) it is the only such mark in the 1.9 cm² of the sheet. The same rule finds **none in 119.7 cm²** of sheet-following renders of all 22 First Letters scrolls.

**What it is not.** The rest of the sheet reads as blobs. There is no legible text, and we have not matched
the mark to the organisers' reading. The rule was written after seeing this mark, so the comparison is
exploratory.

**Why it may be useful.** [villa#1907](https://github.com/ScrollPrize/villa/issues/1907) asks for a positive
control on the eligible 1.2 m scan type, and notes that nobody has a measured reason to trust what `ink_9um`
shows there. This is a partial one: at a place where text is known, on a sheet-following surface, the
public reader draws a stroke-shaped, one-sided, depth-localised mark of a kind that the rule below finds nowhere
in 120 cm² of the eligible scrolls. It shows detection of a stroke, not readability. `src/bigsheet.py` tracks and renders
any sheet from a seed point, so anyone can repeat this at another point in about 15 minutes of GPU time.

![announced sheet](figures/01_announced_sheet.png)
*Figure 1. The sheet through the announced point (red circle), 10.4 x 24.2 mm. Top: CT; bottom: released
ink_9um seed 42, inward face. Blue box: the stroke.*

![stroke across depth and faces](figures/02_stroke_depth_and_face.png)
*Figure 2. The stroke, for each reader (rows), with the render moved along depth (columns; 1 voxel = 8.64 µm;
+ = towards the scroll centre) and on the other face (last column). The number in each panel is the contrast:
mean prediction on the stroke minus a ring 10-40 px around it.*

## Numbers (`results/announced_sheet_checks.json`)

| reader | inward face, depth shift (voxels) -8 / -4 / 0 / +4 / +8 | other face, 0 |
|---|---|---|
| ink_9um seed 42 (released) | +0.04 / +0.53 / **+0.81** / +0.78 / +0.63 | +0.02 |
| ink_9um seed 43 (released) | +0.01 / +0.60 / **+0.80** / +0.81 / +0.58 | +0.02 |
| ft_b (native 9.362 µm fine-tune, [cross-scan-ink-transfer](https://github.com/TAUIL-Abd-Elilah/cross-scan-ink-transfer)) | +0.04 / +0.32 / **+0.47** / +0.46 / +0.37 | -0.00 |
| Scheirer ft_s42 ([reader-ft-s42](https://github.com/ShribyrLabs/vesuvius-reports/releases/tag/reader-ft-s42)) | +0.12 / +0.44 / **+0.54** / +0.54 / +0.47 | +0.04 |

- **Where:** stroke centre at z 12815, y 2857, x 4628, 4.84 mm from the announced point in a straight line.
- **Size:** 3.08 x 1.37 mm (x by z), 20,369 px.
- **Shape:** stroke half-width 276 µm. Elongation (area / r², r = largest inscribed radius, the formula of #1907) is 20.0. A disc is 3.14; #1907 reports 16-25 for its human tracings and 10.6-15.3 for `ink_9um` maps on PHerc0841, with its own thresholding, so the comparison is approximate.

**The surface is the sheet through the announced point, and stays on it:**
- **At the point:** the tracked sheet's depth is y 2741.85 against the announced 2742 (-0.15 voxels). Neighbouring sheets here are about 14 voxels apart.
- **No jump:** along the straight path from the point to the stroke, the height map never steps more than 0.98 voxels between samples 1.37 voxels apart. A jump to the next sheet would be a step of about 14.
- **Never merges** with the deeper sheet of figure 3: the two stay 17-297 voxels apart (median 105).
- **Forward face points inward:** the centroid of the scroll cross-section at z 12557 is at y 3457, x 3915, so the +y face points to the scroll centre.

**The rule** (`src/stroke_null.py`): threshold the seed-42 map at 0.6, then keep components that pass all of these:
- area at least 5,000 px;
- elongation at least 15;
- not touching the rim of the valid surface;
- seed 43 agrees (its mean over the component is above 0.5);
- the other face is quiet (seed-42 mean over the component on the other face is below 0.2).

The null is 66 blocks (33 at 8.64 µm, 33 at 9.362 µm) on all 22 First Letters scrolls, rendered with the same tracker (`src/blockscan.py`), 119.7 cm² per face after removing a 48 px rim:
- 19 components pass area and elongation, 3 of them with elongation of 20 or more;
- none passes the full rule, and none of the 19 has seed 43 agreeing while clear of the rim.

Summary: `results/stroke_null_survey_summary.json`; block list: `runs/survey_blocks.txt`; rerun: `runs/04_null_survey.sh`. One mark passes in total. If the rule fired at the same rate everywhere, the chance that it would land in the 3.2 cm² rendered at the text site (this sheet plus the deeper one) is 3.2 / 122.9 = 2.6 %.

## A deeper sheet: arch shapes, unconfirmed

![deeper sheet](figures/03_deeper_sheet.png)
*Figure 3. A sheet about 100 voxels (0.8 mm) deeper, over the same box; the red circle marks the announced (z, x).
The released readers draw two arch shapes below and to the right of it.*

We found these arches first and at first took them for the announced text; they are not on the announced sheet.
Both are on the inward face only (other-face contrast 0.03 or less) and all four readers draw them, but they are
compact (elongation 10.3 and 6.8), their depth profiles differ (one still +0.40 at -8 voxels, the other +0.41 at
+8), and other blobs on this sheet are one-sided too. They do not pass the rule above, and nothing is known to be
written on that sheet, so they are reported, not claimed.

## Reproduce

Needs a CUDA GPU (~6 GB) and about 2.4 GB of CT chunks plus the m7 surface prediction for the box. Steps 1-3
took 12 minutes on an RTX 3090 with the data cached.
The code needs:
- a [ScrollPrize/villa](https://github.com/ScrollPrize/villa) checkout for `vesuvius.ink_detection.inference.infer` (tested at `5479453a7`; `main` at `f4570bfa6` has the same flags);
- the checkpoints listed in `runs/env.sh`.

```bash
source runs/env.sh                 # set VILLA_SRC, INK9UM_CKPTS, FTB_CKPT, SCH_CKPT, CT_CACHE, OUT
bash runs/01_announced_sheet.sh    # track the sheet through (z 12557, x 4144, y 2742), render, 4 readers, 4 depth shifts
bash runs/02_deeper_sheet.sh       # the deeper sheet (figure 3)
bash runs/03_checks_and_figures.sh # results/*.json and figures/
bash runs/04_null_survey.sh        # the 66-block comparison set (~30 GB of CT, several GPU hours)
```

A from-scratch run of steps 1-3 reproduced the height maps, all four readers' maps, the numbers and the
figures bit for bit; so did one block of step 4 (PHerc0358, 9 sheets).

**The code (`src/`):**
- `sheet_grow.py`: best-first growth of one sheet over the run centres of the organisers' m7 surface-prediction mask, snapped to full resolution.
- `bigsheet.py`: one sheet from a seed point over a box, rendered as a 28-layer stack along the depth axis; `--shift` moves the stack along depth.
- `blockscan.py`: every sheet in a block.
- `infer_sheets.py`: runs the readers through villa's inference CLI, both faces.
- `site_checks.py`: every number above.
- `stroke_null.py`: the rule, on any set of renders.
- `figures.py`, `view_bigsheet.py`.
- `zfetch.py` and `fetch_pred.py`: cached reads of the public zarrs.

**Credits:**
- `ink_9um` and the m7 surface predictions: Vesuvius Challenge (huggingface.co/scrollprize/ink_9um).
- The `reader-ft-s42` fine-tune: Chris Scheirer (MIT).
- The elongation formula: villa#1907.

MIT licence. Data: Vesuvius Challenge, CC BY-NC 4.0.
Developed with AI assistance under my direction.
