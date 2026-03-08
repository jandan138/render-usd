# 相机距离问题排查方案

> 本文档描述了针对「新渲染结果物体显示过近」问题的系统化排查方案，包括代码修改、测试脚本和结果判断逻辑。

## 1. 问题背景

新渲染结果（2026-03-05）中物体显示过近，无法展示全貌。详细对比分析见 [camera-distance-investigation-report.md](./camera-distance-investigation-report.md)。

核心现象：
- **旧渲染**（2026-01-19）：物体完整展示，约占画面 60-65%
- **新渲染**（2026-03-05）：物体特写，几乎填满画面

调查已确认 bbox 计算公式、距离公式、相机参数、USD 文件均未改变。两个可疑改动锁定为：
1. **commit a31f3ee**：每个物体渲染前新增 `world.reset()` 调用
2. **commit 3c294a3**：HDRI 灯光 + `backgroundZeroAlpha` + RGBA alpha 合成

## 2. 排查方案设计

### 设计思路

采用**环境变量开关**控制排查，不修改默认行为。所有开关未设置时，代码行为与当前 main 分支完全一致。这样可以：
- 在同一代码版本下测试多种配置
- 无需 checkout 不同 commit
- 排查完毕后只需删除开关代码即可恢复

### 环境变量开关一览

| 环境变量 | 作用 | 对应可疑改动 |
|----------|------|-------------|
| `RENDER_SKIP_LOOP_RESET=1` | 跳过循环内的 `world.reset()` 调用 | commit a31f3ee |
| `RENDER_SKIP_ALPHA=1` | 跳过 `backgroundZeroAlpha` 设置 + 跳过 RGBA alpha 合成（直接用 RGB） | commit 3c294a3 |

### Debug 日志

新增 `[DEBUG-CAM]` 前缀的日志行，打印每个物体的 bbox 和 distance 计算结果，用于对比新旧环境下相机参数是否一致。

## 3. 代码修改清单

### 3.1 `src/render_usd/core/renderer.py`

#### 修改点 1：world.reset() 环境变量开关（第 183-189 行）

```python
# CRITICAL FIX #1: Reset world state before loading new object
if not os.environ.get("RENDER_SKIP_LOOP_RESET"):
    try:
        self.world.reset()
    except Exception as e:
        print(f"[Warning] World reset failed: {e}, continuing...")
else:
    print(f"[DEBUG] Skipping world.reset() in loop (RENDER_SKIP_LOOP_RESET=1)")
```

当 `RENDER_SKIP_LOOP_RESET=1` 时，跳过循环内的 `world.reset()` 调用，模拟旧代码（1月19日）的行为。

#### 修改点 2：Debug 日志（第 229-231 行）

在 distance 计算完成后打印详细信息：

```python
print(f"[DEBUG-CAM] {object_name}: bbox_min={bbox_min}, bbox_max={bbox_max}, "
      f"diagonal={np.linalg.norm(bbox_max - bbox_min):.4f}, distance={distance:.4f}, "
      f"center={center}")
```

输出示例：
```
[DEBUG-CAM] bed01: bbox_min=[-1.2 -0.9 0.0], bbox_max=[1.2 0.9 0.8], diagonal=2.5100, distance=2.5100, center=[0.0 0.0 0.4]
```

#### 修改点 3：RGBA 合成环境变量开关（第 265-274 行）

```python
if os.environ.get("RENDER_SKIP_ALPHA"):
    rgb = get_src(camera, "rgb")
else:
    rgba = get_src(camera, "rgba")
    if rgba is not None and rgba.shape[2] == 4:
        alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
        bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)
        rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
    else:
        rgb = get_src(camera, "rgb")
```

当 `RENDER_SKIP_ALPHA=1` 时，跳过 RGBA alpha 合成，直接获取 RGB 图像，模拟旧代码行为。

### 3.2 `src/render_usd/core/scene.py`

#### 修改点：backgroundZeroAlpha 环境变量开关（第 67-74 行）

```python
settings = carb.settings.get_settings()
if not os.environ.get("RENDER_SKIP_ALPHA"):
    settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
    settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
    settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
    settings.set("/app/captureFrame/setAlphaTo1", False)
else:
    print(f"[DEBUG] Skipping backgroundZeroAlpha settings (RENDER_SKIP_ALPHA=1)")
```

`RENDER_SKIP_ALPHA=1` 同时控制两处：
1. `scene.py` 中的 RTX `backgroundZeroAlpha` 设置（渲染器级别）
2. `renderer.py` 中的 RGBA alpha 合成（后处理级别）

两者配合使用才能完整回退到旧代码行为。

## 4. 研究结论汇总

### bbox 计算：100% 未变

`compute_bbox` 函数使用 `UsdGeom.Imageable.ComputeWorldBound()`，自初始提交以来从未修改。距离公式 `distance = np.linalg.norm(bbox_max - bbox_min) * 1.0` 同样从未改变。

### commit a31f3ee (world.reset)

`world.reset()` 是 Isaac Sim `omni.isaac.core.World` 的方法，主要作用是重置物理仿真状态。理论上不应影响 USD stage 上的 primitives 和场景层级结构，但：
- 可能重置环境灯光（DomeLight）的某些属性
- 可能影响渲染器的内部状态缓存
- 需要通过实验验证其对相机距离/视角的实际影响

### commit 3c294a3 (HDRI/alpha)

HDRI 灯光和 `backgroundZeroAlpha` 设置**不影响相机参数**（位置、朝向、距离），仅影响：
- 场景光照强度和方向
- 渲染输出的 alpha 通道
- 后处理阶段的背景合成

理论上不应导致物体显示过近，但 RTX 渲染器的 post-processing 管线可能存在未知的副作用。

### render_thumbnail_with_bg

`render_thumbnail_with_bg` 方法（第 314-449 行）：
- **无** 循环内 `world.reset()` 调用
- **无** RGBA alpha 合成（直接使用 `get_src(camera, "rgb")`）
- **不受** 上述两个可疑改动影响

因此，`render_thumbnail_with_bg` 的渲染结果可作为额外参考基线。

## 5. 测试方案

### 测试脚本

`scripts/debug_camera_distance.sh` — 自动化运行三种配置的对比测试。

### 使用方法

```bash
bash scripts/debug_camera_distance.sh /path/to/asset.usd
```

### 三种测试配置

| 测试组 | 环境变量 | 含义 | 输出目录 |
|--------|----------|------|----------|
| A (Baseline) | 无 | 当前 main 分支默认行为 | `test_outputs/debug_A/` |
| B (Skip reset) | `RENDER_SKIP_LOOP_RESET=1` | 跳过循环内 world.reset() | `test_outputs/debug_B/` |
| C (Skip alpha) | `RENDER_SKIP_ALPHA=1` | 跳过 backgroundZeroAlpha + alpha 合成 | `test_outputs/debug_C/` |

### 命令示例

脚本内部实际执行的命令：

```bash
# Test A: Baseline
python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_A \
    --naming_style view \
    --overwrite

# Test B: Skip per-loop world.reset()
RENDER_SKIP_LOOP_RESET=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_B \
    --naming_style view \
    --overwrite

# Test C: Skip backgroundZeroAlpha + alpha compositing
RENDER_SKIP_ALPHA=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_C \
    --naming_style view \
    --overwrite
```

每个测试启动独立的 Python 进程，因为 Isaac Sim 的 `SimulationApp` 只能初始化一次。

### 观察要点

1. **[DEBUG-CAM] 日志**：对比三组的 `bbox_min`、`bbox_max`、`diagonal`、`distance` 是否一致
2. **输出图片**：对比物体在画面中的占比大小
3. **背景颜色**：Test C 的背景可能与 A/B 不同（因跳过了 alpha 合成）

## 6. 结果判断逻辑

### 情况 1：Test B 修复（物体距离恢复正常）

→ **world.reset() 是元凶**

- 循环内的 `world.reset()` 重置了某些渲染状态，导致相机行为异常
- 修复方案：移除循环内的 `world.reset()`，或改用更精确的重置方法

### 情况 2：Test C 修复（物体距离恢复正常）

→ **backgroundZeroAlpha 设置是元凶**

- RTX `backgroundZeroAlpha` 或 RGBA alpha 合成影响了渲染输出
- 修复方案：调整 backgroundZeroAlpha 参数，或修改 alpha 合成逻辑

### 情况 3：Test B 和 C 都修复

→ **两者共同作用**

- 需要进一步隔离：分别测试只跳过 `world.reset()` 内的某些步骤、只跳过 `backgroundZeroAlpha` 设置（不跳过 alpha 合成）等

### 情况 4：Test B 和 C 都没修复

→ **环境差异导致**

- 问题不在代码改动，而在运行环境差异（DLC 容器 vs 本地 dev 机器）
- 后续步骤：
  - 对比 DLC 容器和本地 dev 机器的 Isaac Sim 版本
  - 检查 GPU 驱动、CUDA 版本差异
  - 在旧环境中复现渲染，确认环境因素

## 7. 后续清理

排查完毕后，需要删除以下 debug 代码：

1. **renderer.py**：
   - 移除 `RENDER_SKIP_LOOP_RESET` 环境变量检查（第 183-189 行），根据排查结果决定是否保留 `world.reset()`
   - 移除 `[DEBUG-CAM]` 日志行（第 229-231 行）
   - 移除 `RENDER_SKIP_ALPHA` 环境变量检查（第 265 行），根据排查结果决定是否保留 alpha 合成

2. **scene.py**：
   - 移除 `RENDER_SKIP_ALPHA` 环境变量检查（第 68-74 行），根据排查结果决定是否保留 `backgroundZeroAlpha` 设置

3. **scripts/**：
   - `scripts/debug_camera_distance.sh` 可保留作为后续排查工具，或删除

4. **test_outputs/**：
   - 删除 `test_outputs/debug_A/`、`test_outputs/debug_B/`、`test_outputs/debug_C/` 目录

## 8. 执行阶段记录（2026-03-08）

### 已完成

| 步骤 | 状态 | 说明 |
|------|------|------|
| 代码修改：renderer.py (3处) | ✅ 完成 | debug 日志 + world.reset 开关 + RGBA 开关 |
| 代码修改：scene.py (1处) | ✅ 完成 | backgroundZeroAlpha 开关 |
| 测试脚本：debug_camera_distance.sh | ✅ 完成 | 已验证 CLI 参数兼容性 |
| 代码审查 | ✅ 通过 | 6 项检查全部通过，默认行为零风险 |
| bbox 计算验证 | ✅ 确认未变 | compute_bbox 从初始提交至今完全相同 |
| commit a31f3ee 分析 | ✅ 完成 | world.reset 不影响 USD stage primitives |
| commit 3c294a3 分析 | ✅ 完成 | HDRI/alpha 仅后处理，不影响相机参数 |
| render_thumbnail_with_bg 分析 | ✅ 完成 | 无 world.reset 循环、无 RGBA 合成，不受影响 |

### 未完成：渲染测试执行

**阻塞原因**：执行阶段 Bash 工具间歇性不可用（auto mode classifier 临时故障），导致无法运行 shell 命令（nvidia-smi、find、python 渲染等）。Agent 团队中的 4 个执行 agent 也因此无法正常工作。

**环境状态**（部分已确认）：
- conda 环境：`miniconda/bin/activate` 存在 ✅
- `assets/environments/background.usd`：不存在（将 fallback 到 HDRI DomeLight）
- GPU 可用性：**未确认**（需要 nvidia-smi）
- render-usd 包安装状态：**未确认**

**测试用 USD 文件路径**（待确认）：
- 从 image-comparison-report.md 已知 bed asset ID: `0a85b986de35ccfdec7c686d791fd747`
- 可能路径 1: `/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/0a85b986de35ccfdec7c686d791fd747/usd/0a85b986de35ccfdec7c686d791fd747.usd`
- 可能路径 2: `/cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all/Bed/*/Bed_*.usd`（GRScenes-100 结构: Category/AssetID/AssetID.usd）

## 9. 下一步操作指南

### Step 1：确认环境（1 分钟）

```bash
cd /cpfs/shared/simulation/zhuzihou/dev/render-usd

# 检查 GPU
nvidia-smi

# 激活环境
source miniconda/bin/activate render-usd
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
export OMNI_KIT_ACCEPT_EULA=YES

# 确认包已安装
pip show render-usd || pip install -e .
```

### Step 2：找到测试用 USD 文件（1 分钟）

```bash
# 方式 A: 在 GRScenes-test1 中找 bed（render_custom 结构）
ls /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/0a85b986de35ccfdec7c686d791fd747/usd/

# 方式 B: 在 GRScenes-100 中找 bed（Category/AssetID/AssetID.usd 结构）
find /cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all -maxdepth 3 -name "*.usd" -path "*[Bb]ed*" | head -5

# 方式 C: 找任意一个中等大小的 USD 文件
find /cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all -maxdepth 3 -name "*.usd" | head -10
```

### Step 3：运行对比测试（约 10-15 分钟）

```bash
# 使用测试脚本（推荐，自动运行 3 组测试）
bash scripts/debug_camera_distance.sh /path/to/bed.usd

# 或者手动逐个运行：
# Test A: 基线
python -m render_usd.cli single --usd_path /path/to/bed.usd --output_dir ./test_outputs/debug_A --naming_style view --overwrite

# Test B: 跳过循环内 world.reset()
RENDER_SKIP_LOOP_RESET=1 python -m render_usd.cli single --usd_path /path/to/bed.usd --output_dir ./test_outputs/debug_B --naming_style view --overwrite

# Test C: 跳过 backgroundZeroAlpha + alpha 合成
RENDER_SKIP_ALPHA=1 python -m render_usd.cli single --usd_path /path/to/bed.usd --output_dir ./test_outputs/debug_C --naming_style view --overwrite
```

### Step 4：分析结果

1. **对比 [DEBUG-CAM] 日志**：三组测试的 bbox/distance 数值是否一致
2. **对比输出图片**：哪组的物体大小与旧渲染最接近
3. **根据第 6 节的判断逻辑**确定根因
4. 将结果反馈给 Claude Code 继续执行修复、清理和文档

### Step 5：修复与清理（由 Claude Code 执行）

确定根因后：
1. 实施正式修复（移除导致问题的代码或调整参数）
2. 删除所有 debug 代码（环境变量开关、[DEBUG-CAM] 日志）
3. 删除测试输出（test_outputs/debug_*）
4. 撰写最终调查报告（docs/design/camera-distance-fix-report.md）

## 相关文档

- [camera-distance-investigation-report.md](./camera-distance-investigation-report.md) — 问题调查报告（完整分析）
- [image-comparison-report.md](./image-comparison-report.md) — 新旧图片对比详情
- [git-history-camera-analysis.md](./git-history-camera-analysis.md) — Git 历史完整分析
- [camera-logic-analysis.md](./camera-logic-analysis.md) — 相机逻辑链路分析
- [a31f3ee-world-reset-analysis.md](./a31f3ee-world-reset-analysis.md) — world.reset commit 深度分析
- [commit-3c294a3-hdri-alpha-analysis.md](./commit-3c294a3-hdri-alpha-analysis.md) — HDRI/alpha commit 深度分析
- [with-bg-analysis.md](./with-bg-analysis.md) — render_thumbnail_with_bg 对比分析
