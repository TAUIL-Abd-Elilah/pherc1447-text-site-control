# Edit these, then: source runs/env.sh   (run everything from the repository root)
export CT_CACHE=${CT_CACHE:-cache}                    # CT + m7 chunk cache (~2.5 GB for this site)
export OUT=${OUT:-out}                                # renders and reader outputs
export VILLA_SRC=${VILLA_SRC:-villa/vesuvius/src}     # ScrollPrize/villa checkout (tested at 5479453a7; main f4570bfa6 has the same CLI)
export INK9UM_CKPTS=${INK9UM_CKPTS:-models/ink_9um}   # huggingface.co/scrollprize/ink_9um: hybrid_3d2d-seed42/43/step-075000.pth
export FTB_CKPT=${FTB_CKPT:-models/ink9um_native0139_ft6k.pth}
#   https://github.com/TAUIL-Abd-Elilah/cross-scan-ink-transfer/releases/download/v1.0/ink9um_native0139_ft6k.pth
export SCH_CKPT=${SCH_CKPT:-models/ink9um_ft_s42_step12000.pth}
#   https://github.com/ShribyrLabs/vesuvius-reports/releases/download/reader-ft-s42/ink9um_ft_s42_step12000.pth
export RV2_CKPT=${RV2_CKPT:-models/reader-v2-step040000.pth}
#   huggingface.co/domenicor046/reader-v2 (MIT), sha256 654ec5acec2b6c4788d9cb326e2f0b8c2c730584949a934ef775db7f6ab5d3a6
export READERS=${READERS:-"s42 s43 ftb sch rv2"}
export VOL=PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr
export PRED=PHerc1447/representations/predictions/surfaces/20250521151220-surface-20260413222639-surface-m7-L0-th0.2.zarr
export BOX="12100 13300 2510 2974 2400 5200"          # z0 z1 y0 y1 x0 x1 (L0): 10.4 x 24.2 mm around the text point
