# Bottle Blank Render Investigation

## Problem

Several assets under `GRScenes_assets/bottle/` have `front/left/back/right.png` files that are present but visually blank. Two examples reported by the user were:

- `bottle/3fbea76496bf04349440a969710847fc`
- `bottle/4f2775f5bcb1559d0794f09ef6cb8f8a`

Both source assets had four `512x512` PNGs that were pure background `RGB(40,40,40)` with `0` foreground pixels.

## Investigation

The previous bbox-ratio scan did include both examples, but it did not recommend them for rerender:

- `image_class=blank`
- `diag_ratio=1.000000`
- `fallback_changed=false`
- `rerender_recommended=false`
- `view_classes=blank;blank;blank;blank`

That scan only considered authored bbox size inflation. These bottle assets had a different bbox failure mode:

- Their authored bbox diagonal length was close to the mesh-point bbox diagonal.
- Their authored bbox center was far away from the actual transformed mesh-point center.
- The renderer placed cameras around the authored bbox center, so the real geometry was outside the frame.

Representative measurements:

- `3fbea76496bf04349440a969710847fc`: authored center `[-23.55, -70.83, -53.76]`; mesh-point center `[0, 0, 0]`; center offset ratio `3.887170`.
- `4f2775f5bcb1559d0794f09ef6cb8f8a`: authored center `[24.22, -19.88, -49.69]`; mesh-point center `[0, 0, 0]`; center offset ratio `2.415501`.

Other hypotheses were tested against the two examples:

- Adding the test0 MDL search path did not fix the blank outputs.
- Forcing double-sided mesh rendering did not fix the blank outputs.
- Repairing incorrect normal interpolation warnings removed the Hydra normals warning but did not fix the blank outputs.
- Temporarily replacing materials with an opaque preview material did not fix the blank outputs while the camera still targeted the shifted authored bbox center.
- Rendering with the bbox center fallback fixed both examples to `ok;ok;ok;ok`.

## Solution

`compute_bbox()` now falls back to the mesh-point bbox when the authored bbox center is far from the mesh-point bbox center, even if the bbox diagonal sizes are similar. The existing inflated-diagonal fallback remains unchanged.

The bbox scan tool now records `center_offset_ratio` and recommends rerender if either condition is true:

- `diag_ratio >= diag_ratio_threshold`
- `center_offset_ratio >= center_offset_threshold`

`center_offset_threshold` defaults to `1.0`, is exposed as a CLI argument, and is recorded in generated summary files.

## Results

Runtime validation on the two reported bottle assets after the code change:

- `3fbea76496bf04349440a969710847fc`: `ok;ok;ok;ok`
- `4f2775f5bcb1559d0794f09ef6cb8f8a`: `ok;ok;ok;ok`

Focused tests:

```bash
PYTHONPATH=src python -m pytest tests/test_prim_utils_bbox.py tests/test_scan_bbox_rerender_candidates.py tests/test_render_rerender_manifest.py tests/test_dlc_run_task_manifest_mode.py
```

Result: `47 passed in 0.41s`.

Bottle-specific current-source scan:

- Bottle assets scanned: `676`
- Current source classification: `ok=257`, `all_blank=235`, `partial_bad=184`
- Current source view counts: `ok=1,238`, `blank=1,351`, `tiny=115`
- Missing bottle PNGs: `0`

Bottle center-offset rerender candidate scan:

- Bad bottle assets scanned: `419`
- Recommended by center/diag fallback: `387`
- Recommended blank assets: `230`
- Recommended suspicious assets: `157`
- Not recommended: `32`
- Scan errors: `0`

Generated files:

- `docs/tmp/bottle-blank-investigation/bottle_current_quality.csv`
- `docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_manifest.csv`
- `docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_recommended.csv`
- `docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_summary.md`
- `docs/tmp/bottle-blank-investigation/renders/center_fallback/`

## DLC Submission

The `387` recommended bottle assets were submitted for isolated rerendering to:

- `docs/tmp/bottle-blank-investigation/center_offset_rerender/`

Submission command:

```bash
python scripts/dlc/submit_batch.py --total 50 --name test0_bottle_center_offset_rerender --data_sources d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8 --command_args "render_manifest /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_recommended.csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/bottle-blank-investigation/center_offset_rerender {chunk_id} {chunk_total}"
```

Registration verification command:

```bash
./dlc get job --workspace_id 270969 --display_name test0_bottle_center_offset_rerender --page_size 100
```

Fresh status count after submission:

- `Queuing`: `50`

Fresh status count after completion:

- `Succeeded`: `50`

Quality analysis command:

```bash
python docs/tmp/bbox-rerender-selected-validation/analyze_selected_rerender.py --selected_csv docs/tmp/bottle-blank-investigation/center_offset_manifest/bbox_rerender_recommended.csv --output_root docs/tmp/bottle-blank-investigation/center_offset_rerender --analysis_dir docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender
```

Quality analysis result:

- Assets analyzed: `387`
- Complete assets: `387`
- Improved to `ok`: `387`
- Previous counts: `blank=230`, `suspicious=157`
- New counts: `ok=387`

Generated analysis files:

- `docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/asset_quality_after.csv`
- `docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/view_quality_after.csv`
- `docs/tmp/bottle-blank-investigation/analysis_center_offset_rerender/summary.md`

## Source Overwrite

The `387` four-view-`ok` bottle assets were copied back to the source `GRScenes_assets` tree with source backup and SHA verification.

Operation directory:

- `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/`

Safety gates before copy:

- Exact scope equality between recommended manifest and `new_class=ok` quality rows: `387/387`
- Category scope: `bottle` only
- Source and rerender path root checks: passed
- Source PNGs present/non-empty: `1,548/1,548`
- Rerender PNGs present/non-empty: `1,548/1,548`
- Backup SHA verified against source-before SHA: `1,548/1,548`
- Pre-copy source/rerender SHA recheck: passed

Post-overwrite result:

- Source PNGs replaced: `1,548`
- Assets overwritten: `387`
- Assets with all four source views classified `ok`: `387/387`
- Source/rerender SHA matches: `1,548/1,548`
- SHA mismatches: `0`

Generated overwrite files:

- `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/dry_run_pairs.csv`
- `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/overwrite_manifest.csv`
- `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/post_overwrite_verification.csv`
- `docs/tmp/bottle-blank-investigation/overwrite_387_ok_2026-05-09/report.md`

## Current State

The verified `387` bottle source assets have been overwritten with the recovered rerender PNGs. Subsequent non-bottle center-offset and current residual bbox recovery waves completed under `docs/tmp/center-offset-dataset-evaluation/` and `docs/tmp/final-source-verification-2026-05-09/`.

Final targeted source verification across the original `3,364` historical object-like non-ok assets reports `2,832 ok` and `532` remaining non-ok after all four overwrite waves.

## Review Result

Two review passes found no critical or important issues in the bbox center fallback or scanner changes. Minor auditability feedback was addressed by exposing and recording `center_offset_threshold` and validating it as finite and positive.
