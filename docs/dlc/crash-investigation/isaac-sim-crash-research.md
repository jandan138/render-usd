# Isaac Sim Crash Research Report

**Date**: 2026-03-04
**Researcher**: isaac-researcher agent
**Task**: Research Isaac Sim crash causes and propose solutions

---

## Executive Summary

This document documents research into common causes of Isaac Sim segmentation faults and crashes during USD rendering, with a focus on the render-usd pipeline. The web search was not available (likely due to network restrictions or API issues), so this analysis is based on:
1. Code inspection of the render-usd pipeline
2. Common Isaac Sim rendering patterns
3. Known best practices for Isaac Sim batch rendering
4. Analysis of potential failure points in the current implementation

---

## Potential Crash Scenarios Analysis

### 1. Memory/GPU Resource Exhaustion

**Location**: `src/render_usd/core/renderer.py` (lines 156-159)

**Code Pattern**:
```python
for _ in range(100):
    self.world.step(render=False)
for _ in range(8):
    self.world.step(render=True)
```

**Analysis**:
- The pipeline renders 4 camera views per object (512x512 resolution)
- Each render pass creates RGBA images and annotator data (distance, bbox2d_tight, bbox2d_loose)
- In batch mode, hundreds or thousands of USD files are processed sequentially
- **Risk**: GPU memory accumulation if resources are not properly cleaned up

**Potential Issues**:
- Camera annotators accumulate data in memory
- USD stages loaded via `create_prim()` and `add_reference_to_stage()` may not be fully cleared
- PathTracing renderer is computationally expensive (CONFIG uses PathTracing)

**Recommendations**:
1. Add explicit camera cleanup between objects
2. Clear USD stage references after each render
3. Consider memory monitoring and periodic GC
4. Reduce render steps if possible

---

### 2. USD File Corruption or Incompatible Formats

**Location**: `src/render_usd/core/renderer.py` (line 138)

**Code Pattern**:
```python
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
```

**Analysis**:
- The pipeline loads USD files directly without validation
- GRScenes-100 dataset contains assets from various sources
- **Risk**: Corrupted or malformed USD files can cause Isaac Sim to crash during loading

**Potential Issues**:
- USD files with invalid material bindings
- Files with unsupported geometry types
- Missing or broken MDL material references
- Malformed USD composition arcs

**Recommendations**:
1. Add USD file validation before loading
2. Try-catch around `create_prim()` and `add_reference_to_stage()`
3. Log problematic files for manual inspection
4. Skip files that fail to load gracefully

---

### 3. Camera Setup and Simulation Step Issues

**Location**: `src/render_usd/core/renderer.py` (lines 144-159, camera.py)

**Code Pattern**:
```python
azimuth = init_azimuth_angle + i * 360 / sample_number
elevation = 35
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
```

**Analysis**:
- Camera position depends on computed bounding box
- **Risk**: Invalid bbox computation can lead to invalid camera positions
- Extremely large or small distances can cause numerical instability

**Potential Issues**:
- `compute_bbox()` may return invalid values for certain geometries
- Distance calculation: `np.linalg.norm(bbox_max - bbox_min) * 1.0` can be problematic for:
  - Empty geometry (distance = 0)
  - Extremely large geometry (camera too far)
  - NaN/Inf values in bbox

**Recommendations**:
1. Add validation for bbox values before camera positioning
2. Clamp distance to reasonable range (e.g., 0.1 to 100 meters)
3. Check for NaN/Inf values
4. Add error handling around camera setup

---

### 4. PathTracing Renderer Issues

**Location**: `src/render_usd/cli.py` (line 9)

**Code Pattern**:
```python
CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}
```

**Analysis**:
- PathTracing is the most computationally expensive renderer
- **Risk**: PathTracing can fail on certain material/lighting configurations

**Potential Issues**:
- MDL material resolution failures (already addressed via carb.settings)
- HDRI texture loading issues
- Lighting configuration conflicts
- Anti-aliasing setting may be too aggressive for headless mode

**Recommendations**:
1. Consider using RayTracing renderer as fallback
2. Reduce anti-aliasing to 2 or test without it
3. Add material loading validation
4. Log lighting setup for debugging

---

### 5. MDL Material Resolution Failures

**Location**: `src/render_usd/core/scene.py`, `cli.py`

**Current Implementation**:
- Uses MDL search paths via `carb.settings.get_settings().set_string_array("/app/mdl/additionalSystemPaths", ...)`
- Fallback to `MDL_SYSTEM_PATH` environment variable

**Analysis**:
- GRScenes assets use relative MDL paths
- Material resolution failures can cause rendering to fail
- **Risk**: Segmentation fault when Isaac Sim tries to render with invalid materials

**Potential Issues**:
- MDL files may be corrupted or incompatible
- MDL version mismatches
- Circular dependencies in material definitions

**Recommendations**:
1. Add MDL material validation before rendering
2. Try-catch around material loading
3. Consider using a default material as fallback
4. Log which MDL files are being used

---

### 6. HDRI Environment Loading Issues

**Location**: `src/render_usd/core/scene.py` (lines 43-76)

**Code Pattern**:
```python
dome_light = UsdLux.DomeLight.Define(stage, "/World/default_dome_light")
dome_light.CreateTextureFileAttr(hdri_path)
settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
```

**Analysis**:
- HDRI texture path is hardcoded to Isaac Sim installation
- **Risk**: HDRI file may not exist or be corrupted

**Potential Issues**:
- HDRI path may be invalid in DLC environment
- HDRI file corruption
- Texture loading failures causing crashes

**Recommendations**:
1. Add validation that HDRI file exists before loading
2. Provide fallback to solid color DomeLight
3. Consider bundling a simple HDRI with the project
4. Log HDRI loading status

---

### 7. Annotator Data Access Issues

**Location**: `src/render_usd/core/camera.py` (lines 92-197)

**Code Pattern**:
```python
def get_bounding_box_2d_tight(camera: Camera) -> tuple[np.ndarray, dict]:
    annotator = camera._custom_annotators["bounding_box_2d_tight"]
    annotation_data = annotator.get_data()
    bbox = annotation_data["data"]
    info = annotation_data["info"]
    return bbox, info["idToLabels"]
```

**Analysis**:
- Camera annotators are accessed via private `_custom_annotators` dictionary
- **Risk**: Accessing annotator data before rendering completes

**Potential Issues**:
- Annotator may not have data ready
- Dictionary key may not exist
- Data format may be unexpected

**Recommendations**:
1. Add validation that annotator exists before access
2. Check that data is not empty
3. Add try-catch around annotator data access
4. Consider using public API if available

---

### 8. DLC Environment Specific Issues

**Location**: `scripts/dlc/run_task.sh`

**Analysis**:
- DLC jobs run in containers with CPFS mounts
- **Risk**: Environment differences between dev and DLC

**Potential Issues**:
- Isaac Sim installation path differences
- GPU driver/version differences
- Missing dependencies in DLC environment
- Network issues accessing CPFS

**Recommendations**:
1. Log Isaac Sim version at startup
2. Validate GPU availability and memory
3. Add environment health checks
4. Ensure all dependencies are installed in conda environment

---

## Common Isaac Sim Crash Patterns (General Knowledge)

Based on general Isaac Sim usage patterns, the following are common crash causes:

### 1. Initialization Order Issues
- **Issue**: Importing `omni` or `pxr` before `SimulationApp` initialization
- **Status**: ✅ Handled correctly in current code (cli.py line 115)

### 2. Physics/Rendering Step Mismatch
- **Issue**: Calling `world.step()` with different `physics_dt` and `rendering_dt`
- **Status**: ⚠️ Both set to 0.01, but not validated across calls

### 3. Camera Cleanup
- **Issue**: Not properly destroying camera objects between renders
- **Status**: ❌ Cameras are reused but not explicitly cleaned up

### 4. Stage Cleanup
- **Issue**: Loading multiple USD stages without clearing old ones
- **Status**: ⚠️ Uses `delete_prim()` but stage may accumulate references

### 5. Material Reference Issues
- **Issue**: Material assignments with invalid MDL files
- **Status**: ⚠️ Handled via search paths but no validation

---

## Recommended Immediate Actions

### High Priority
1. **Add error handling around USD loading** (renderer.py line 138)
2. **Validate bbox before camera positioning** (renderer.py line 153)
3. **Add try-catch around world.step() calls** (renderer.py lines 156-159)
4. **Log which files are being processed** for crash identification

### Medium Priority
5. **Reduce simulation step counts** to minimize render time and memory usage
6. **Add memory monitoring** to detect resource exhaustion
7. **Implement camera cleanup** between renders
8. **Add USD file validation** before processing

### Low Priority
9. **Consider RayTracing renderer** as a fallback option
10. **Bundle HDRI texture** with project for consistency
11. **Add detailed logging** for debugging
12. **Implement per-file timeout** to prevent infinite hangs

---

## Code-Level Fixes

### Fix 1: Add USD Loading Error Handling

**File**: `src/render_usd/core/renderer.py`

```python
# Around line 138
try:
    usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
    set_prim_cast_shadow_true(usd_prim)
    add_update_semantics(usd_prim, semantic_label="instance", type_label="class")
    bbox_min, bbox_max = compute_bbox(usd_prim)
except Exception as e:
    print(f"[ERROR] Failed to load USD {object_usd_path}: {e}")
    print(f"[ERROR] Skipping this asset and continuing...")
    continue
```

### Fix 2: Validate Bounding Box

**File**: `src/render_usd/core/renderer.py`

```python
# After line 141
# Validate bbox values
if np.any(np.isnan(bbox_min)) or np.any(np.isnan(bbox_max)):
    print(f"[ERROR] Invalid bounding box (NaN) for {object_usd_path}")
    delete_prim(show_prim_path)
    continue
if np.any(np.isinf(bbox_min)) or np.any(np.isinf(bbox_max)):
    print(f"[ERROR] Invalid bounding box (Inf) for {object_usd_path}")
    delete_prim(show_prim_path)
    continue

center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
# Clamp distance to reasonable range
distance = np.clip(distance, 0.1, 100.0)
```

### Fix 3: Add Render Step Error Handling

**File**: `src/render_usd/core/renderer.py`

```python
# Around lines 156-159
try:
    for _ in range(100):
        self.world.step(render=False)
    for _ in range(8):
        self.world.step(render=True)
except Exception as e:
    print(f"[ERROR] Rendering failed for {object_usd_path}: {e}")
    print(f"[ERROR] Skipping this asset and continuing...")
    # Clean up
    try:
        delete_prim(show_prim_path)
    except:
        pass
    continue
```

### Fix 4: Add Memory Cleanup

**File**: `src/render_usd/core/renderer.py`

```python
# After line 192 (after saving images)
# Clean up resources
import gc
gc.collect()

# Optional: Force CUDA cache clear if needed
# import torch
# torch.cuda.empty_cache()
```

### Fix 5: Add Progress Logging

**File**: `src/render_usd/core/renderer.py`

```python
# Around line 136
print(f"[{idx_obj+1}/{len(object_usd_paths)}] Rendering: {object_usd_path}")
# ... rest of code
print(f"[{idx_obj+1}/{len(object_usd_paths)}] Completed: {object_name}")
```

---

## Testing Recommendations

1. **Single File Testing**: Test with individual USD files to isolate problematic assets
2. **Memory Monitoring**: Monitor GPU memory usage during batch rendering
3. **Log Analysis**: Review Isaac Sim logs at `miniconda/envs/render-usd/lib/python3.10/site-packages/omni/logs/Kit/Isaac-Sim/4.1/`
4. **Chunk Testing**: Run with smaller chunks to identify if crash is file-specific or resource-related
5. **Renderer Comparison**: Test with RayTracing vs PathTracing to see if renderer is the issue

---

## Further Investigation

Since web search was not available, consider:
1. Checking NVIDIA Isaac Sim GitHub issues for known crash patterns
2. Reviewing NVIDIA Isaac Sim documentation for batch rendering best practices
3. Contacting NVIDIA support for crash debugging
4. Analyzing core dumps from crashed jobs (if available)

---

## Conclusion

The most likely crash scenarios for the render-usd pipeline are:

1. **USD file corruption** causing crashes during asset loading
2. **Bounding box computation errors** leading to invalid camera positions
3. **Memory exhaustion** from processing many USD files without cleanup
4. **Material resolution failures** when MDL files are invalid

Implementing the recommended fixes, particularly error handling around USD loading and bbox validation, should significantly improve robustness. The medium-priority items (memory monitoring, camera cleanup) address potential long-running batch issues.

---

**Sources**:
- Code analysis of render-usd pipeline (renderer.py, scene.py, camera.py, cli.py)
- DLC job scripts (run_task.sh, submit_batch.py)
- Isaac Sim best practices documentation (not accessible via web search)
- Common Isaac Sim crash patterns (from general knowledge)

**Next Steps**: Implement the recommended fixes and monitor crash rates.
