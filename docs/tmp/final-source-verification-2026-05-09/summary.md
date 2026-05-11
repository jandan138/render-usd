# Final Source Verification 2026-05-09

Scope: historical object-like non-ok assets from the 2026-05-08 full quality screen.

## Source Recovery Waves

- Initial bbox-ratio blank/tiny overwrite: `460` assets, `1,840` PNGs.
- Bottle center-offset overwrite: `387` assets, `1,548` PNGs.
- Non-bottle center-offset overwrite: `1,369` assets, `5,476` PNGs.
- Current residual bbox overwrite: `616` assets, `2,464` PNGs.
- Total verified source overwrites in this recovery: `2,832` assets, `11,328` PNGs.

## Targeted Source Verification

- Assets scanned: `3,364`
- Historical counts: `{'tiny': 609, 'blank': 817, 'suspicious': 1938}`
- Counts before the current residual bbox overwrite: `{'ok': 2216, 'suspicious': 1041, 'blank': 47, 'tiny': 60}`
- Counts after the current residual bbox overwrite: `{'ok': 2832, 'suspicious': 508, 'blank': 22, 'tiny': 2}`
- Non-ok before the current residual bbox overwrite: `1,148`
- Non-ok after the current residual bbox overwrite: `532`
- Newly recovered by the current residual bbox overwrite: `616`
- Regressed from pre-residual `ok`: `0`

## Current Residual BBox Pass

- Residual scan input: `docs/tmp/final-source-verification-2026-05-09/current_object_non_ok_quality_for_scan.csv`
- Residual scan candidates: `639`
- DLC rerender output root: `docs/tmp/final-source-verification-2026-05-09/current_residual_bbox_rerender/`
- Rerender quality: `616 ok`, `22 suspicious`, `1 blank`
- Source overwrite operation: `docs/tmp/final-source-verification-2026-05-09/overwrite_current_residual_ok_2026-05-10/`
- Post-overwrite verification: `616/616` assets all four source views `ok`; `2,464/2,464` source SHA hashes match rerender outputs.

## Top Post-Residual Non-OK Category/Class Counts

- pillow/suspicious: 283
- pen/suspicious: 51
- book/suspicious: 31
- bottle/suspicious: 20
- cup/suspicious: 18
- cabinet/suspicious: 17
- toy/suspicious: 15
- picture/suspicious: 14
- shelf/suspicious: 10
- plant/suspicious: 9
- towel/suspicious: 8
- decoration/suspicious: 6
- plate/suspicious: 6
- blanket/suspicious: 5
- bottle/blank: 5
- door/suspicious: 5
- pen/blank: 5
- cabinet/blank: 2
- chair/suspicious: 2
- cup/blank: 2
- curtain/suspicious: 2
- decoration/blank: 2
- plant/blank: 2
- shoe/suspicious: 2
- tray/suspicious: 2
- book/blank: 1
- clothes/suspicious: 1
- couch/blank: 1
- pan/suspicious: 1
- pen/tiny: 1
- picture/blank: 1
- toy/tiny: 1
- toy/blank: 1

## Files

- Pre-residual targeted source quality CSV: `docs/tmp/final-source-verification-2026-05-09/object_non_ok_historical_current_quality.csv`
- Post-residual targeted source quality CSV: `docs/tmp/final-source-verification-2026-05-09/object_non_ok_historical_current_quality_after_residual.csv`
- Post-residual non-ok CSV: `docs/tmp/final-source-verification-2026-05-09/current_object_non_ok_quality_after_residual.csv`
- Generated post-residual summary: `docs/tmp/final-source-verification-2026-05-09/summary_after_residual.md`
- Residual triage and next-action decision: `docs/tmp/final-source-verification-2026-05-09/residual_532_triage.md`
