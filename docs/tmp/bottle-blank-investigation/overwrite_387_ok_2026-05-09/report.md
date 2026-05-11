# Bottle Center-Offset Source Overwrite Report

## Problem

The `387` verified bottle center-offset rerender outputs were still isolated under `docs/tmp/bottle-blank-investigation/center_offset_rerender/` and had not been copied back into the source `GRScenes_assets` tree.

## Investigation

Overwrite scope was locked by exact set equality between:

- `docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_recommended.csv`
- `docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/asset_quality_after.csv`

Dry-run validation before mutation:

- Selected assets: `387`
- PNG pairs checked: `1548`
- Source PNGs present and non-empty: `1548`
- Rerender PNGs present and non-empty: `1548`
- Already-identical PNG pairs before overwrite: `0`
- Planned overwrite PNG pairs: `1548`
- Validation errors: `0`

## Solution

Original source PNGs were backed up under:

`/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/source_png_backup`

Manifests:

- Dry-run pairs: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/dry_run_pairs.csv`
- Backup/overwrite SHA manifest: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/overwrite_manifest.csv`
- Post-overwrite verification: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/post_overwrite_verification.csv`

Backup verification:

- Backup PNGs: `1548`
- Backup SHA verified against source-before hashes: `1548`
- Backup verification errors: `0`

Before copying, the script rechecked that source files still matched source-before SHA values and rerender files still matched recorded rerender SHA values.

## Results

Overwrite result:

- Manifest rows: `1548`
- Replaced source PNGs: `1548`
- Assets overwritten: `387`

Post-overwrite verification:

- Verified source PNGs: `1548`
- Assets verified: `387`
- Assets with all four views classified `ok`: `387`
- Assets not all-ok: `0`
- View class counts: `{'ok': 1548}`
- SHA mismatches against rerender outputs: `0`

## Rollback

Rollback can be performed by copying files from `source_png_backup/` back to the matching source paths recorded in `overwrite_manifest.csv`.

## Risks

- Source dataset PNGs for these `387` bottle assets were intentionally modified in place.
- Binary backup and rerender PNGs should not be committed.
