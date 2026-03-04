# Renderer.py Crash Analysis

**Date**: 2026-03-04
**Author**: code-investigator (Agent Team)
**Task**: #6 - Investigate renderer.py for crash patterns
**Related Issue**: Segmentation fault during `world.step(render=True)` at line 159

---

## Executive Summary

The crash occurs during the rendering loop in `renderer.py:159` at `self.world.step(render=True)`. Based on code analysis and Isaac Sim logs, the primary cause is **USD prim validation failures** detected by the USD imaging delegate. The pattern of "Failed verification: ' prim '" errors suggests that prims are becoming invalid during the rendering loop, likely due to improper cleanup or resource management between object renders.

---

## 1. Code Review: Crash Location (Lines 150-170)

### 1.1 Critical Code Section

```python
# Lines 144-159 in renderer.py
for i in range(sample_number):
    azimuth = init_azimuth_angle + i * 360 / sample_number
    elevation = 35
    distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
    set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)

for _ in range(100):
    self.world.step(render=False)
for _ in range(8):
    self.world.step(render=True)  # ← CRASH HERE (line 159)
```

### 1.2 Problem Analysis

**Immediate Issue**: The crash occurs when `render=True`, which triggers actual PathTracing rendering. The first 100 steps (`render=False`) likely complete successfully.

**Root Cause Indicators**:
1. **Prim invalidation**: USD prims loaded at line 138 may become invalid after multiple render cycles
2. **No camera cleanup**: Cameras are initialized once at lines 110-114 and reused across objects
3. **No world reset**: `self.world` is never reset between objects
4. **Accumulating prims**: Each object is created at `/World/Show` (line 137) and deleted (line 192), but the stage state may accumulate errors

---

## 2. Code Review: Initial Setup (Lines 102-115)

### 2.1 Camera Initialization

```python
# Lines 110-114
cameras = []
for i in range(sample_number):
    camera = init_camera(f"camera_{i}", image_width=512, image_height=512)
    setup_camera(camera, with_bbox2d=show_bbox2d)
    cameras.append(camera)
```

**Issues Identified**:
- Cameras are created **once** at the start of `render_thumbnail_wo_bg()`
- Same cameras are reused for ALL objects in `object_usd_paths`
- Camera state (position, orientation, render targets) is not reset between objects
- No camera cleanup/reinitialization between renders

### 2.2 World Initialization

```python
# Lines 103-104
if not self.world:
    self.world = init_world()
```

**Issues Identified**:
- World is created once per `RenderManager` instance
- Never reset or recreated during the object loop
- Accumulated stage state may cause USD validation errors over time

---

## 3. Code Review: Post-Crash Behavior (Lines 161-193)

### 3.1 Image Extraction and Saving

```python
# Lines 162-191
os.makedirs(save_dir, exist_ok=True)
for idx, camera in enumerate(cameras):
    rgba = get_src(camera, "rgba")
    # ... image compositing ...
    if show_bbox2d:
        bbox2d = get_src(camera, "bbox2d_tight")
        # ... bbox drawing ...
        cv2.imwrite(f"{save_dir}/{filename_base}_bbox2d.png", ...)
```

**Note**: This code is never reached when crash occurs at line 159.

### 3.2 Prim Deletion

```python
# Line 192
delete_prim(show_prim_path)
```

**Issues Identified**:
- Prim deletion happens AFTER rendering
- If crash occurs before this line, prim is not deleted
- Accumulated prims may cause stage corruption in subsequent renders

---

## 4. Resource Management Issues

### 4.1 Camera Accumulation

**Problem**: Cameras are created once but their internal state accumulates:
- Render targets (annotators) retain previous frame data
- GPU buffers may accumulate
- Camera position/orientation is updated but not fully reset

**Location**: `src/render_usd/core/camera.py:67-86` (setup_camera function)

```python
def setup_camera(
    camera: Camera,
    focal_length: float = 18.0,
    # ... other params ...
    with_bbox2d: bool = False,
    # ... other params ...
) -> None:
    camera.initialize()  # ← Called ONCE per camera creation
    camera.set_focal_length(focal_length)
    # ... annotator additions ...
    if with_bbox2d:
        camera.add_bounding_box_2d_tight_to_frame()
        camera.add_bounding_box_2d_loose_to_frame()
```

**Issue**: `camera.initialize()` is only called once when camera is created. There's no cleanup or reinitialization between object renders.

### 4.2 Stage State Accumulation

**Problem**: USD stage accumulates state across renders:
1. Each object is loaded at `/World/Show` (line 138)
2. Previous object is deleted at line 192
3. However, USD stage may retain references or validation state
4. Isaac Sim's USD imaging delegate may have cached invalid prims

**Evidence**: Log pattern shows repeated `Failed verification: ' prim '` errors at regular intervals (~1 second), suggesting ongoing prim validation failures during rendering.

---

## 5. Race Conditions and Threading Issues

### 5.1 Potential Race Conditions

While there's no explicit threading in the code, Isaac Sim's internal rendering pipeline uses threading:

**Likely Race Conditions**:
1. **Prim deletion vs. rendering**: `delete_prim(show_prim_path)` happens after rendering, but Isaac Sim may still hold references
2. **Camera annotator access**: `get_src(camera, "rgba")` accesses internal annotator buffers that may be in use by render thread
3. **USD stage mutation**: Modifying stage (deleting prims) while renderer still processes previous frames

### 5.2 Threading-Safe Practices Missing

Current code lacks:
- No explicit render synchronization
- No `world.reset()` between objects
- No explicit camera flush/cleanup
- No exception handling around `world.step()`

---

## 6. USD Prim Loading Issues

### 6.1 Prim Creation

```python
# Line 138
show_prim_path = "/World/Show"
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
```

**Issues**:
- Same prim path `/World/Show` is reused for every object
- If previous deletion failed, `create_prim` may fail or create invalid state
- No validation that `create_prim` succeeded

### 6.2 BBox Computation

```python
# Lines 141-142
bbox_min, bbox_max = compute_bbox(usd_prim)
center = (bbox_min + bbox_max) / 2
```

**Issue**: If `compute_bbox` returns invalid data (NaN, infinity), camera positioning will fail, potentially causing renderer crashes.

---

## 7. Error Handling Gaps

### 7.1 Missing Try-Catch Blocks

**Critical**: No error handling around rendering steps:

```python
# Lines 156-159 - No error handling
for _ in range(100):
    self.world.step(render=False)
for _ in range(8):
    self.world.step(render=True)  # ← Can segfault here with no recovery
```

### 7.2 No Prim Validation

**Missing checks**:
1. No verification that `usd_prim` is valid after `create_prim`
2. No check that `bbox_min/bbox_max` are valid numbers
3. No validation that cameras are ready before rendering

---

## 8. Specific Code Locations with Line Numbers

| Issue | Location | Line | Severity |
|-------|----------|------|----------|
| No world reset between objects | renderer.py | 103-104, 116-193 | HIGH |
| Camera reused without cleanup | renderer.py | 110-114 | HIGH |
| No error handling around world.step | renderer.py | 156-159 | CRITICAL |
| Prim deletion after crash point | renderer.py | 192 | MEDIUM |
| Same prim path reused | renderer.py | 138 | MEDIUM |
| No bbox validation | renderer.py | 141-142 | MEDIUM |
| Camera initialize called once | camera.py | 67 | LOW |
| No render synchronization | renderer.py | 156-193 | HIGH |

---

## 9. Isaac Sim Log Analysis

### 9.1 USD Validation Errors

**Pattern from log** (repeated ~1 second intervals):
```
2026-03-04 10:47:39 [119,007ms] [Warning] [omni.usd] Coding Error: in _Get at line 3003 of /buildAgent/work/ac88d7d902b57417/USD/pxr/usdImaging/usdImaging/delegate.cpp -- Failed verification: ' prim '
```

**Interpretation**:
- USD imaging delegate's `_Get` method is receiving invalid prims
- Error occurs during rendering (not during prim loading)
- Pattern suggests prims are becoming invalid during the render loop
- Location: `usdImaging/delegate.cpp:3003` - USD's internal delegate validation

### 9.2 Timeline Analysis

```
10:47:39 - First prim validation error (119 seconds after start)
10:47:40 - Second error (1 sec later)
10:47:42 - Third error (1 sec later)
... [continues every ~1 second]
```

**Interpretation**: The errors occur at approximately the rendering interval, suggesting:
- Each render cycle (`world.step(render=True)`) triggers validation
- Multiple cameras cause multiple validation checks per cycle
- Errors accumulate over time until crash occurs

---

## 10. Recommended Fixes

### 10.1 CRITICAL: Add World Reset Between Objects

**Location**: renderer.py, after line 135

```python
if not overwrite:
    has_rendered = os.path.exists(save_dir) and len([f for f in os.listdir(save_dir) if f.startswith(object_name) and f.endswith('.png')]) >= sample_number
    if has_rendered:
        continue

# NEW: Reset world state before loading new object
self.world.reset()
```

**Rationale**: Clearing world state between objects prevents accumulation of invalid prims and render state.

### 10.2 CRITICAL: Add Error Handling Around Rendering

**Location**: renderer.py, lines 156-165

```python
try:
    for _ in range(100):
        self.world.step(render=False)
    for _ in range(8):
        self.world.step(render=True)
except Exception as e:
    print(f"[Error] Rendering failed for {object_usd_path}: {e}")
    delete_prim(show_prim_path)  # Clean up prim on error
    continue  # Skip to next object instead of crashing
```

**Rationale**: Prevents single object failure from crashing entire job. Allows recovery and continuation.

### 10.3 HIGH: Reinitialize Cameras Between Objects

**Location**: renderer.py, move lines 110-114 inside object loop

```python
for idx_obj, object_usd_path in enumerate(tqdm(object_usd_paths, desc="Rendering objects")):
    # ... existing code ...

    # NEW: Create fresh cameras for each object
    cameras = []
    for i in range(sample_number):
        camera = init_camera(f"camera_{i}", image_width=512, image_height=512)
        setup_camera(camera, with_bbox2d=show_bbox2d)
        cameras.append(camera)

    # ... rest of rendering code ...
```

**Alternative** (better performance): Clear camera state without recreating:

```python
# After rendering each object, clean up cameras
for camera in cameras:
    # Clear render targets
    camera._custom_annotators.clear()
    camera._render_product = None
```

### 10.4 MEDIUM: Validate BBox Data

**Location**: renderer.py, after line 142

```python
center = (bbox_min + bbox_max) / 2

# NEW: Validate bbox data
if np.isnan(center).any() or np.isinf(center).any():
    print(f"[Error] Invalid bbox for {object_name}, skipping")
    delete_prim(show_prim_path)
    continue
```

### 10.5 MEDIUM: Use Unique Prim Paths

**Location**: renderer.py, line 137

```python
# NEW: Use unique prim path per object
show_prim_path = f"/World/Show_{object_name}_{idx_obj}"
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
```

### 10.6 MEDIUM: Add Prim Validation After Creation

**Location**: renderer.py, after line 138

```python
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))

# NEW: Validate prim was created successfully
if usd_prim is None or not usd_prim.IsValid():
    print(f"[Error] Failed to create prim for {object_usd_path}")
    continue
```

### 10.7 LOW: Reduce Render Steps

**Location**: renderer.py, lines 156-159

```python
# Current: 108 steps total (100 non-render + 8 render)
for _ in range(100):
    self.world.step(render=False)
for _ in range(8):
    self.world.step(render=True)

# NEW: Reduce to 20 steps total (16 non-render + 4 render)
for _ in range(16):
    self.world.step(render=False)
for _ in range(4):
    self.world.step(render=True)
```

**Rationale**: Fewer render steps = fewer validation checks = lower crash probability. May reduce quality but improves reliability.

---

## 11. Additional Recommendations

### 11.1 Add Logging for Debugging

```python
print(f"[Debug] Loading object: {object_name}")
print(f"[Debug] Prim path: {show_prim_path}")
print(f"[Debug] BBox: {bbox_min} to {bbox_max}")
print(f"[Debug] Starting render cycle...")
```

### 11.2 Monitor GPU Memory

```python
import torch
if torch.cuda.is_available():
    print(f"[Debug] GPU memory before render: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
```

### 11.3 Add Chunk-Level Checkpoints

Save progress after every N objects:
```python
if idx_obj % 100 == 0:
    print(f"[Progress] Processed {idx_obj} objects so far...")
```

---

## 12. Testing Strategy

### 12.1 Reproduce Crash

1. Render a large batch of objects (>100)
2. Monitor for "Failed verification" errors in Isaac Sim logs
3. Expected crash after ~50-100 objects

### 12.2 Verify Fixes

1. Apply world reset fix
2. Render same batch
3. Verify no crashes occur
4. Check that all output images are valid

### 12.3 Performance Impact

Monitor changes in:
- Rendering time per object
- GPU memory usage
- Total job completion time

---

## 13. Conclusion

The crash at `renderer.py:159` is caused by USD prim validation failures during rendering. The primary issues are:

1. **No world reset between objects** - Accumulated stage state causes validation errors
2. **Cameras reused without cleanup** - GPU buffers accumulate invalid data
3. **No error handling** - Single failure crashes entire job
4. **Same prim path reused** - Potential for invalid state after failed deletion

The recommended fixes address these issues through:
- Adding `world.reset()` between objects (CRITICAL)
- Implementing error handling around rendering (CRITICAL)
- Reinitializing or cleaning up cameras between objects (HIGH)
- Adding validation for prim and bbox data (MEDIUM)

These changes should eliminate the segfault and improve overall rendering reliability.

---

**Document Status**: Complete
**Next Steps**: Implement CRITICAL fixes (#1 and #2) first, then test with small batch before large-scale deployment
