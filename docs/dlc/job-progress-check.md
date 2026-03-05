# DLC Job Progress Display Check Report

**Date:** 2026-03-05
**Checked by:** dlc-operator agent

## Summary

All 4 running DLC jobs are displaying **incorrect progress numbers**. They show the total dataset size (52907) instead of the chunk size (~530).

## Jobs Checked

| Chunk | Job ID | Status | Pod ID | Progress Display |
|-------|--------|--------|--------|------------------|
| 13 | dlctx6dqh4kvx1vp | Running | dlctx6dqh4kvx1vp-master-0 | `[X/52907]` |
| 14 | dlcxt0p3dqh57d0l | Running | dlcxt0p3dqh57d0l-master-0 | `[X/52907]` |
| 15 | dlcyczvuxzzzuwql | Running | dlcyczvuxzzzuwql-master-0 | `[X/52907]` |
| 17 | dlcz6yo095r6946j | Running | dlcz6yo095r6946j-master-0 | `[X/52907]` |

## Log Evidence

### Chunk 13 (dlctx6dqh4kvx1vp)
```
[188/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/blanket/0de0c48976fde9c070b2764930be82df/usd/0de0c48976fde9c070b2764930be82df.usd
[189/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/blanket/0df8d8cc2c95061dd4d82f7a9ba2a751/usd/0df8d8cc2c95061dd4d82f7a9ba2a751.usd
...
[200/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/blanket/15e4fa830261c086d5192f1cde0de527/usd/15e4fa830261c086d5192f1cde0de527.usd
[201/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/blanket/15eec3462336cfefe90b1d5825861fa1/usd/15eec3462336cfefe90b1d5825861fa1.usd
```

### Chunk 14 (dlcxt0p3dqh57d0l)
```
[146/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/aa4ad4375a38f7c89d100d36c6a206e5/usd/aa4ad4375a38f7c89d100d36c6a206e5.usd
[147/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/aa7c816f82cc6bdd384643d3c9fc05c5/usd/aa7c816f82cc6bdd384643d3c9fc05c5.usd
...
[150/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/b0637c7c7b53824eb7bc2b556ab8bc72/usd/b0637c7c7b53824eb7bc2b556ab8bc72.usd
[151/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/b2dd2adcf0319bddb0ad7dc6147c8eab/usd/b2dd2adcf0319bddb0ad7dc6147c8eab.usd
```

### Chunk 15 (dlcyczvuxzzzuwql)
```
[162/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/e0f2172eaba4bae75aebdca9e596289b/usd/e0f2172eaba4bae75aebdca9e596289b.usd
[163/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/e26e4c16158005d3419bb4f9b1a64626/usd/e26e4c16158005d3419bb4f9b1a64626.usd
...
[167/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/eeddbdefeff04437a11a32b7734275ce/usd/eeddbdefeff04437a11a32b7734275ce.usd
[168/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/ef4a0445e92e0a3bcab74e2530f7713e/usd/ef4a0445e92e0a3bcab74e2530f7713e.usd
```

### Chunk 17 (dlcz6yo095r6946j)
```
[160/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/dab327501bea3539edc5ca1842631def/usd/dab327501bea3539edc5ca1842631def.usd
[161/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/db2d46cc6932e68275c07f07ea229d2a/usd/db2d46cc6932e68275c07f07ea229d2a.usd
...
[166/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/ebeced8476bb3d01fa5f4f139912fb59/usd/ebeced8476bb3d01fa5f4f139912fb59.usd
[167/52907] Rendering: /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/eeddbdefeff04437a11a32b7734275ce/usd/eeddbdefeff04437a11a32b7734275ce.usd
```

## Problem Analysis

**Expected behavior:** Each chunk should display progress as `[X/530]` (or similar chunk-sized number)

**Actual behavior:** All chunks display `[X/52907]` (the total number of assets across all chunks)

**Root cause:** The `render_custom` command being used does not support chunking. Looking at the user command in job details:

```bash
bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view
```

The `render_custom` mode processes all files in the directory without chunking. The chunking logic (`--chunk_id` and `--chunk_total` args) is only available in the `grscenes100` command.

## Impact

- Progress display is misleading - shows 188/52907 instead of 188/530
- Each chunk is processing the full dataset instead of its assigned slice
- This means all 100 chunks are processing all 52907 assets = redundant work

## Recommendation

The job submission needs to be fixed to:
1. Either use `grscenes100` command with proper `--chunk_id` and `--chunk_total` arguments
2. Or add chunking support to `render_custom` command

Current incorrect submission:
```bash
run_task.sh render_custom <assets_dir> view
```

Should be:
```bash
run_task.sh <chunk_id> <chunk_total>  # for grscenes100 mode
```

Or `render_custom` needs to accept `--chunk_id` and `--chunk_total` parameters.
