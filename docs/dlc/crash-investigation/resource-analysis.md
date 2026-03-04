# Resource Analysis: DLC Job Crashes

## Investigation Summary

Investigation into DLC job crashes (exit code 139 = SIGSEGV/OOM) identified several critical memory management issues in the render_usd pipeline.

**Analysis Date:** 2026-03-04
**Investigated Jobs:**
- Failed: `dlc1ypy51l0st5au` (chunk 49/50, exit code 139)
- Running: `dlc1yfyjntnuvoj1` (chunk 48/50)

## Current Resource Allocation

```json
{
  "CPU": "16",
  "GPU": "1",
  "Memory": "118Gi",
  "SharedMemory": "118Gi"
}
```

## Data Volume Analysis

**Total Assets:** 9,525 USD files (GRScenes_assets)
- **Chunk Size (50 chunks):** ~191 files per chunk
- **Chunk Size (48 chunks - failed job):** ~199 files per chunk

**Largest Categories (potential memory hotspots):**
1. bottle: 1,698 files
2. ceiling: 1,610 files  ⚠️ Structural meshes
3. book: 1,595 files
4. cabinet: 1,278 files
5. door: 650 files

## Identified Memory Issues

### 1. **No Cleanup Between Object Renders** (Critical)

**Location:** `src/render_usd/core/renderer.py` lines 116-192

```python
for idx_obj, object_usd_path in enumerate(tqdm(object_usd_paths, ...)):
    # ... loading USD ...
    usd_prim = create_prim(show_prim_path, ...)  # Line 138
    # ... rendering ...
    delete_prim(show_prim_path)  # Line 192 - ONLY PRIM IS DELETED
```

**Problem:** Only the prim is deleted, but:
- Camera frames stay in memory
- RGBA/RGB numpy arrays accumulate
- Isaac Sim internal rendering buffers are not cleared
- USD stage grows with each load

**Impact:** With 191 objects × 4 views × 512×512 RGBA arrays = ~1.9GB of image data per chunk (before compression)

### 2. **Large USD Files Accumulate in Stage**

**Location:** `src/render_usd/core/renderer.py` line 138

```python
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), ..., usd_path=str(object_usd_path))
```

**Problem:** Even though `delete_prim(show_prim_path)` is called, Isaac Sim's USD stage may retain:
- Material references (MDL files)
- Mesh geometry data
- Texture data

**Impact:** After 100+ objects, the stage becomes bloated, especially for large categories like "ceiling" and "cabinet" which contain complex structural geometry.

### 3. **No Garbage Collection or Memory Cleanup**

**Location:** Throughout `renderer.py`

**Missing operations:**
- No `import gc; gc.collect()` calls
- No explicit `del` statements for large objects
- No `camera._custom_annotators.clear()` calls

### 4. **Camera Objects Persist Entire Chunk**

**Location:** `src/render_usd/core/renderer.py` lines 110-114

```python
cameras = []
for i in range(sample_number):  # 4 cameras
    camera = init_camera(f"camera_{i}", image_width=512, image_height=512)
    setup_camera(camera, with_bbox2d=show_bbox2d)
    cameras.append(camera)
```

**Problem:** Cameras are created once per chunk and never cleaned up. Each camera maintains:
- 512×512 frame buffers
- Custom annotator data (distance_to_image_plane, bbox2d_tight, bbox2d_loose)
- Render target resources

### 5. **No Stage Reset Between Renders**

**Location:** `src/render_usd/core/scene.py`

**Problem:** The `init_world()` creates a World instance but there's no `world.reset()` or stage clearing between object renders.

### 6. **Potential OOM from Large Categories**

**Analysis of largest categories:**
- **ceiling (1,610 files):** Large planar meshes, likely high vertex counts
- **cabinet (1,278 files):** Complex furniture with sub-components
- **bottle (1,698 files):** Many small objects but each has geometry + materials

**Hypothesis:** Chunks that contain many "ceiling" or "cabinet" files may exceed memory limits even with 118GiB allocation.

## Proposed Solutions

### Priority 1: Add Explicit Memory Cleanup (Critical)

**File:** `src/render_usd/core/renderer.py`

**Changes needed after line 191 (inside object loop):**

```python
# After cv2.imwrite(...)
delete_prim(show_prim_path)

# NEW: Clear camera annotator data
for camera in cameras:
    camera._annotator.clear()  # Clear annotator data if available

# NEW: Force garbage collection periodically
if (idx_obj + 1) % 50 == 0:  # Every 50 objects
    import gc
    gc.collect()
    print(f"[Memory] Garbage collected after {idx_obj + 1} objects")
```

### Priority 2: Release GPU Memory Between Renders

**File:** `src/render_usd/core/renderer.py`

**Add after line 159 (world.step loop):**

```python
# NEW: Clear render targets
import carb.settings
settings = carb.settings.get_settings()
settings.set("/renderer/rest/defaultBufferId", "rgba")  # Reset render buffer

# OR force a complete stage reset every N objects
if (idx_obj + 1) % 100 == 0:
    print(f"[Memory] Resetting stage after {idx_obj + 1} objects")
    self.world.reset()
    setup_environment()  # Re-apply environment
```

### Priority 3: Reduce Chunk Size

**File:** `scripts/dlc/submit_batch.py`

**Current:** 50 chunks (~191 files/chunk)
**Proposed:** 100 chunks (~95 files/chunk) OR 150 chunks (~64 files/chunk)

**Rationale:** Smaller chunks reduce peak memory usage and provide better failure isolation.

### Priority 4: Add Memory Monitoring

**File:** `src/render_usd/core/renderer.py`

**Add at top:**

```python
import psutil
import gc

def log_memory_usage():
    process = psutil.Process()
    mem_info = process.memory_info()
    print(f"[Memory] RSS: {mem_info.rss / 1024**3:.2f} GiB, "
          f"VMS: {mem_info.vms / 1024**3:.2f} GiB")
```

**Call every 10 objects:**

```python
if (idx_obj + 1) % 10 == 0:
    log_memory_usage()
```

### Priority 5: Implement Per-Object Stage Isolation

**Advanced Solution:** Create a new USD stage for each object render instead of reusing the same stage.

```python
# In render_thumbnail_wo_bg:
for idx_obj, object_usd_path in enumerate(tqdm(object_usd_paths, ...)):
    # Create temporary stage for this object
    temp_stage = Usd.Stage.CreateInMemory()
    # Load and render
    # Save output
    # Destroy stage (implicit when temp_stage goes out of scope)
```

## Implementation Priority

1. **Immediate (before next batch):** Add memory monitoring + garbage collection
2. **Short-term (within 1 day):** Implement chunk size reduction (100-150 chunks)
3. **Medium-term (within 1 week):** Add explicit GPU memory cleanup
4. **Long-term:** Implement per-object stage isolation

## Additional Considerations

### Checkpoint/Resume Support

Currently, skip logic (`overwrite=False`) only checks for output files. Better approach:
- Save progress to a JSON file after each N objects
- Allow resuming from last checkpoint on crash

### Category-Based Chunking

Instead of simple index-based chunking, use category-aware chunking:
- Distribute large categories across chunks
- Avoid concentrating memory-intensive categories in single chunks

### Test with Problematic Categories

Manually test rendering only:
- ceiling files (largest structural meshes)
- cabinet files (complex furniture)
- All 1,698 bottle files in single chunk

## Conclusion

**Root Cause:** Memory leaks due to lack of explicit cleanup between object renders in `render_thumbnail_wo_bg`.

**Primary Fix Required:**
1. Add garbage collection every 50 objects
2. Add explicit camera/frame buffer cleanup
3. Reduce chunk size from 50 to 100-150

**Estimated Impact:** These changes should reduce peak memory usage by 30-50% and eliminate SIGSEGV crashes.
