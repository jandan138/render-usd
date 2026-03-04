# DLC Job Crash Analysis Report

**Job ID**: dlc1ypy51l0st5au
**Job Name**: render_grscenes_test1_49_50
**Status**: Failed (Segmentation Fault)
**Analysis Date**: 2026-03-04

## 1. Crash Summary

- **When**: March 4, 2026, 10:53:14 UTC
- **Location**: `renderer.py:159` at `self.world.step(render=True)`
- **What**: Segmentation fault (exit code 139) during rendering iteration
- **Progress**: 28/1016 objects rendered (2.8% complete)
- **Duration**: ~6.7 minutes (10:46:33 - 10:53:14)

## 2. Error Details

### Stack Trace
```
Thread 0x00007f9725b08740 (most recent call first):
  File ".../isaacsim/exts/omni.isaac.core/omni/isaac/core/simulation_context/simulation_context.py", line 696 in step
  File ".../isaacsim/exts/omni.isaac.core/omni/isaac/core/world/world.py", line 536 in step
  File ".../src/render_usd/core/renderer.py", line 159 in render_thumbnail_wo_bg
  File ".../src/render_usd/cli.py", line 336 in main
  File ".../src/render_usd/cli.py", line 349 in <module>
```

### Code Location
**File**: `src/render_usd/core/renderer.py`
**Line**: 159
**Code**: `self.world.step(render=True)` in the 8-step rendering loop after 100 physics steps

## 3. Last Rendered USD File

**Path**: `/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/washing_machine/2803be44430b12e21b95208bee7aed27/usd/2803be44430b12e21b95208bee7aed27.usd`
**Category**: washing_machine
**File Size**: 29 MB
**Verification Failures**: 10 (during this object's rendering)

## 4. Analysis of USD Imaging Warnings

### Warning Pattern
Throughout the job log, there are recurring USD imaging verification warnings:

```
[Warning] [omni.usd] Coding Error: in _Get at line 3003 of /buildAgent/work/ac88d7d902b57417/USD/pxr/usdImaging/usdImaging/delegate.cpp -- Failed verification: ' prim '
```

### Warning Count by Object Type
- **Wall objects** (26 rendered): 1 verification failure each
- **Washing machine objects** (12 rendered): 10-22 verification failures each
- **Last object (washing_machine/2803be44)**: 10 verification failures

### Key Observation
The "Failed verification: ' prim '" warnings indicate USD imaging delegate issues with prim references. These warnings appear to be:
1. More frequent with complex objects (washing machines have more warnings than walls)
2. Consistently present but not immediately fatal
3. Possibly cumulative - may lead to unstable state over time

## 5. Potential Causes

### Primary Cause: Accumulated USD Imaging State Corruption

**Evidence**:
- Segmentation fault occurs at `world.step(render=True)` - a rendering operation
- Warnings from `usdImaging/delegate.cpp` (USD imaging delegate) accumulate
- Complex objects generate more warnings
- No explicit memory OOM errors in logs
- Crash happens after ~40 objects with ~203 total verification warnings

**Hypothesis**:
The USD imaging delegate's prim verification failures may lead to:
1. Accumulation of invalid/incomplete prim references in the delegate's internal state
2. GPU resource leaks from improperly cleaned rendering state
3. Eventual corruption causing segmentation fault during rendering steps

### Secondary Factors

1. **Scene Complexity Accumulation**
   - The renderer loads USD stages but may not fully unload them between objects
   - Accumulated scene complexity could exceed internal buffers

2. **Memory Management**
   - Job configured with 118Gi memory, but no OOM errors
   - Possible GPU memory fragmentation or leaks

3. **Object-Specific Issues**
   - Washing machine objects are more complex than walls
   - The last object (29MB) is not the largest in its category
   - No clear correlation between file size and crash

## 6. Resource Configuration

```
Image: pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118
Resources:
  CPU: 16 cores
  GPU: 1
  Memory: 118 Gi
  Shared Memory: 118 Gi
  Data Sources: d-mzps5b7joy2axmqpa8, d-d49o5g0h2818sw8j1g, d-8wz4emfs21s5ajs9oz
```

## 7. Recommendations

### Immediate Actions

1. **Add Scene Cleanup Between Objects**
   - Explicitly clear USD stage and prim references after each render
   - Force garbage collection between iterations
   - Reload SimulationApp periodically or restart after N objects

2. **USD Imaging Error Handling**
   - Suppress or handle the "Failed verification" warnings more gracefully
   - Add validation before rendering to detect corrupted state
   - Implement fallback when imaging delegate errors accumulate

3. **Monitor and Restart**
   - Add checkpoint saving every N objects
   - Implement auto-restart after crash with resume capability
   - Track warning counts and trigger restart before crash

### Long-term Solutions

1. **Refactor Rendering Loop**
   - Consider rendering batches of objects in separate processes
   - Use external process isolation to prevent state accumulation
   - Implement proper resource cleanup pattern

2. **USD File Validation**
   - Pre-validate USD files for structural issues
   - Identify and fix problematic USD files with prim reference issues
   - Consider simplifying or repairing complex USD files

3. **Alternative Rendering Approach**
   - Explore batch rendering with USD Composer or other tools
   - Consider using Isaac Sim's multi-stage rendering capabilities
   - Evaluate switching to RTX renderer with different configuration

## 8. Data for Further Investigation

### Test Cases to Run

1. **Reproduce with Single Object**
   ```bash
   python -m render_usd.cli single \
     --usd_path /cpfs/.../washing_machine/2803be44430b12e21b95208bee7aed27/usd/2803be44430b12e21b95208bee7aed27.usd \
     --output_dir ./test_crash
   ```

2. **Test with Smaller Batch**
   - Run job with chunk_id 49 but limited to 20 objects
   - Monitor warning accumulation pattern

3. **Compare Successful Job**
   - Find and analyze logs from a successfully completed job
   - Compare warning patterns and rendering progress

### Files to Monitor

- Output directory for partial results
- Isaac Sim log files (if accessible)
- GPU memory usage during rendering
- USD stage reference counts

## 9. Conclusion

The crash appears to be caused by accumulated state corruption in the USD imaging delegate, evidenced by:
- Consistent "Failed verification" warnings from `usdImaging/delegate.cpp`
- Higher warning counts for complex objects
- Segmentation fault during rendering step after 40 objects

The recommended approach is to add proper cleanup and checkpointing to prevent state accumulation and enable recovery from crashes.
