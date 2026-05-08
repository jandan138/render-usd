# BBox-Ratio Rerender Manifest Validation

## Problem

The full GRScenes image-quality screening had `34,153` non-ok or suspicious assets across `blank`, `tiny`, and `suspicious` classes. Small-batch validation showed that bbox fallback helps selected object assets with inflated authored extents, but structural and thin/edge categories often remain low visibility. A full rerender should therefore target assets with both image-quality evidence and USD bbox-ratio evidence, rather than rerendering every non-ok row.

## Investigation

Inputs:

- Source screening CSV: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv`
- Manifest design: `docs/superpowers/specs/2026-05-08-bbox-rerender-manifest-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-08-bbox-rerender-manifest.md`

The scan compares two bboxes for each candidate USD:

- Authored bbox: `compute_bbox(prim, use_mesh_point_fallback=False)`
- Fallback bbox: `compute_bbox(prim)`

Default recommendation criteria:

- `image_class` in `blank,tiny,suspicious`
- fallback bbox changed the result
- `old_diag / new_diag >= 5.0`
- `category_group == object`

Category groups:

- `structural`: `wall`, `ground`, `ceiling`
- `edge_thin`: `column`, `window`, `threshold`
- `other`: `other`
- `object`: all remaining categories

## Solution

Added `scripts/tools/scan_bbox_rerender_candidates.py`.

The tool writes:

- `bbox_rerender_manifest.csv`: all scanned candidates
- `bbox_rerender_recommended.csv`: recommended object-category subset
- `bbox_rerender_summary.md`: aggregate scan counts

The CLI supports:

- `--asset_quality_csv`
- `--output_dir`
- `--diag_ratio_threshold`, default `5.0`
- `--classes`, default `blank,tiny,suspicious`
- `--recommended_groups`, default `object`
- `--limit`
- `--progress_every`

Implementation notes:

- Missing or unreadable USDs stay in the full manifest with `scan_error` populated and `rerender_recommended=false`.
- Zero-size or non-finite fallback bboxes do not count as changed and do not emit ratio evidence.
- The tool does not render images and does not modify USD assets or source PNGs.

## Verification

TDD red check:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_scan_bbox_rerender_candidates.py -q
```

Initial result before implementation: `5 failed`, all due to missing `scripts/tools/scan_bbox_rerender_candidates.py`.

Final unit/regression tests:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py tests/test_scan_bbox_rerender_candidates.py -q
```

Result: `30 passed in 0.29s`.

Compile check:

```bash
python -m compileall scripts/tools/scan_bbox_rerender_candidates.py tests/test_scan_bbox_rerender_candidates.py
```

Result: succeeded.

Limited scan command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python scripts/tools/scan_bbox_rerender_candidates.py --asset_quality_csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv --output_dir docs/tmp/bbox-rerender-manifest-limited --limit 25 --progress_every 10
```

Limited scan result: `scanned=25 recommended=7`.

Full scan command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python scripts/tools/scan_bbox_rerender_candidates.py --asset_quality_csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv --output_dir docs/tmp/bbox-rerender-manifest-full --progress_every 500
```

Full scan result: `scanned=34153 recommended=1098`.

## Results

Full manifest summary:

- total scanned: `34,153`
- recommended: `1,098`
- fallback changed: `29,310`
- scan errors: `0`

Counts by image class:

- `blank`: `9,319`
- `suspicious`: `19,220`
- `tiny`: `5,614`

Counts by category group:

- `structural`: `23,933`
- `other`: `6,020`
- `object`: `3,364`
- `edge_thin`: `836`

Recommended rows by image class:

- `suspicious`: `554`
- `tiny`: `456`
- `blank`: `88`

Top recommended categories:

- `cabinet`: `487`
- `door`: `167`
- `desk`: `71`
- `faucet`: `41`
- `pan`: `31`
- `dish_washer`: `29`
- `washing_machine`: `27`
- `hearth`: `26`
- `night_stand`: `26`
- `pot`: `22`

Artifacts:

- Limited manifest: `docs/tmp/bbox-rerender-manifest-limited/bbox_rerender_manifest.csv`
- Limited recommended subset: `docs/tmp/bbox-rerender-manifest-limited/bbox_rerender_recommended.csv`
- Limited summary: `docs/tmp/bbox-rerender-manifest-limited/bbox_rerender_summary.md`
- Full manifest: `docs/tmp/bbox-rerender-manifest-full/bbox_rerender_manifest.csv`
- Full recommended subset: `docs/tmp/bbox-rerender-manifest-full/bbox_rerender_recommended.csv`
- Full summary: `docs/tmp/bbox-rerender-manifest-full/bbox_rerender_summary.md`

## Review

Two independent reviews were run after the first implementation.

Spec review initially found:

- Missing configurable category-group controls.
- Invalid or zero fallback bboxes could still be reported as changed.
- Summary lacked true/false recommendation counts.

Code quality review initially found:

- Invalid fallback bboxes could emit `diag_ratio=inf`, which could mislead manual ranking even though rows were not recommended.

Fixes added:

- `--recommended_groups` and `parse_category_groups()`.
- Manifest-level fallback validity gating.
- `bbox_effect_from_bboxes()` to omit ratio evidence for invalid fallback bboxes.
- Summary counts by recommendation.
- Additional tests for category group controls, invalid fallback handling, and ratio omission.

Re-review result: no findings for the previously flagged issues.

## Risks / Next Step

- The `1,098` recommended rows are rerender candidates, not guaranteed recoveries. The object-focused small batch improved `11/20` selected bbox-ratio-positive samples to `ok`.
- Structural, thin/edge, and `other` categories show many fallback changes but are intentionally excluded from the default rerender recommendation because prior validation showed bbox correction alone often does not make those thumbnails useful.
- Next step is a small DLC or local rerender of the `bbox_rerender_recommended.csv` subset, followed by the same image-quality analyzer to measure recovery before committing to a larger rerender campaign.
