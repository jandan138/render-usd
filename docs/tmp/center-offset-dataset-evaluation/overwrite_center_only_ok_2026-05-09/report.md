# Non-Bottle Center-Offset Source Overwrite Report

## Problem

The full non-bottle center-offset rerender recovered `1,369` assets to four-view `ok`, while one `pen` asset remained suspicious. Only the verified `ok` assets should be copied back to source.

## Investigation

Overwrite scope was locked by exact set checks:

- Recommended candidate assets: `1,370`
- Quality analysis assets: `1,370`
- Selected `new_class=ok` and `view_classes=ok;ok;ok;ok`: `1,369`
- Rejected residual: `pen/5259a9e94e1c0a24de525763dc3e9c7c`
- Bottle assets in scope: `0`
- Overlap with previous 460 overwrite: `0`
- Overlap with bottle 387 overwrite: `0`

Dry-run validation before mutation:

- Selected assets: `1369`
- PNG pairs checked: `5476`
- Source PNGs present and non-empty: `5476`
- Rerender PNGs present and non-empty: `5476`
- Already-identical PNG pairs before overwrite: `0`
- Planned overwrite PNG pairs: `5476`
- Source asset classes before overwrite: `{'suspicious': 758, 'blank': 478, 'tiny': 133}`
- Validation errors: `0`

## Solution

Original source PNGs were backed up under:

`/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/source_png_backup`

Manifests:

- Dry-run pairs: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/dry_run_pairs.csv`
- Backup/overwrite SHA manifest: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/overwrite_manifest.csv`
- Post-overwrite verification: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/post_overwrite_verification.csv`

Backup verification:

- Backup PNGs: `5476`
- Backup SHA verified against source-before hashes: `5476`
- Backup verification errors: `0`

Before copying, the script rechecked that source files still matched source-before SHA values and rerender files still matched recorded rerender SHA values.

## Results

Overwrite result:

- Manifest rows: `5476`
- Replaced source PNGs: `5476`
- Assets overwritten: `1369`

Post-overwrite verification:

- Verified source PNGs: `5476`
- Assets verified: `1369`
- Asset class counts after overwrite: `{'ok': 1369}`
- View class counts after overwrite: `{'ok': 5476}`
- Assets not all-ok: `0`
- SHA mismatches against rerender outputs: `0`

## Rollback

Rollback can be performed by copying files from `source_png_backup/` back to the matching source paths recorded in `overwrite_manifest.csv`.

## Risks

- Source dataset PNGs for these `1,369` non-bottle assets were intentionally modified in place.
- Binary backup and rerender PNGs should not be committed.
- The residual `pen/5259a9e94e1c0a24de525763dc3e9c7c` was not copied back.
