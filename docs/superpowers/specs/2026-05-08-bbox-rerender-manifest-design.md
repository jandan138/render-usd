# Design: BBox-Ratio Rerender Manifest

## Problem

Small-batch rerender validation showed that bbox fallback improves many selected bbox-ratio-positive object assets, but it does not make every `blank`/`tiny` output useful. Structural and thin/edge categories can remain low-visibility after bbox correction. A DLC rerender should therefore target assets with USD bbox evidence and useful category grouping, not all non-ok image-quality rows.

## Goal

Produce a reproducible CSV manifest that ranks GRScenes assets for bbox-fallback rerendering using both prior image-quality labels and USD bbox-ratio evidence.

## Non-Goals

- Do not render images.
- Do not modify USD assets or source PNGs.
- Do not require Isaac Sim; the scan uses `pxr` only.
- Do not decide final DLC chunking or submit jobs in this step.

## Chosen Design

Create a standalone tool under `scripts/tools/scan_bbox_rerender_candidates.py`.

Inputs:

- `--asset_quality_csv`: the full image screening CSV with `category`, `uid`, `class`, and `usd_path` fields.
- `--output_dir`: where to write manifest artifacts.
- Optional thresholds: `--diag_ratio_threshold` default `5.0`, `--classes` default `blank,tiny,suspicious`, and category-group controls.

Processing:

1. Read `asset_quality.csv`.
2. Filter to requested image classes, defaulting to `blank`, `tiny`, and `suspicious` because `suspicious` had strong bad-extent evidence in sampling.
3. For each candidate USD, open the stage with `pxr.Usd`.
4. Use `compute_bbox(prim, use_mesh_point_fallback=False)` for authored bbox and `compute_bbox(prim)` for fallback bbox.
5. Compute `old_diag`, `new_diag`, `diag_ratio`, and `fallback_changed`.
6. Assign `category_group`:
   - `structural`: `wall`, `ground`, `ceiling`
   - `edge_thin`: `column`, `window`, `threshold`
   - `other`: `other`
   - `object`: everything else
7. Set `rerender_recommended=True` only when `fallback_changed`, `diag_ratio >= threshold`, and `category_group == object` by default.
8. Write a full scanned manifest and a recommended rerender manifest.

Outputs:

- `bbox_rerender_manifest.csv`: all scanned candidates.
- `bbox_rerender_recommended.csv`: recommended object-category rerender subset.
- `bbox_rerender_summary.md`: counts by image class, category group, and recommendation.

## Error Handling

- Missing or unreadable USDs remain in the full manifest with `scan_error` populated and `rerender_recommended=False`.
- Non-finite or zero fallback bbox produces `fallback_changed=False` unless `compute_bbox()` returns a valid fallback.
- The tool supports `--limit` and `--progress_every` for controlled dry runs.

## Testing

Unit tests should cover:

- Category grouping.
- Recommendation logic.
- CSV field parsing and class filtering.
- Error row handling for missing USDs.
- Summary count generation.

Integration validation should run a limited scan first, then the full scan over the existing `asset_quality.csv`.

## Acceptance Criteria

- Tests pass with system Python.
- The tool compiles.
- Limited scan produces expected CSVs and summary.
- Full scan completes and produces counts suitable for deciding a targeted DLC rerender scope.
