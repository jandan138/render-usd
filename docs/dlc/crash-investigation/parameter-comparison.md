# Parameter Comparison: Failed vs Running Jobs

**Date:** 2026-03-04
**Task:** Compare parameters between failed job (chunk 49) and running jobs (chunks 48, 43)
**Jobs analyzed:**
- Failed: `dlc1ypy51l0st5au` (chunk 49/50)
- Running: `dlc1yfyjntnuvoj1` (chunk 48/50), `dlc1ws0zd518q9xf` (chunk 43/50)

---

## Job Configuration Comparison

### Identical Parameters

All three jobs have **identical** configuration except for the chunk ID:

| Parameter | Failed Job (49) | Running Jobs (48, 43) |
|-----------|-----------------|----------------------|
| **Image** | pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118 | Same |
| **CPU** | 16 | Same |
| **GPU** | 1 | Same |
| **Memory** | 118Gi | Same |
| **SharedMemory** | 118Gi | Same |
| **DataSources** | d-mzps5b7joy2axmqpa8, d-d49o5g0h2818sw8j1g, d-8wz4emfs21s5ajs9oz | Same |
| **Priority** | 7 | Same |
| **JobType** | PyTorchJob | Same |

### UserCommand Comparison

| Job | Command | Difference |
|-----|---------|-----------|
| Failed (49) | `bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view 49 50 true` | Chunk ID: **49** |
| Running (48) | `bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view 48 50 true` | Chunk ID: **48** |
| Running (43) | `bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view 43 50 true` | Chunk ID: **43** |

**Only difference:** The chunk ID parameter (49 vs 48 vs 43)

---

## Asset Categories Analysis

### Chunk Distribution

The dataset has **79 categories** distributed across 50 chunks (approx. 1-2 categories per chunk).

| Chunk | Category | Assets |
|-------|----------|--------|
| 49 (Failed) | **piano** | 10 assets |
| 48 (Running) | **person** | ~100+ assets |
| 43 (Running) | Various | Multiple categories |

### Piano Category Details

Chunk 49 processes the `piano` category with 10 assets:
```
piano/
├── 063a5c39a236e1eccaa98f33caaa0991/
├── 6a348e241fdc8aaecdae8c956936baa3/
├── 709f62d716d8a4bf1ccce14a5d109aef/
├── 7facdf53d93cf83fd6fb7be300483490/
├── 9edbec4fb3f4a2e2a61e22cc951d573d/
├── ac13ac675e4ee25aebd2da7309a70b35/
├── b28c2b582761f6156f1f76734ad5e31f/
├── bf7fcea263767dd3f29bfd22f4425019/
└── d317c9673e89fc996864e4df0caad4e3/
```

Each piano asset follows the expected structure:
- `usd/{UID}.usd` - USD file (large, ~6.8MB each)
- `glb/{UID}.glb` - GLB file (~16MB each)
- `{front,left,right,back}.png` - Render outputs
- `{UID}_annotation.json` - Annotation file
- `textures` symlink -> `../../../../Material/mdl/textures`

---

## Critical Finding: Renders Were Successful

### Timeline Analysis

| Event | Time (UTC) |
|-------|------------|
| Job Created | 2026-03-04T10:42:08Z |
| Job Started Running | 2026-03-04T10:46:34Z |
| **First Piano Render Complete** | **2026-03-04T10:50:12Z** |
| **Last Piano Render Complete** | **2026-03-04T10:50:37Z** (25 seconds total) |
| Job Failed | 2026-03-04T10:53:15Z |

### Key Observations

1. **All 10 piano assets were successfully rendered** between 10:50:12 and 10:50:37
2. The renders were created during job execution (between start and fail times)
3. The job ran for ~11 minutes (667 seconds) but the actual rendering of 10 piano assets took only ~25 seconds
4. The job failed with exit code **139** (SIGSEGV - segmentation fault) **after** all renders completed

---

## Root Cause Hypothesis

### NOT Related To:
- **Job configuration** - All parameters identical
- **Resource allocation** - CPU/GPU/Memory same
- **Data sources** - Same datasets mounted
- **Command arguments** - Only chunk ID differs
- **Asset structure** - Piano assets follow expected pattern
- **Rendering process** - All piano renders completed successfully

### Likely Cause: Post-Rendering Cleanup/Shutdown

The evidence suggests the crash occurs **after** rendering completes:

1. **Timeline:** Renders finished at 10:50:37, job failed at 10:53:15 (~3 minutes later)
2. **Exit code 139:** SIGSEGV indicates a segmentation fault, commonly occurring during:
   - Isaac Sim cleanup/shutdown
   - Python interpreter shutdown
   - Memory deallocation after SimulationApp destruction

### Possible Scenarios

1. **Isaac Sim Shutdown Bug:** After rendering all 10 piano assets, the script attempts to shutdown `SimulationApp`, causing a segfault
2. **Post-Processing Error:** The script might be performing cleanup operations after the render loop
3. **Resource Cleanup Memory Issue:** Deallocating large USD stages (6.8MB each) + Isaac Sim resources might trigger a memory corruption
4. **Timeout/Hanging:** The script might hang during shutdown, and the job controller kills it (though exit code 139 suggests crash, not timeout)

### Why Only Chunk 49?

This could be:
1. **Random chance:** The bug might be intermittent and happened to occur on chunk 49
2. **Last chunk effect:** Chunk 49 is near the end (49/50), possibly hitting edge cases
3. **Asset-specific:** Piano assets might have characteristics that trigger cleanup bugs (large USD files, specific material references)
4. **Node-specific:** The job ran on node `10.224.159.33` - might be a problematic node

---

## Job Network Information

| Job | Node IP |
|-----|---------|
| Failed (49) | 10.224.159.33 |
| Running (48) | 10.224.158.131 |
| Running (43) | 10.224.158.131 |

**Note:** The failed job ran on a different node than the running jobs. This could be a factor if node `10.224.159.33` has issues.

---

## Next Steps

1. **Examine the full job log** for chunk 49 to see what happened after the renders completed
2. **Check if other chunks on node 10.224.159.33** have similar failures
3. **Review shutdown/cleanup code** in `renderer.py` for potential segfault sources
4. **Consider adding error handling** around Isaac Sim shutdown
5. **Investigate if the issue is reproducible** by re-running chunk 49

---

## Summary

**No parameter differences found** between failed and running jobs. The failure is **not** due to:
- Different assets being rendered (piano assets rendered successfully)
- Different job configuration
- Different resource allocation

**Most likely cause:** Post-rendering cleanup/shutdown issue causing a segmentation fault (exit code 139). The renders completed successfully, but the process crashed 3 minutes later, likely during Isaac Sim or Python shutdown.

**Investigation priority:** Review logs from the failed job to see what happened between 10:50:37 (last render) and 10:53:15 (job failure).
