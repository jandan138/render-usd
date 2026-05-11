# Center Offset Source Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely recover center-offset bbox render failures in the source GRScenes asset PNGs without overwriting unverified outputs.

**Architecture:** Use existing manifest rerender and image-quality analysis workflows. Every source overwrite must be preceded by a source backup and SHA manifest, then followed by source quality verification and rerender/source SHA matching.

**Tech Stack:** Python 3.10, Isaac Sim renderer via `scripts/tools/render_rerender_manifest.py`, DLC via `scripts/dlc/submit_batch.py`, CSV manifests, SHA-256 verification.

---

### Task 1: Bottle Source Overwrite

**Files:**
- Read: `docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_recommended.csv`
- Read: `docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/asset_quality_after.csv`
- Read: `docs/tmp/bottle-blank-investigation/center_offset_rerender/`
- Write: `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/overwrite_manifest.csv`
- Write: `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/post_overwrite_verification.csv`
- Write: `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/report.md`
- Modify: `docs/tmp/bottle-blank-investigation/report.md`

- [ ] **Step 1: Verify bottle rerender quality input**

Run:

```bash
python - <<'PY'
import csv
from pathlib import Path
quality = Path('docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/asset_quality_after.csv')
rows = list(csv.DictReader(quality.open(newline='')))
bad = [row for row in rows if row['new_class'] != 'ok']
print('rows=', len(rows))
print('bad=', len(bad))
PY
```

Expected: `rows= 387`, `bad= 0`.

- [ ] **Step 2: Backup source PNGs, write SHA manifest, copy rerender PNGs**

Run a Python operation that only selects rows from `asset_quality_after.csv` with `new_class == "ok"`, backs up `front/left/back/right.png` from source to `source_png_backup/<category>/<uid>/`, records old and new SHA-256 values in `overwrite_manifest.csv`, then copies the rerender PNGs into each source asset directory.

- [ ] **Step 3: Verify post-overwrite source PNGs**

Run a Python verification that reclassifies copied source PNGs using the same thresholds as `analyze_selected_rerender.py`, writes `post_overwrite_verification.csv`, and checks every asset is `ok` with source SHA equal to rerender SHA.

- [ ] **Step 4: Update bottle report**

Record source overwrite counts, backup path, manifest path, post-overwrite quality counts, and any residual risks in `docs/tmp/bottle-blank-investigation/report.md`.

### Task 2: Non-Bottle Center-Offset Rerender

**Files:**
- Read: `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv`
- Write: `docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender/`
- Write: `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/asset_quality_after.csv`
- Write: `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/view_quality_after.csv`
- Modify: `docs/tmp/center-offset-dataset-evaluation/report.md`

- [ ] **Step 1: Submit DLC rerender jobs**

Run:

```bash
python scripts/dlc/submit_batch.py --total 100 --name test0_center_offset_non_bottle_rerender --data_sources d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8 --command_args "render_manifest /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender {chunk_id} {chunk_total}"
```

- [ ] **Step 2: Poll DLC to terminal state**

Poll `./dlc get job --workspace_id 270969 --display_name test0_center_offset_non_bottle_rerender --page_size 100` until all `100` jobs are `Succeeded`, `Failed`, or `Stopped`.

- [ ] **Step 3: Analyze rerender quality**

Run:

```bash
python docs/tmp/bbox-rerender-selected-validation/analyze_selected_rerender.py --selected_csv docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv --output_root docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender --analysis_dir docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis
```

- [ ] **Step 4: Update evaluation report**

Record DLC job counts, PNG counts, quality counts, and exact analysis file paths in `docs/tmp/center-offset-dataset-evaluation/report.md`.

### Task 3: Non-Bottle Source Overwrite

**Files:**
- Read: `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/asset_quality_after.csv`
- Read: `docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender/`
- Write: `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/overwrite_manifest.csv`
- Write: `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/post_overwrite_verification.csv`
- Write: `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/report.md`
- Modify: `docs/tmp/center-offset-dataset-evaluation/report.md`

- [ ] **Step 1: Select only four-view ok assets**

Read `asset_quality_after.csv` and select only rows with `new_class == "ok"`.

- [ ] **Step 2: Backup source PNGs, write SHA manifest, copy rerender PNGs**

Back up source PNGs into `source_png_backup/<category>/<uid>/`, record old and new SHA-256 values in `overwrite_manifest.csv`, then copy only selected rerender PNGs into source asset directories.

- [ ] **Step 3: Verify post-overwrite source PNGs**

Reclassify source PNGs for overwritten assets and verify every copied source SHA equals the rerender SHA.

- [ ] **Step 4: Update evaluation report**

Record overwrite counts, backup path, SHA verification counts, post-overwrite quality counts, and residual non-ok count.

### Task 4: Final Verification and Review

**Files:**
- Read: `docs/tmp/bottle-blank-investigation/report.md`
- Read: `docs/tmp/center-offset-dataset-evaluation/report.md`
- Read: `src/render_usd/utils/usd_utils/prim_utils.py`
- Read: `scripts/tools/scan_bbox_rerender_candidates.py`
- Read: `tests/test_prim_utils_bbox.py`
- Read: `tests/test_scan_bbox_rerender_candidates.py`

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_prim_utils_bbox.py tests/test_scan_bbox_rerender_candidates.py tests/test_render_rerender_manifest.py tests/test_dlc_run_task_manifest_mode.py
```

Expected: all tests pass.

- [ ] **Step 2: Run diff hygiene check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 3: Request independent review**

Dispatch review agents to check source overwrite safety evidence, rerender quality evidence, and code/test consistency.

- [ ] **Step 4: Final report**

Summarize recovered counts, residual risks, generated files, verification commands, and state that no git commit was made unless explicitly requested.
