# BBox-Ratio Rerender Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible manifest generator that ranks prior non-ok GRScenes renders by USD bbox fallback evidence.

**Architecture:** Add one standalone tool, `scripts/tools/scan_bbox_rerender_candidates.py`, with small pure helper functions for category grouping, class filtering, recommendation logic, CSV output, and Markdown summary output. The USD-dependent scan is isolated behind `scan_usd_bbox_effect()` so most behavior is unit-testable without opening real assets.

**Tech Stack:** Python, CSV, pathlib, argparse, NumPy, pxr.Usd, pytest

---

## File Structure

- Create: `scripts/tools/scan_bbox_rerender_candidates.py`
  - CLI entry point for scanning `asset_quality.csv`.
  - Pure helper functions for class parsing, category grouping, recommendation logic, summary counts, and CSV writing.
  - USD helper that opens a stage, selects the default prim or pseudo-root, and compares `compute_bbox(..., use_mesh_point_fallback=False)` against `compute_bbox(...)`.
- Create: `tests/test_scan_bbox_rerender_candidates.py`
  - Unit tests for helper behavior and scan flow using injected bbox scan functions.
- Create or update: `docs/tmp/2026-05-08-bbox-rerender-manifest.md`
  - Commands, limited/full scan results, artifact paths, and risks.

## Task 1: Write Failing Unit Tests

**Files:**
- Create: `tests/test_scan_bbox_rerender_candidates.py`

- [ ] **Step 1.1: Test category grouping and class parsing**

Add tests that import the future tool via `importlib.util.spec_from_file_location()` because `scripts/` is not a package. Verify `wall`, `ground`, and `ceiling` map to `structural`; `column`, `window`, and `threshold` map to `edge_thin`; `other` maps to `other`; normal categories map to `object`. Verify `parse_classes(" blank, tiny , suspicious ")` returns `{"blank", "tiny", "suspicious"}`.

- [ ] **Step 1.2: Test recommendation logic**

Verify `is_rerender_recommended(fallback_changed=True, diag_ratio=5.0, category_group="object", threshold=5.0)` returns `True`, and returns `False` when the category group is `structural`, the ratio is below threshold, or fallback did not change.

- [ ] **Step 1.3: Test scan flow with injected bbox results**

Create in-memory asset rows with classes `blank`, `tiny`, `suspicious`, and `ok`. Inject a fake bbox scan function that returns old/new diagonal values and changed flags. Assert the scan excludes `ok`, includes full manifest rows, writes `image_class`, `category_group`, `old_diag`, `new_diag`, `diag_ratio`, `fallback_changed`, `rerender_recommended`, and `scan_error`, and recommends only object rows meeting the threshold.

- [ ] **Step 1.4: Test missing USD error rows and summary output**

Inject a bbox scan function that raises or returns a scan error for one row. Assert the manifest keeps the row with `scan_error` populated, `rerender_recommended` false, and the summary text includes total scanned, recommended count, counts by image class, and counts by category group.

- [ ] **Step 1.5: Run tests and verify RED**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_scan_bbox_rerender_candidates.py -q
```

Expected before implementation: import failure or missing attribute failures from `scripts/tools/scan_bbox_rerender_candidates.py` not existing.

## Task 2: Implement Manifest Tool

**Files:**
- Create: `scripts/tools/scan_bbox_rerender_candidates.py`
- Test: `tests/test_scan_bbox_rerender_candidates.py`

- [ ] **Step 2.1: Add constants and pure helpers**

Implement field names, `parse_classes()`, `category_group_for()`, `diag()`, `format_float()`, and `is_rerender_recommended()` with the semantics from the design spec.

- [ ] **Step 2.2: Add USD bbox scanner**

Implement `scan_usd_bbox_effect(usd_path)` to open the USD with `Usd.Stage.Open(str(path))`, fail with a clear error when opening fails, select `stage.GetDefaultPrim()` when valid otherwise `stage.GetPseudoRoot()`, compute old/new bboxes via `compute_bbox()`, and return old diag, new diag, ratio, changed flag, and an empty error.

- [ ] **Step 2.3: Add row scanning and output writers**

Implement `scan_asset_rows()`, `write_csv()`, and `build_summary_markdown()`. Keep missing/unreadable USDs in the full manifest with `scan_error` set and `rerender_recommended` false.

- [ ] **Step 2.4: Add CLI**

Implement argparse options `--asset_quality_csv`, `--output_dir`, `--diag_ratio_threshold`, `--classes`, `--limit`, and `--progress_every`. Write `bbox_rerender_manifest.csv`, `bbox_rerender_recommended.csv`, and `bbox_rerender_summary.md`.

- [ ] **Step 2.5: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_scan_bbox_rerender_candidates.py -q
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python -m pytest tests/test_prim_utils_bbox.py tests/test_scan_bbox_rerender_candidates.py -q
python -m compileall scripts/tools/scan_bbox_rerender_candidates.py tests/test_scan_bbox_rerender_candidates.py
```

Expected after implementation: all tests pass and compileall succeeds.

## Task 3: Limited and Full Scan Validation

**Files:**
- Use: `scripts/tools/scan_bbox_rerender_candidates.py`
- Use: `.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv`
- Create: `docs/tmp/bbox-rerender-manifest-limited/`
- Create: `docs/tmp/bbox-rerender-manifest-full/`

- [ ] **Step 3.1: Run limited scan**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python scripts/tools/scan_bbox_rerender_candidates.py --asset_quality_csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv --output_dir docs/tmp/bbox-rerender-manifest-limited --limit 25 --progress_every 10
```

Expected: the three output artifacts are created and the summary has nonzero scanned counts.

- [ ] **Step 3.2: Run full scan**

Run:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python scripts/tools/scan_bbox_rerender_candidates.py --asset_quality_csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv --output_dir docs/tmp/bbox-rerender-manifest-full --progress_every 500
```

Expected: all default non-ok candidate rows are scanned and a recommended subset is written.

- [ ] **Step 3.3: Document results**

Write `docs/tmp/2026-05-08-bbox-rerender-manifest.md` with Problem, Investigation, Solution, Results, commands, artifact paths, and any residual risk. Do not commit unless the user explicitly asks for a commit.
