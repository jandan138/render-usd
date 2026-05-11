# Overwrite 460 Recovered OK Assets Report

## Problem

The source `GRScenes_assets` tree still contained old tiny or blank PNGs for assets that were recovered by the bbox-fallback rerender workflow. The user requested copying the recovered results back into the source dataset tree.

## Investigation

The overwrite scope was confirmed as the `460` assets listed in `docs/tmp/bbox-rerender-selected-validation/recovered_ok_assets.csv`, not the full `544` rerendered assets. This avoids writing the `84` residual low-quality assets back to the source tree.

Dry-run validation checked every row before writing:

- Selected assets: `460`
- PNG pairs checked: `1,840`
- Source PNGs present and non-empty: `1,840`
- Rerender PNGs present and non-empty: `1,840`
- Already-identical PNG pairs before overwrite: `0`
- Planned overwrite PNG pairs: `1,840`
- Validation errors: `0`

## Solution

Before overwriting, the original source PNGs were backed up under:

`docs/tmp/bbox-rerender-selected-validation/overwrite_460_ok_2026-05-09/source_png_backup/`

The backup manifest is:

`docs/tmp/bbox-rerender-selected-validation/overwrite_460_ok_2026-05-09/overwrite_manifest.csv`

The manifest records source paths, backup paths, rerender paths, source SHA-256 before overwrite, rerender SHA-256, and file sizes.

Backup verification result:

- Backup PNGs: `1,840`
- Backup SHA verified against source-before hashes: `1,840`
- Backup verification errors: `0`

Only after backup verification, each source PNG was replaced with the corresponding rerender PNG. The overwrite script preflighted that source files still matched their backup-time SHA and that rerender files still matched the recorded rerender SHA before replacing anything.

## Results

Overwrite result:

- Manifest rows: `1,840`
- Replaced source PNGs: `1,840`
- Assets overwritten: `460`

Post-overwrite verification output:

`docs/tmp/bbox-rerender-selected-validation/overwrite_460_ok_2026-05-09/post_overwrite_verification.csv`

Post-overwrite verification result:

- Verified source PNGs: `1,840`
- Assets verified: `460`
- Assets with all four views classified `ok`: `460`
- Assets not all-ok: `0`
- View class counts: `ok=1,840`
- SHA mismatches against rerender outputs: `0`

Global source-tree completeness after overwrite remained:

- Asset directories scanned: `53,202`
- Asset dirs with all four required PNGs: `53,167`
- Asset dirs missing required PNGs: `35`
- Zero-size PNGs: `0`

The remaining `35` missing-PNG directories are unchanged from the earlier completeness scan and correspond to directories without source USDs.

Representative fixed source asset:

- `basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1`: source `front/left/back/right.png` now match the recovered rerender outputs. Before this overwrite, the source images were classified `blank` with only a roughly `4x4` foreground bbox; after overwrite, all four source views are classified `ok`.

## Rollback

Rollback can be performed by copying files from `source_png_backup/` back to the matching source paths recorded in `overwrite_manifest.csv`.

## Risks

- The source dataset PNGs for these `460` assets have been intentionally modified in place.
- The backup exists in the project `docs/tmp` tree and should not be committed as binary output.
- The `84` residual low-quality rerender outputs were not copied back.
