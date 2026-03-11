# DLC 批量重提交报告：相机距离修复 (v2)

**日期**: 2026-03-08
**操作员**: team-lead (Claude Code agent team)
**Commit**: `8d64a69` — fix(renderer): Remove camera distance upper bound

---

## 1. 背景

上一轮批量渲染 (2026-03-04/05, `render_grscenes_test1_fixed`) 使用的代码中，相机距离计算存在上限截断：

```python
# 旧代码
distance = np.clip(distance, 0.1, 100.0)
```

这导致**大型物体**（bbox 对角线 > 100）的相机距离被截断到 100，相机距离物体过近，渲染效果不正确。

## 2. 代码修改

**文件**: `src/render_usd/core/renderer.py:224`

```python
# 修改前
distance = np.clip(distance, 0.1, 100.0)

# 修改后
distance = max(distance, 0.1)
```

- 移除了 `100.0` 的上限，仅保留 `0.1` 的下限防止除零
- 大物体现在可以获得正确的相机距离，渲染时完整显示

## 3. 提交配置

| 配置项 | 值 |
|--------|-----|
| 任务名前缀 | `render_grscenes_test1_v2` |
| 总 Chunk 数 | 100 |
| 每 Chunk 约 | 529 个资产 (52,907 / 100) |
| 资产路径 | `/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets` |
| 命名风格 | `view` (front.png, left.png, back.png, right.png) |
| Overwrite | **启用** (需要覆盖旧渲染结果) |
| GPU | 1x per job |
| CPU | 16 cores per job |
| 内存 | 118 GiB per job |
| 镜像 | `isaacsim41-cuda118` |
| 优先级 | 7 |
| 工作空间 | 270969 (SmartBot) |
| 数据源 | `d-mzps5b7joy2axmqpa8`, `d-d49o5g0h2818sw8j1g`, `d-8wz4emfs21s5ajs9oz` |

## 4. 提交命令

```bash
python3 scripts/dlc/submit_batch.py \
    --total 100 \
    --name render_grscenes_test1_v2 \
    --command_args "render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view {chunk_id} {chunk_total} --overwrite"
```

容器内实际执行：
```bash
bash run_task.sh render_custom \
    /cpfs/.../GRScenes-test1/GRScenes_assets \
    view <chunk_id> 100 true
```

## 5. 提交结果

| 指标 | 值 |
|------|-----|
| 提交成功 | **100 / 100** |
| 提交失败 | **0** |
| 提交时间 | 2026-03-08 17:16 ~ 17:18 UTC |
| Failed 任务 | **0** (提交后即时检查) |

### 任务命名格式

`render_grscenes_test1_v2_{chunk_id}_100`

### 首尾 Job ID

| Chunk | Job ID | 初始状态 |
|-------|--------|---------|
| 0 | `dlcqs3oy1jua8tbk` | EnvPreparing |
| 99 | `dlc1o2qyvdxqadf5` | Running |

完整 Job ID 列表保存在: `/tmp/dlc_job_ids_v2.txt`

## 6. 与上次提交的对比

| 对比项 | v1 (03-04/05) | v2 (03-08) |
|--------|---------------|------------|
| 任务名 | `render_grscenes_test1_fixed` | `render_grscenes_test1_v2` |
| Chunk 数 | 100 | 100 |
| 代码修复 | 重复代码块 (`8c1eb14`) | 相机距离上限 (`8d64a69`) |
| Overwrite | 否 | **是** |
| 资源配置 | 相同 | 相同 |

## 7. Pre-flight 检查结果

| 检查项 | 结果 |
|--------|------|
| 最新 commit `8d64a69` | PASS |
| src/ 无未提交改动 | PASS |
| DLC CLI 二进制 | PASS |
| Shell 脚本语法 | PASS |
| 资产目录 (80 分类) | PASS |
| MDL 搜索路径 | PASS |
| submit_batch.py 语法 | PASS |

## 8. 监控命令

```bash
# 查看所有 v2 任务状态
./dlc get job --workspace_id 270969 --display_name_regex "render_grscenes_test1_v2_.*"

# 查看失败任务
./dlc get job --workspace_id 270969 --display_name_regex "render_grscenes_test1_v2_.*" --status Failed

# 查看单个任务详情
./dlc get job <job_id>

# 查看任务日志
./dlc logs <job_id>
```

## 9. 预期输出

每个 USD 文件生成 4 张 512×512 PNG，就地保存在资产目录下：
```
GRScenes_assets/Category/UID/front.png
GRScenes_assets/Category/UID/left.png
GRScenes_assets/Category/UID/back.png
GRScenes_assets/Category/UID/right.png
```

---

**报告状态**: 完成
**Agent Team**: dlc-resubmit (team-lead 独立完成，子 agents 未能正常执行)
