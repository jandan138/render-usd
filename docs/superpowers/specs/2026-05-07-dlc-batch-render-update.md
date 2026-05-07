---
title: "DLC Batch Rendering Update for test0_transitive_apply_parallel Dataset"
date: "2026-05-07"
author: "OpenCode Agent"
status: "approved"
---

# Design: DLC Batch Rendering Update for test0_transitive_apply_parallel Dataset

## 1. Problem Statement

对 `/cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset` 下 53,167 个 USD 资产执行批量四视角渲染，DLC 提交脚本需要更新以支持：

1. 访问 `/cpfs/user/zhuzihou`（需要第4个数据源 `d-f1dsz5nbamclxgydo8`）
2. 同步参考仓库（`usd-scene-physics-prep`）的脚本改进（严格模式、参数验证、资源配置模板）
3. 保持 Isaac Sim 4.1.0 conda 环境配置不变
4. 修复 view 命名模式下的跳过逻辑（关键 bug）

## 2. Scope

### In Scope
- `scripts/dlc/launch_job.sh` 重构
- `scripts/dlc/run_task.sh` 安全性修复（移除 eval）
- `src/render_usd/core/renderer.py` view 模式跳过逻辑修复
- 数据源更新（4个）
- 镜像保持 4.1.0

### Out of Scope
- 渲染核心逻辑改动（相机、光照等）
- submit_batch.py 修改（已支持所需功能）
- 新功能开发

## 3. Architecture

### Call Chain
```
submit_batch.py -> launch_job.sh -> dlc submit -> Worker Container
                                                      |
                                            run_task.sh -> python render_usd.cli
```

### Key Changes
1. **launch_job.sh**: 添加严格模式、参数验证、GPU模板、超时配置、二进制校验
2. **run_task.sh**: 移除 eval，改用直接执行
3. **renderer.py**: 修复 view 模式跳过逻辑，支持检测 `front.png`/`back.png`/`left.png`/`right.png`

## 4. Data Flow

### Input
- 53,167 USD assets in `GRScenes_assets/<category>/<uid>/usd/<uid>.usd`

### Processing
- 75 chunks, ~709 assets per chunk
- Each asset: 4 views (front/back/left/right)
- Render time: ~2-3 seconds per view (estimate)
- Chunk time: ~709 × 4 × 2.5s ≈ 1.97 hours

### Output
- `GRScenes_assets/<category>/<uid>/front.png`
- `GRScenes_assets/<category>/<uid>/back.png`
- `GRScenes_assets/<category>/<uid>/left.png`
- `GRScenes_assets/<category>/<uid>/right.png`

## 5. Error Handling

| Error | Handling |
|-------|----------|
| Missing assets_dir | Pre-check in run_task.sh |
| DLC binary missing | launch_job.sh validates before submit |
| Invalid chunk_id/total | Integer validation in launch_job.sh |
| Timeout | job_max_running_time_minutes=480 (8h) |
| Isaac Sim crash | renderer.cleanup() + gc.collect() + kit.close() |

## 6. Configuration

### Default Data Sources
```
d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8
```

### Resource Defaults
```bash
GPU=1, CPU=14, Memory=100Gi, SharedMemory=100Gi
Resource_ID=quota1r947pmazvk
Image=pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118
Timeout=480 minutes (8h)
```

## 7. Security

- `set -euo pipefail` in all bash scripts
- Integer validation for chunk parameters
- DLC binary executable check
- Quoted path variables to prevent injection
- No eval in run_task.sh

## 8. Testing & Verification

1. **Local dry-run**: Test launch_job.sh with DLC_BIN=/bin/echo
2. **Single asset test**: Run render_custom on 1 asset
3. **Small batch**: Submit 2-3 chunks, verify output structure
4. **Full batch**: Submit all 75 chunks
5. **Output validation**: Random sample check for front/back/left/right.png

## 9. Risks

| Risk | Mitigation |
|------|-----------|
| renderer.py fix breaks existing index mode | Unit test both modes |
| Quota insufficient for 75 jobs | Monitor and batch if needed |
| Isaac Sim 4.1.0 image outdated | Keep current, user confirmed |

## 10. Rollback

All changes are backward-compatible:
- Environment variables override all defaults
- launch_job.sh 保留全部参数接口
- run_task.sh 保留所有现有模式
