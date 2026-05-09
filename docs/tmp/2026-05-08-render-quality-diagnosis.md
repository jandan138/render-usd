# Render Quality Diagnosis: Tiny/Blank Basket Views

**Date:** 2026-05-08
**Mode:** Diagnosis only, no code changes

## Problem

Some completed `test0_render_views` outputs are technically present but visually poor:

- `basket/040600389fdab577a5376c28e6c5eb15` renders as a tiny object.
- `basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1` renders almost blank.

The initial camera-distance hypothesis was not sufficient because `UsdGeom.Imageable.ComputeWorldBound()` reported very large bounds, and the renderer positioned the camera from those bounds as intended.

## Investigation

### DLC State

Current DLC query for `test0_render_views`:

- `Succeeded`: 74 chunk jobs
- `Failed`: 75 jobs, including 73 historic bad-template submissions, one test job, and chunk `1/75`
- `Running`, `Queuing`, `EnvPreparing`: 0

Chunk `1/75` has status `Failed` with reason code `137`, but local output validation found all 709 assets in that chunk have `front.png`, `left.png`, `back.png`, and `right.png`.

Full output completeness scan:

- Total assets: 53,167
- Complete four-view outputs: 53,167
- Partial outputs: 0
- Missing outputs: 0

### USD Evidence

Compared three assets with `pxr.Usd`, `UsdGeom.BBoxCache`, authored mesh `extent`, and actual transformed mesh points:

1. Tiny basket: `basket/040600389fdab577a5376c28e6c5eb15`
2. Blank basket: `basket/6ae01f7e1ba19fc58a6f9d0b1102c3d1`
3. Normal control: `backpack/7e66385cf06355dd76b9340ec9bdfaee`

Key findings:

- Tiny basket authored/default bbox diag: `636.184620`
- Tiny basket actual transformed points union diag: `62.323327`
- Blank basket authored/default bbox diag: `4239.049048`
- Blank basket actual transformed points union diag: `42.769519`
- Normal backpack authored/default bbox diag: `76.540939`
- Normal backpack actual transformed points union diag: `76.540939`

The bad basket meshes have authored `extent` values that are much larger than their actual transformed points. Example from tiny basket:

- `/Root/Instance/Group_00/Component_1` actual world point size: `[32.348499, 25.0321, 45.9182]`
- Same mesh authored local extent size: `[459.181992, 323.485001, 250.320999]`

Example from blank basket:

- `/Root/Instance/Group_00/Component_0` actual world point size: `[31.20004, 18.565521, 16.817959]`
- Same mesh authored local extent size: `[4627.720215, 2494.51001, 2753.715759]`

Material binding warnings appeared on both broken and normal control assets, so they are not sufficient to explain the tiny/blank behavior.

## Root Cause

The renderer calls `compute_bbox()` in `src/render_usd/utils/usd_utils/prim_utils.py`, which uses:

```python
imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
```

For these basket assets, USD bounding-box computation is driven by stale or mis-scaled authored mesh `extent` metadata. The resulting bbox is 10x to 100x larger than the actual visible mesh points.

The camera distance is then derived from this oversized bbox:

```python
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
```

This places the camera too far away. The observed tiny/blank PNGs are consistent with the actual point bounds divided by the oversized bbox-derived camera distance.

## Result

Diagnosis is complete enough to avoid further guessing:

- The problem is not primarily a missing-output DLC issue; all four-view outputs exist.
- The problem is not yet proven to be material or MDL related.
- The immediate technical root cause for the tiny/blank examples is invalid authored USD `extent` metadata causing oversized bbox-based camera placement.

No code changes were made because the requested scope was diagnosis only.

## Follow-Up Options

If implementation is requested later, likely options are:

- Add a robust bbox path that recomputes bounds from transformed mesh `points` when authored extent and point-derived bounds differ substantially.
- Preprocess/fix bad USD `extent` attributes in the asset dataset, then rerender affected assets.
- Keep renderer unchanged and mark affected assets as low-quality for downstream filtering.
