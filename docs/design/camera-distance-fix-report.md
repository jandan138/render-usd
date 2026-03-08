# Camera Distance Bug Fix Report

> Date: 2026-03-08
> Status: **FIXED**

## Problem

New renderings (2026-03-05) showed objects as extreme close-ups, filling the entire frame. Old renderings (2026-01-19) correctly showed objects at ~60-65% frame occupancy.

## Root Cause

**`np.clip(distance, 0.1, 100.0)` in `renderer.py:228`** (introduced in commit `a31f3ee`).

The distance calculation uses the bounding box diagonal:
```python
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
```

For the test asset (bed `0a85b986de35ccfdec7c686d791fd747`):
- `bbox_min = [-97.83, -111.92, -45.00]`
- `bbox_max = [97.83, 111.92, 45.00]`
- `diagonal = 310.63` (correct distance)
- After `np.clip`: `distance = 100.0` (truncated to ~32% of correct value)

The upper bound of 100.0 was too aggressive. GRScenes assets use centimeter-scale coordinates where bbox diagonals commonly exceed 100 for furniture items.

## Investigation Process

### Initial Suspects (from prior analysis)
1. **commit a31f3ee**: `world.reset()` added to render loop
2. **commit 3c294a3**: HDRI lighting + `backgroundZeroAlpha` + alpha compositing

### Debug Approach
Added environment variable switches:
- `RENDER_SKIP_LOOP_RESET=1`: Skip per-loop `world.reset()`
- `RENDER_SKIP_ALPHA=1`: Skip `backgroundZeroAlpha` + alpha compositing

### Test Results (A/B/C)
Three tests were run with the bed asset:
- **Test A (Baseline)**: Close-up, object fills frame
- **Test B (Skip reset)**: Nearly identical to A — `world.reset()` is NOT the cause
- **Test C (Skip alpha)**: Nearly identical to A (different background color) — alpha is NOT the cause

All three tests showed the same "too close" problem, confirming **neither suspected change was the root cause**.

### Actual Discovery
Adding `[DEBUG-CAM]` logging revealed the true culprit:
```
distance=100.0000 (clamped by np.clip!)
```

The `np.clip(distance, 0.1, 100.0)` was also introduced in commit `a31f3ee` as part of "preventing numerical instability", but it silently truncated distances for large objects.

### Fix Verification (Test D)
After removing the upper bound:
```
distance=310.6278 (correct, unclamped)
```

Output image shows complete bed at proper ~60-65% frame occupancy — matching the old (January) renderings.

## Fix Applied

**File: `src/render_usd/core/renderer.py`**

Before:
```python
distance = np.clip(distance, 0.1, 100.0)
```

After:
```python
distance = max(distance, 0.1)
```

The minimum clamp (0.1) is retained to prevent division-by-zero / camera-at-origin issues for degenerate bounding boxes. The upper bound is removed entirely — there is no valid reason to limit camera distance for legitimately large objects.

## Cleanup

Removed all debug instrumentation:
1. `renderer.py`: Removed `RENDER_SKIP_LOOP_RESET` env var check, `[DEBUG-CAM]` print, `RENDER_SKIP_ALPHA` env var check
2. `scene.py`: Removed `RENDER_SKIP_ALPHA` env var check around `backgroundZeroAlpha` settings

## Key Lesson

The `np.clip` was introduced in a commit focused on crash prevention (DLC shutdown fixes). The upper bound of 100.0 assumed meter-scale coordinates, but GRScenes assets use centimeter-scale where bbox diagonals of 100-500+ are common for furniture. This silent truncation had no error output, making it difficult to detect without explicit logging of the distance values.
