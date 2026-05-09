# Bbox Rerender Selected DLC Report

## Problem

Some GRScenes object thumbnails were present but visually blank or tiny because invalid authored USD extent metadata inflated the renderer bbox and pushed cameras too far away. The bbox fallback fix was merged in `52cf15a`, but the affected object subset still needed a safe rerender path that does not overwrite the source dataset PNGs.

## Investigation

Full bbox-ratio scanning produced these candidate counts:

- Scanned assets: 34,153
- Recommended bbox-fallback rerender candidates: 1,098
- Candidate classes: `blank=88`, `tiny=456`, `suspicious=554`
- Scan errors: 0

Local selected validation used 36 assets: 12 blank, 12 tiny, and 12 suspicious. All 144 validation PNGs rendered. The bbox fallback recovered most blank/tiny examples but did not recover suspicious examples:

- Improved to ok: 22 of 36
- Blank recovered: 11 of 12
- Tiny recovered: 11 of 12
- Suspicious recovered: 0 of 12

Based on this evidence, the DLC rerender scope was narrowed to blank/tiny only:

- Manifest: `docs/tmp/bbox-rerender-selected-validation/bbox_rerender_blank_tiny_recommended.csv`
- Assets: 544
- Expected PNGs: 2,176
- Output root: `docs/tmp/bbox-rerender-selected-validation/test0_render_views_bbox_selected`

## Solution

Added a manifest-based render path instead of using `render_custom`, because `render_custom` writes into the source asset tree by design.

Code changes:

- `scripts/tools/render_rerender_manifest.py`: renders rows from a rerender manifest to an explicit output root while preserving `<category>/<uid>/{front,left,back,right}.png`.
- `scripts/dlc/run_task.sh`: adds `render_manifest` mode for DLC invocation.
- `tests/test_render_rerender_manifest.py`: covers chunking, manifest filtering, output path safety, missing USD skipping, required fields, and source dataset output-root rejection.
- `tests/test_dlc_run_task_manifest_mode.py`: covers shell mode exposure, argument validation, output-root preflight, and shell syntax.

Safety behavior:

- `rerender_recommended=true` rows are selected by default.
- Missing USD files are skipped with warnings unless `--fail_on_missing` is passed to the Python tool.
- Category and UID path escapes are rejected.
- Output roots inside the inferred source dataset tree are rejected.
- Isaac/Omni imports remain after `SimulationApp` initialization.

## DLC Submission

Submission command:

```bash
python scripts/dlc/submit_batch.py --total 75 --name test0_render_views_bbox_selected --data_sources d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8 --command_args "render_manifest /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bbox-rerender-selected-validation/bbox_rerender_blank_tiny_recommended.csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bbox-rerender-selected-validation/test0_render_views_bbox_selected {chunk_id} {chunk_total}"
```

Registration verification:

```bash
./dlc get job --workspace_id 270969 --display_name test0_render_views_bbox_selected --page_size 100
```

Registered jobs: 75.

Current observed status after non-empty chunks finished:

- `Succeeded`: 73
- `Queuing`: 2
- `Failed`: 0

The remaining queued jobs are chunks `73/75` and `74/75`. With 544 manifest rows and 75 chunks, the manifest chunk size is 8, so chunks `68` through `74` select zero rows. The two queued jobs therefore do not block output completeness or quality analysis.

Final output completeness:

- Complete asset dirs: 544 of 544
- PNG count: 2,176 of 2,176
- Missing source USD rows: 0

## Verification

Focused tests after review fixes:

```bash
PYTHONPATH=src python -m pytest tests/test_prim_utils_bbox.py tests/test_scan_bbox_rerender_candidates.py tests/test_render_rerender_manifest.py tests/test_dlc_run_task_manifest_mode.py
```

Result: `43 passed in 0.37s` after the manifest schema validation test was added.

Subagent review result after fixes: no remaining Critical or Important findings in the manifest rerender tooling or DLC entrypoint.

## Results

DLC output completeness is final for the 544-row manifest:

- Assets complete: 544 of 544
- PNGs complete: 2,176 of 2,176
- Missing or incomplete assets: 0

Quality analysis command:

```bash
python docs/tmp/bbox-rerender-selected-validation/analyze_selected_rerender.py --selected_csv docs/tmp/bbox-rerender-selected-validation/bbox_rerender_blank_tiny_recommended.csv --output_root docs/tmp/bbox-rerender-selected-validation/test0_render_views_bbox_selected --analysis_dir docs/tmp/bbox-rerender-selected-validation/analysis_dlc
```

Quality analysis output:

- Assets analyzed: 544
- Complete assets: 544
- Improved to ok: 460
- Previous counts: `tiny=456`, `blank=88`
- New counts: `ok=460`, `tiny=58`, `blank=26`

Transitions:

- `blank -> ok`: 62
- `blank -> blank`: 26
- `tiny -> ok`: 398
- `tiny -> tiny`: 58

Remaining non-ok assets are concentrated in two categories:

- `cabinet`: 79
- `door`: 5

Analysis outputs:

- `docs/tmp/bbox-rerender-selected-validation/analysis_dlc/asset_quality_after.csv`
- `docs/tmp/bbox-rerender-selected-validation/analysis_dlc/view_quality_after.csv`

Final consumption lists:

- `docs/tmp/bbox-rerender-selected-validation/recovered_ok_assets.csv`: 460 assets whose rerendered outputs are safe bbox-fallback recovery candidates.
- `docs/tmp/bbox-rerender-selected-validation/residual_low_quality_assets.csv`: 84 assets that remain blank/tiny and should not replace formal outputs.

Remaining operations follow-up:

- Monitor the two zero-row queued DLC jobs until terminal status, or leave them because all manifest outputs are complete.
- Separate diagnosis for the 79 cabinet and 5 door assets is recorded in `docs/tmp/remaining-cabinet-door-investigation/report.md`.
- Diagnosis result: do not change the production renderer for the residual 84; mark them as low-quality residuals. A 45-degree view offset can produce at least one usable view for 28 assets, but it does not recover the canonical four-view output contract.

## Risks

- The source-root safety check depends on either manifest `asset_dir` or the expected USD layout `<dataset>/<category>/<uid>/usd/<uid>.usd`.
- Jobs with all USDs missing can exit successfully with no outputs; output completeness verification remains mandatory.
- The active DLC jobs started before the latest local safety guard was added, but their submitted output root is outside the source dataset tree.
