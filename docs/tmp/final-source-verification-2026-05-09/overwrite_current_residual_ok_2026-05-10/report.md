# Current Residual BBox Source Overwrite Report

## Problem

After final source verification, `639` current residual object assets still had bbox evidence and were rerendered. The rerender recovered `616` assets to four-view `ok`; `23` assets remained non-ok and were excluded.

## Investigation

Overwrite scope was locked by exact set checks:

- Recommended residual assets: `639`
- Quality analysis assets: `639`
- Selected `new_class=ok` and `view_classes=ok;ok;ok;ok`: `616`
- Rejected residual assets: `23`
- Rejected residual counts: `{('cabinet', 'suspicious'): 16, ('door', 'suspicious'): 5, ('pen', 'suspicious'): 1, ('cabinet', 'blank'): 1}`
- Overlap with previous overwrite manifests: `0`

Dry-run validation before mutation:

- Selected assets: `616`
- PNG pairs checked: `2464`
- Source PNGs present and non-empty: `2464`
- Rerender PNGs present and non-empty: `2464`
- Already-identical PNG pairs before overwrite: `0`
- Planned overwrite PNG pairs: `2464`
- Source asset classes before overwrite: `{'suspicious': 533, 'tiny': 58, 'blank': 25}`
- Validation errors: `0`

## Solution

Original source PNGs were backed up under:

`/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/final-source-verification-2026-05-09/overwrite_current_residual_ok_2026-05-10/source_png_backup`

Manifests:

- Dry-run pairs: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/final-source-verification-2026-05-09/overwrite_current_residual_ok_2026-05-10/dry_run_pairs.csv`
- Backup/overwrite SHA manifest: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/final-source-verification-2026-05-09/overwrite_current_residual_ok_2026-05-10/overwrite_manifest.csv`
- Post-overwrite verification: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/final-source-verification-2026-05-09/overwrite_current_residual_ok_2026-05-10/post_overwrite_verification.csv`

Backup verification:

- Backup PNGs: `2464`
- Backup SHA verified against source-before hashes: `2464`
- Backup verification errors: `0`

Before copying, the script rechecked that source files still matched source-before SHA values and rerender files still matched recorded rerender SHA values.

## Results

Overwrite result:

- Manifest rows: `2464`
- Replaced source PNGs: `2464`
- Assets overwritten: `616`

Post-overwrite verification:

- Verified source PNGs: `2464`
- Assets verified: `616`
- Asset class counts after overwrite: `{'ok': 616}`
- View class counts after overwrite: `{'ok': 2464}`
- Assets not all-ok: `0`
- SHA mismatches against rerender outputs: `0`

## Rollback

Rollback can be performed by copying files from `source_png_backup/` back to the matching source paths recorded in `overwrite_manifest.csv`.

## Risks

- Source dataset PNGs for these `616` assets were intentionally modified in place.
- Binary backup and rerender PNGs should not be committed.
- The `23` residual non-ok assets were not copied back.
