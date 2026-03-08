# Git History Analysis: Camera Distance & View-Related Changes

**Date**: 2026-03-08
**Agent**: git-historian
**Purpose**: Trace all git commits that could affect camera distance, bbox calculation, or view composition.

---

## Summary of Findings

**The distance formula (`np.linalg.norm(bbox_max - bbox_min) * 1.0`) has NEVER changed throughout the entire git history.** The multiplier has always been `1.0` (i.e., diagonal of bounding box).

However, one significant change was introduced in commit `a31f3ee` that **clamps** the distance to `[0.1, 100.0]`, which could affect very large or very small objects.

The HDRI lighting change in commit `3c294a3` switched from RGB to RGBA compositing, which changes the visual appearance of renders (dark gray background instead of environment-lit background) but does NOT change the camera distance or framing.

---

## Files Analyzed

| File | Commits | Camera-relevant changes? |
|---|---|---|
| `src/render_usd/core/camera.py` | 3 commits | No distance/elevation changes |
| `src/render_usd/core/renderer.py` | 12 commits | **Yes** - distance clamp added |
| `src/render_usd/core/scene.py` | 3 commits | No (lighting only) |
| `src/render_usd/utils/usd_utils/prim_utils.py` | 1 commit (initial) | No changes since initial |

---

## Detailed Commit Analysis

### Commit 1: `8db89e0` — Initial commit (2026-01-12)

**Original distance formula in `renderer.py`:**

```python
# render_thumbnail_wo_bg:
bbox_min, bbox_max = compute_bbox(usd_prim)
center = (bbox_min + bbox_max) / 2
# distance computed INSIDE the per-view loop:
for i in range(sample_number):
    azimuth = init_azimuth_angle + i * 360 / sample_number
    elevation = 35
    distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
    set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)

# render_thumbnail_with_bg:
bbox_min, bbox_max = compute_bbox(mesh_prim)
center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
for i in range(sample_number):
    azimuth = 30 + i * 360 / (sample_number / 2)
    elevation = 35 if i < sample_number / 2 else -35
    set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
```

**Key parameters at initial commit:**
- Distance multiplier: `1.0`
- Elevation: `35` degrees (wo_bg), `35/-35` degrees (with_bg)
- Azimuth: `0, 90, 180, 270` degrees (wo_bg with default `init_azimuth_angle=0`)
- Camera resolution: `512x512` (wo_bg), `600x450` (with_bg)
- Simulation steps: 100 (non-render) + 8 (render)
- No distance clamping
- No bbox validation

**`compute_bbox` in `prim_utils.py`:**
```python
def compute_bbox(prim: Usd.Prim) -> np.ndarray:
    imageable = UsdGeom.Imageable(prim)
    time = Usd.TimeCode.Default()
    bound = imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
    bound_range = bound.ComputeAlignedBox()
    bbox_min = bound_range.min
    bbox_max = bound_range.max
    bound_range = np.array([bbox_min, bbox_max])
    return bound_range
```
This function has **never been modified** since the initial commit.

---

### Commit 2: `9e459aa` / `570796b` — Refactor: Modularize core logic (2026-01-12)

**Changes to camera.py:**
- Moved from `utils/common_utils/sim_utils.py` to `core/camera.py`
- Removed unrelated functions (world init, semantic setup)
- Cleaned up debug print statements
- Changed `XFormPrim | np.ndarray` to `Union[XFormPrim, np.ndarray]` (Python 3.9 compat)
- Fixed `set_camera_rational_polynomial(camera, *camera_params)` to `**camera_params`
- Commented out broken `get_world_corners_from_bbox3d` call

**Impact on distance/view: NONE.** The `set_camera_look_at` function is completely unchanged:
```python
def set_camera_look_at(camera, target, distance=0.4, elevation=90.0, azimuth=0.0):
    # ... spherical coordinate math unchanged
    offset_x = distance * math.cos(elev_rad) * math.cos(azim_rad)
    offset_y = distance * math.cos(elev_rad) * math.sin(azim_rad)
    offset_z = distance * math.sin(elev_rad)
    camera_position = target_position + np.array([offset_x, offset_y, offset_z])
    rot = R.from_euler("xyz", [0, elevation, azimuth - 180], degrees=True)
```

---

### Commit 3: `7ff169b` — Add inplace rendering support (2026-01-13)

**Changes to renderer.py:**
- `thumbnail_wo_bg_dir` changed from `Path` to `Optional[Path]`
- Added inplace rendering: if `thumbnail_wo_bg_dir` is None, save in same directory as USD file
- Added nested asset scanning support

**Impact on distance/view: NONE.** Distance formula unchanged.

---

### Commit 4: `b2ea605` — Add semantic naming (view mode) (date unknown)

**Changes to renderer.py:**
- Added `naming_style="index"` parameter
- Added view name mapping: `{0: "front", 1: "left", 2: "back", 3: "right"}`
- Added comments explaining azimuth-to-view mapping
- Changed `elevation = 35` to `elevation = 35  # Fixed elevation angle (high angle shot)` (comment only)

**Impact on distance/view: NONE.** Distance formula unchanged. Only output filenames changed.

---

### Commit 5: `f0f4777` — Add render_custom command (date unknown)

**Changes to renderer.py:**
- `thumbnail_wo_bg_dir` changed from `Optional[Path]` to `Optional[Union[Path, List[Path]]]`
- Added per-object output directory support

**Impact on distance/view: NONE.** Distance formula unchanged.

---

### Commit 6: `3c294a3` — HDRI environment lighting (2026-03-04)

**Changes to camera.py:**
- Added `get_rgba()` function
- Added `"rgba"` type to `get_src()`

**Changes to scene.py:**
- Added HDRI texture search (Isaac Sim bundled `photo_studio_01_4k.hdr`)
- Changed DomeLight intensity from `1000` to `1500` (with HDRI) or kept `1000` (without)
- Added `backgroundZeroAlpha` settings for transparent background
- Added `carb.settings` for alpha compositing

**Changes to renderer.py:**
- Changed from `get_src(camera, "rgb")` to RGBA compositing:
```python
# NEW (HDRI commit):
rgba = get_src(camera, "rgba")
if rgba is not None and rgba.shape[2] == 4:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)  # dark gray RGB(40,40,40)
    rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
else:
    rgb = get_src(camera, "rgb")
```

**Impact on distance/view: NONE directly.** The camera distance, elevation, azimuth, and bbox calculation are completely unchanged. However, the visual appearance changes significantly:
- Background changes from whatever the environment provides to dark gray (RGB 40,40,40)
- Lighting changes from DomeLight 1000 intensity to HDRI 1500 intensity
- This could make objects appear different in brightness/contrast, but the framing/zoom is identical

---

### Commit 7: `a31f3ee` — **DLC crash fix (2026-03-04) — MOST SIGNIFICANT**

This is the only commit that materially changes the distance calculation pipeline.

**Before (all prior commits):**
```python
bbox_min, bbox_max = compute_bbox(usd_prim)
center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
set_camera_look_at(cameras[i], center, azimuth=..., elevation=35, distance=distance)
```

**After (a31f3ee):**
```python
bbox_min, bbox_max = compute_bbox(usd_prim)

# NEW: Validate bounding box
if np.any(np.isnan(bbox_min)) or np.any(np.isnan(bbox_max)):
    print(f"[Error] Invalid bounding box (NaN) for {object_name}, skipping")
    delete_prim(show_prim_path)
    continue
if np.any(np.isinf(bbox_min)) or np.any(np.isinf(bbox_max)):
    print(f"[Error] Invalid bounding box (Inf) for {object_name}, skipping")
    delete_prim(show_prim_path)
    continue

center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0

# NEW: Clamp distance
distance = np.clip(distance, 0.1, 100.0)

set_camera_look_at(cameras[i], center, azimuth=..., elevation=35, distance=distance)
```

**Changes introduced:**
1. **Bbox NaN/Inf validation** — Objects with invalid bounding boxes are now skipped. Previously, they would produce garbage camera positions.
2. **Distance clamping to [0.1, 100.0]** — This is the ONLY change that could affect rendered output for valid objects:
   - Objects with bbox diagonal > 100.0 units would now render with `distance=100.0` (closer than before)
   - Objects with bbox diagonal < 0.1 units would now render with `distance=0.1` (farther than before)
   - Objects with diagonal in [0.1, 100.0] are **completely unaffected**

**Also notable in this commit:**
- Distance was moved from inside the per-view loop to outside (minor refactor, no behavioral change since bbox_min/bbox_max don't change per view)
- Error handling wraps the rendering steps in try/except
- `overwrite` flag added (affects skip logic, not distance)

---

### Commits 8-10: `df6a2a2`, `0e2cd49`, `8c1eb14` — Exception handling and bug fixes

**Impact on distance/view: NONE.** These only changed `except:` to `except Exception:` and fixed a duplicate code block.

---

## Complete Change Timeline for Distance Formula

| Date | Commit | Distance Formula | Change |
|---|---|---|---|
| 2026-01-12 | `8db89e0` | `np.linalg.norm(bbox_max - bbox_min) * 1.0` | Initial |
| 2026-01-12 | `9e459aa` | Same | No change |
| 2026-01-13 | `7ff169b` | Same | No change |
| varies | `b2ea605` | Same | No change |
| varies | `f0f4777` | Same | No change |
| 2026-03-04 | `3c294a3` | Same | No change (HDRI lighting only) |
| **2026-03-04** | **`a31f3ee`** | Same + `np.clip(distance, 0.1, 100.0)` | **Distance clamping added** |
| 2026-03-05 | `df6a2a2` | Same | No change |
| 2026-03-05 | `0e2cd49` | Same | No change |

---

## Key Findings

1. **The base distance formula has NEVER changed**: `distance = np.linalg.norm(bbox_max - bbox_min) * 1.0` — the multiplier is and has always been `1.0`.

2. **`compute_bbox` in `prim_utils.py` has NEVER been modified** since the initial commit. It uses `UsdGeom.Imageable.ComputeWorldBound()` which is a standard USD API.

3. **`set_camera_look_at` in `camera.py` has NEVER been modified** in terms of its spherical coordinate math. The function signature and logic are identical from initial commit to HEAD.

4. **The only distance-affecting change** is the `np.clip(distance, 0.1, 100.0)` clamp introduced in `a31f3ee`. This would only affect objects with bbox diagonal outside [0.1, 100.0] range.

5. **Camera parameters unchanged**: elevation=35, resolution=512x512 (wo_bg), focal_length=18.0 (default), simulation steps=100+8. None of these have ever changed.

6. **No scale/transform changes**: `create_prim(show_prim_path, position=(0,0,0), scale=(1,1,1), usd_path=...)` — the scale has always been `(1,1,1)`.

7. **If rendered images look different (closer/farther)**, the cause is NOT in the git history of this codebase. Possible external causes:
   - Different USD files being rendered (different bbox sizes)
   - Different `stage_units_in_meters` in the USD files
   - Different material/texture loading affecting perceived size
   - The distance clamp affecting objects at the extremes
   - The HDRI compositing making background different (visual difference, not zoom)

---

## Recommendations for Further Investigation

If the camera distance appears to have changed for specific objects:
1. Check if the object's bbox diagonal falls outside [0.1, 100.0] — the clamp would be the cause
2. Check if the USD file's `metersPerUnit` or transform hierarchy has changed
3. Compare the exact bbox values (`compute_bbox` output) for old vs new renders
4. The HDRI+alpha compositing change makes the background dark gray, which can create an optical illusion of different framing even when the object is identically positioned
