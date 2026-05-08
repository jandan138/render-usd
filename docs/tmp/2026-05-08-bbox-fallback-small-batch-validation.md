# BBox Fallback Small-Batch Render Validation

## Problem

The bbox fallback fixed the known basket examples in bbox diagnostics and a one-asset render smoke test. Before any full DLC rerun, we need a broader controlled rerender that separates two cases:

- Object-category assets where invalid authored extents push the camera too far away.
- Structural or thin/edge assets (`wall`, `ground`, `column`, `window`, `threshold`, etc.) where bbox correction alone may not make four object-thumbnail views useful. This residual low visibility can also come from camera/view policy, material/background segmentation, or asset content issues.

## Investigation

Two temporary rerender batches were run from the isolated worktree:

`/cpfs/shared/simulation/zhuzihou/dev/render-usd/.worktrees/bbox-fallback`

Both wrote only under:

`docs/tmp/bbox-fallback-small-batch-render-validation/`

The original dataset PNGs under `/cpfs/user/zhuzihou/.../GRScenes_assets` were not overwritten.

### Batch 1: Mixed Tiny/Blank Sample

Selection:

- `24` assets total.
- `12` previous `blank`, `12` previous `tiny`.
- Included the known bad baskets.
- Mostly selected from `usd_root_cause_samples.csv` with bad-extent evidence.
- Included structural categories because they dominate full-screening non-ok counts.

Render command:

```bash
source "/cpfs/shared/simulation/zhuzihou/dev/render-usd/miniconda/bin/activate" render-usd && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && export OMNI_KIT_ACCEPT_EULA=YES && export PYTHONUNBUFFERED=1 && python docs/tmp/bbox-fallback-small-batch-render-validation/run_small_batch_render.py docs/tmp/bbox-fallback-small-batch-render-validation/selected_usds.txt docs/tmp/bbox-fallback-small-batch-render-validation/renders
```

Analysis command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python docs/tmp/bbox-fallback-small-batch-render-validation/analyze_small_batch.py
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python docs/tmp/bbox-fallback-small-batch-render-validation/analyze_bbox_effect.py
```

Results:

```text
assets=24 complete=24 improved_to_ok=4
previous_counts={'blank': 12, 'tiny': 12}
new_counts={'blank': 11, 'ok': 4, 'tiny': 9}
view_counts={'blank': 71, 'ok': 16, 'tiny': 9}
rows=24 fallback_changed=22 fallback_changed_and_ok=4 unchanged_and_ok=0
```

Interpretation:

- The bbox fallback was applied for `22/24` assets.
- The two known baskets both improved to `ok`.
- The mixed batch remained mostly non-ok because it intentionally included many `wall` and `ground` samples. These are frequently low-visibility from four object-thumbnail views even after bbox correction.

### Batch 2: Object-Focused BBox-Ratio-Positive Sample

Selection:

- `20` assets total.
- Excluded the most dominant structural screening categories: `wall`, `ground`, `ceiling`, and `other`.
- Selected from previous `blank`/`tiny` rows whose USD bbox changed under the fallback and whose authored/new diagonal ratio was at least `5x`. Therefore, the `20/20` fallback rate below is selection-implied and not population-wide evidence.
- Categories included object classes such as `dish_washer`, `refrigerator`, `faucet`, `cabinet`, `microwave`, `desk`, `cart`, `pan`, and `night_stand`, plus edge/thin classes such as `threshold`, `column`, and `window` that should remain separately labeled in any rerender manifest.

Selection command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python docs/tmp/bbox-fallback-small-batch-render-validation/select_object_batch.py
```

Render command:

```bash
source "/cpfs/shared/simulation/zhuzihou/dev/render-usd/miniconda/bin/activate" render-usd && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && export OMNI_KIT_ACCEPT_EULA=YES && export PYTHONUNBUFFERED=1 && python docs/tmp/bbox-fallback-small-batch-render-validation/run_small_batch_render.py docs/tmp/bbox-fallback-small-batch-render-validation/object_selected_usds.txt docs/tmp/bbox-fallback-small-batch-render-validation/object_renders
```

Analysis command:

```bash
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python docs/tmp/bbox-fallback-small-batch-render-validation/analyze_small_batch.py docs/tmp/bbox-fallback-small-batch-render-validation/object_selected_assets.csv docs/tmp/bbox-fallback-small-batch-render-validation/object_renders object_
PYTHONPATH="$PYTHONPATH:$(pwd)/src" python docs/tmp/bbox-fallback-small-batch-render-validation/analyze_bbox_effect.py docs/tmp/bbox-fallback-small-batch-render-validation/object_selected_assets.csv docs/tmp/bbox-fallback-small-batch-render-validation/object_asset_quality_after.csv object_
```

Results:

```text
assets=20 complete=20 improved_to_ok=11
previous_counts={'blank': 3, 'tiny': 17}
new_counts={'blank': 3, 'ok': 11, 'tiny': 6}
view_counts={'blank': 30, 'ok': 44, 'tiny': 6}
rows=20 fallback_changed=20 fallback_changed_and_ok=11 unchanged_and_ok=0
```

Selected bbox-ratio-positive assets improved to `ok`:

- `dish_washer/2991148db83892dee23db1ee00f054b1`
- `refrigerator/04b384cf8c8cb3a1e69fe32e321efd00`
- `faucet/819dedfb27592364d6ad4f2800278205`
- `microwave/f4e870a6475e1cc8ab7721106fca4c8b`
- `desk/549c97eff42f1a6ec00bbfbd1a3cd0fe`
- `cart/3c99611fcb49f3472a77439fb7c99bfb`
- `cabinet/e5733fb5d4828ae51248579ee1a996e6`
- `desk/4381f6120ac3eb9bcf07636c316bc7c1`
- `pan/536cf7bc12df75800bfba942d19cba0c`
- `window/50958e275f8523ef5b01b509ec2f1aa0`
- `night_stand/1cc49bc9d06e2357b052f1d989676bae`

Selected bbox-ratio-positive assets still non-ok after fallback:

- `blank`: `threshold/f86790f72ec4229c96512289d524a8ff`, `cabinet/ebc2b84a248d43815706c0cc06013d2d`, `column/ab645b4677de2327015375898cc4c21e`
- `tiny`: `cabinet/9d7a33fc87f1d1f35b9b6c27aa9f0f3c`, `cabinet/68007680b83db0c9fbc59f2431607d9f`, `column/195764fa598b923cf866c3738446d0f4`, `cabinet/5beeaa7bfe13ad1b18b3e90600a3e58e`, `cabinet/e9a4e1fc5ec5eaa27245f6a2b75993ba`, `window/fbe55d2e3f6d944b1d9b92c592555a6d`

## Solution

Keep the bbox fallback implementation. It fixes the confirmed root cause for many selected bbox-ratio-positive renders without changing renderer camera angles or source USD files.

Use the small-batch result to avoid overclaiming:

- Among selected non-dominant-structural assets with bbox-ratio evidence, bbox fallback improved thumbnail framing for `11/20` samples. This is not a population-wide recovery rate because the batch was prefiltered for fallback applicability.
- For structural/thin/edge classes, bad authored extents can be present but bbox correction alone often does not make four object-thumbnail views useful. The remaining cause is not proven by this test alone.

## Results

Artifacts:

- Mixed selection: `docs/tmp/bbox-fallback-small-batch-render-validation/selected_assets.csv`
- Mixed rendered metrics: `docs/tmp/bbox-fallback-small-batch-render-validation/asset_quality_after.csv`
- Mixed bbox effect: `docs/tmp/bbox-fallback-small-batch-render-validation/bbox_effect.csv`
- Object selection: `docs/tmp/bbox-fallback-small-batch-render-validation/object_selected_assets.csv`
- Object rendered metrics: `docs/tmp/bbox-fallback-small-batch-render-validation/object_asset_quality_after.csv`
- Object bbox effect: `docs/tmp/bbox-fallback-small-batch-render-validation/object_bbox_effect.csv`
- Rendered PNGs: `docs/tmp/bbox-fallback-small-batch-render-validation/renders/` and `docs/tmp/bbox-fallback-small-batch-render-validation/object_renders/`

Key result:

- Mixed batch: `4/24` improved to `ok`, but dominated by structural samples.
- Object-focused bbox-ratio-positive batch: `11/20` improved to `ok`.
- All selected assets rendered all four views in temporary output directories.

## Risks / Next Step

- Do not use the full image-quality `blank/tiny/suspicious` classes alone to decide rerender scope. Structural categories overrepresent non-ok outputs and often remain low-visibility even after bbox correction.
- A rerender campaign should prioritize assets with USD bbox ratio evidence and category grouping, not every `blank`/`tiny` row.
- Category groups should separate normal object categories from edge/thin/structural categories such as `wall`, `ground`, `ceiling`, `column`, `window`, `threshold`, and likely `other`.
- Next recommended step is a full USD bbox-ratio scan over all assets, producing a rerender manifest with columns `category`, `uid`, `image_class`, `category_group`, `old_diag`, `new_diag`, `diag_ratio`, and `rerender_recommended`.
- After that, run DLC only for the recommended object-like bad-extent subset, not for all `53167` assets.
