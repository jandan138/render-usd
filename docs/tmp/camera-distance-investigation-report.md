# 相机距离/视角变化调查报告

## 问题描述

新渲染结果（2026-03-05）中物体显示过近，无法展示全貌。以 bed 类别为例：
- **旧渲染**（GRScenes-test1_bak，2026-01-19）：完整展示整张床，约占画面 60-65%
- **新渲染**（GRScenes-test1，2026-03-05）：仅看到床面布料特写，几乎填满画面

问题在所有资产类别中均有出现，严重程度与物体尺寸成正比。

## 调查结论

### 已确认排除的因素

| 排查项 | 结论 |
|--------|------|
| 距离公式 `distance = bbox_diagonal * 1.0` | **从未改过**，初始提交至今完全相同 |
| `compute_bbox` (ComputeWorldBound) | **从未改过** |
| `set_camera_look_at` 球坐标数学 | **从未改过** |
| 相机参数 (focal_length=18, apertures) | **从未改过** |
| USD 文件本身 | MD5 校验 **完全一致** (8dcba7a5d085333260c95386f36633d4) |
| 图片分辨率 | 均为 512×512 |
| `np.clip(distance, 0.1, 100.0)` | 床的 bbox 对角线 ~2.51m，不受 clamp 影响 |

### 代码变化时间线

| 日期 | Commit | 改动 | 影响距离？ |
|------|--------|------|-----------|
| 01-19 | f0f4777 | 添加 render_custom 命令 | 否 |
| 03-04 | 3c294a3 | HDRI灯光 + backgroundZeroAlpha + RGBA合成 | **待验证** |
| 03-04 | a31f3ee | DLC crash fix: 添加 `world.reset()` + `np.clip` | **待验证** |
| 03-05 | 8c1eb14 | 移除重复代码块 | 否 |

### 关键差异：两个可疑改动

#### 1. `world.reset()` 在每个物体前调用 (a31f3ee)

**旧代码流程**（1月19日）:
```
init_world() → world.reset()  # 仅此一次
setup_environment()  # 创建 DomeLight
for each object:
    create_prim → compute_bbox → render → delete_prim
```

**新代码流程**（3月5日）:
```
init_world() → world.reset()
setup_environment()  # 创建 DomeLight + HDRI + backgroundZeroAlpha
for each object:
    world.reset()  ← 每次循环都 reset！
    create_prim → compute_bbox → render → delete_prim
```

`world.reset()` 可能重置 DomeLight 或其他场景状态，导致后续渲染行为异常。

#### 2. backgroundZeroAlpha + RGBA 合成 (3c294a3)

旧代码直接用 `get_rgb()`（取 RGBA 丢弃 alpha），新代码启用 `backgroundZeroAlpha` 后用 RGBA + alpha 合成到深灰背景。RTX `backgroundZeroAlpha` 设置可能影响 PathTracing 渲染器的行为。

### 运行环境差异

- **旧渲染**（01-19）：1月19日的 run_task.sh **不支持 render_custom 模式**，因此旧渲染大概率是**本地 dev 机器**直接执行的
- **新渲染**（03-05）：通过 DLC 集群执行（Docker image: `isaacsim41-cuda118`）
- 两者使用相同的 CPFS conda 环境 (`miniconda/bin/activate render-usd`)，但 DLC 容器的 Isaac Sim 版本可能与本地不同

## 建议验证步骤

### 方案 A：回滚代码验证（最快）

1. checkout 到 f0f4777（01-19 版本）
2. 在当前环境渲染同一个 bed 资产
3. 对比结果是否与旧渲染一致
4. 如果一致→确认是代码改动导致
5. 如果不一致→确认是环境差异导致

### 方案 B：逐步排查

1. **测试 world.reset() 影响**：注释掉循环中的 `world.reset()`，渲染对比
2. **测试 backgroundZeroAlpha 影响**：禁用 HDRI/alpha 相关设置，使用旧版简单 DomeLight
3. **增大距离系数**：临时把 `* 1.0` 改为 `* 1.5`，验证是否能恢复旧效果

### 方案 C：添加 debug 日志

在 `render_thumbnail_wo_bg` 中添加打印：
```python
print(f"[DEBUG] {object_name}: bbox_min={bbox_min}, bbox_max={bbox_max}, distance={distance}")
```
对比旧/新环境下同一 USD 文件的 bbox 和 distance 值。

## 相关文档

- `docs/tmp/image-comparison-report.md` — 新旧图片对比详情
- `docs/tmp/git-history-camera-analysis.md` — Git 历史完整分析
- `docs/tmp/camera-logic-analysis.md` — 相机逻辑链路分析
