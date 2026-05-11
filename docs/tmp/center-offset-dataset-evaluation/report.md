# Center Offset Dataset Evaluation

## Problem

The bottle investigation found a bbox failure mode where the authored bbox size was plausible, but its center was far from the real mesh center. This made the renderer point cameras at empty space. This evaluation checks whether the same center-offset failure appears outside `bottle`.

## Investigation

Inputs:

- Full historical quality screen: `.worktrees/quality-screening/docs/tmp/quality-screening-2026-05-08/asset_quality.csv`
- Known source-overwritten safe recovery set: `docs/tmp/bbox-rerender-selected-validation/recovered_ok_assets.csv`
- Bottle-specific center-offset scan and rerender were handled separately under `docs/tmp/bottle-blank-investigation/`

Filtering for this evaluation:

- Keep object-like `blank`, `tiny`, and `suspicious` rows.
- Exclude `bottle`, because bottle was already measured separately.
- Exclude the `460` assets already copied back to source as verified `ok`, because the historical quality CSV is stale for those rows.

Filtered population:

- Source asset rows: `53,167`
- Historical non-ok object-like rows: `3,364`
- Excluded `bottle`: `412`
- Excluded already recovered source assets: `460`
- Scanned for this evaluation: `2,492`

Scan command:

```bash
PYTHONPATH=src python scripts/tools/scan_bbox_rerender_candidates.py --asset_quality_csv docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered.csv --output_dir docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan --classes blank,tiny,suspicious --diag_ratio_threshold 5.0 --center_offset_threshold 1.0 --recommended_groups object --progress_every 500
```

Scan result:

- Scanned: `2,492`
- Recommended: `2,008`
- Center-offset-only recommendations: `1,370`
- Diagonal-inflation-only recommendations: `638`
- Scan errors: `0`

Generated scan files:

- `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/bbox_rerender_manifest.csv`
- `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/bbox_rerender_recommended.csv`
- `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv`
- `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/diag_only_recommended.csv`
- `docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/recommendation_breakdown_by_category.csv`

Top center-offset-only categories:

- `book`: `426`
- `pillow`: `243`
- `cup`: `134`
- `toy`: `108`
- `decoration`: `103`
- `pen`: `96`
- `plant`: `42`
- `towel`: `37`
- `shoe`: `35`
- `plate`: `34`

Center-offset-only by previous image class:

- `suspicious`: `758`
- `blank`: `479`
- `tiny`: `133`

## Sample Validation

A 20-asset sample was selected from the top center-offset-only non-bottle categories: `book`, `pillow`, `cup`, `toy`, `decoration`, `pen`, `plant`, `towel`, `shoe`, and `plate`.

Sample render command:

```bash
source miniconda/bin/activate render-usd && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && export OMNI_KIT_ACCEPT_EULA=YES && python scripts/tools/render_rerender_manifest.py --manifest_csv docs/tmp/center-offset-dataset-evaluation/center_only_sample_manifest.csv --output_root docs/tmp/center-offset-dataset-evaluation/center_only_sample_rerender --naming_style view --overwrite
```

Sample quality command:

```bash
python docs/tmp/bbox-rerender-selected-validation/analyze_selected_rerender.py --selected_csv docs/tmp/center-offset-dataset-evaluation/center_only_sample_manifest.csv --output_root docs/tmp/center-offset-dataset-evaluation/center_only_sample_rerender --analysis_dir docs/tmp/center-offset-dataset-evaluation/center_only_sample_analysis
```

Sample result:

- Assets rendered: `20`
- Complete assets: `20`
- Improved to `ok`: `20`
- Previous counts: `blank=10`, `suspicious=10`
- New counts: `ok=20`

## Full Non-Bottle Rerender

The `1,370` center-offset-only non-bottle candidates were submitted to DLC for isolated rerendering.

Submission command:

```bash
python scripts/dlc/submit_batch.py --total 100 --name test0_center_offset_non_bottle_rerender --data_sources d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8 --command_args "render_manifest /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv /cpfs/shared/simulation/zhuzihou/dev/render-usd/docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender {chunk_id} {chunk_total}"
```

DLC result:

- Jobs succeeded: `100/100`
- Output PNGs: `5,480/5,480`

Quality analysis command:

```bash
python docs/tmp/bbox-rerender-selected-validation/analyze_selected_rerender.py --selected_csv docs/tmp/center-offset-dataset-evaluation/object_non_ok_excluding_bottle_and_recovered_scan/center_only_recommended.csv --output_root docs/tmp/center-offset-dataset-evaluation/center_only_full_rerender --analysis_dir docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis
```

Quality analysis result:

- Assets analyzed: `1,370`
- Complete assets: `1,370`
- Improved to `ok`: `1,369`
- Previous counts: `blank=479`, `suspicious=758`, `tiny=133`
- New counts: `ok=1,369`, `suspicious=1`
- Residual non-ok: `pen/5259a9e94e1c0a24de525763dc3e9c7c` with `view_classes=ok;ok;ok;tiny`

Generated analysis files:

- `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/asset_quality_after.csv`
- `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/view_quality_after.csv`
- `docs/tmp/center-offset-dataset-evaluation/center_only_full_analysis/summary.md`

## Source Overwrite

Only the `1,369` assets with `new_class=ok` and `view_classes=ok;ok;ok;ok` were copied back to source. The residual `pen/5259a9e94e1c0a24de525763dc3e9c7c` was intentionally not copied back.

Operation directory:

- `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/`

Safety gates before copy:

- Recommended candidate assets: `1,370`
- Quality analysis assets: `1,370`
- Selected four-view `ok` assets: `1,369`
- Rejected residual: `pen/5259a9e94e1c0a24de525763dc3e9c7c`
- Bottle assets in copy scope: `0`
- Overlap with previous `460` overwrite: `0`
- Overlap with bottle `387` overwrite: `0`
- Source PNGs present/non-empty: `5,476/5,476`
- Rerender PNGs present/non-empty: `5,476/5,476`
- Backup SHA verified against source-before SHA: `5,476/5,476`
- Pre-copy source/rerender SHA recheck: passed

Post-overwrite result:

- Source PNGs replaced: `5,476`
- Assets overwritten: `1,369`
- Assets with all four source views classified `ok`: `1,369/1,369`
- Source/rerender SHA matches: `5,476/5,476`
- SHA mismatches: `0`

Generated overwrite files:

- `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/dry_run_pairs.csv`
- `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/overwrite_manifest.csv`
- `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/post_overwrite_verification.csv`
- `docs/tmp/center-offset-dataset-evaluation/overwrite_center_only_ok_2026-05-09/report.md`

## Result

The center-offset bbox failure is not bottle-specific. It appears in other object categories, especially `book`, `pillow`, `cup`, `toy`, `decoration`, and `pen`.

The scan estimated `1,370` non-bottle, not-yet-recovered object assets are center-offset-only candidates. Full rerender recovered `1,369` of them to four-view `ok` quality, and those `1,369` assets have been safely copied back to source with backup and SHA verification. One `pen` remains suspicious and was not copied back.

## Caveats

- The source quality CSV used for candidate discovery is historical. A later targeted current-source verification over the original `3,364` object-like non-ok assets is recorded under `docs/tmp/final-source-verification-2026-05-09/`.
- The `1,370` count is a bbox-evidence candidate count, not a guaranteed final copy-back count. Full rerender plus image-quality verification is still required before overwriting source PNGs.
- Structural, edge-thin, and `other` groups were intentionally excluded from recommendation because their view-quality labels need different interpretation.

## Final Follow-Up

Final targeted source verification and a current residual bbox rerender pass completed after this evaluation:

- Current residual scan input: `1,148` non-ok rows after the first three overwrite waves.
- Residual bbox candidates rerendered: `639`.
- Residual rerender quality: `616 ok`, `22 suspicious`, `1 blank`.
- Residual source overwrite: `616` assets and `2,464` PNGs copied back with backup and SHA verification.
- Final targeted source state for the original `3,364` object-like non-ok rows: `2,832 ok`, `532` remaining non-ok.
