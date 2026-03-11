# MDL 材质搜索路径修复 — 技术报告

> 日期: 2026-03-04
> 状态: 已实现并测试（DLC 任务 `dlc1k9aayxi3arv6`）
>
> **⚠️ 根因分析修正 (2026-03-11)**：本文第 3 节的根因分析有误。实际上 USD 文件中的 MDL 相对路径（`../../../../Material/mdl/`，4 级）是正确的，能正常解析。泛红的真正原因是 KooPbr 自定义 MDL 模块（`::KooPbr::KooMtl`）不在 Isaac Sim 默认搜索路径中，而 OmniUe4 模块是内置的所以不受影响。详见 **[修正报告](./mdl-material-fix-correction.md)**。

**[English Version](./mdl-material-fix.md)**

## 目录

1. [问题描述](#1-问题描述)
2. [背景：什么是 MDL？](#2-背景什么是-mdl)
3. [根因分析](#3-根因分析)
4. [方案设计](#4-方案设计)
5. [实现细节](#5-实现细节)
6. [测试与验证](#6-测试与验证)
7. [使用指南](#7-使用指南)
8. [常见问题](#8-常见问题)

---

## 1. 问题描述

### 现象

使用 `render-usd` 管道渲染 GRScenes-test1 USD 资产时，**所有物体显示为纯红色** — 这是 NVIDIA Isaac Sim / Omniverse 中 MDL 材质解析失败的明显信号。

问题文件示例：
```
/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/
  GRScenes_assets/microwave/23fa2734dd917d97b308fbe494284597/usd/
  23fa2734dd917d97b308fbe494284597.usd
```

### 关键发现

用户发现了一个临时解决方案：如果在启动 Isaac Sim **之前**设置 `MDL_SYSTEM_PATH` 环境变量，材质可以正确加载：

```bash
# 在启动 Isaac Sim 之前设置这个变量
export MDL_SYSTEM_PATH=/isaac-sim/materials/:/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials:

# 然后启动 Isaac Sim UI —— 材质正确渲染
/isaac-sim/isaac-sim.sh --allow-root
```

这确认了问题出在 **MDL 搜索路径解析**，而不是材质文件损坏。

---

## 2. 背景：什么是 MDL？

### 一句话解释 MDL

**MDL（Material Definition Language）** 是 NVIDIA 的开源材质定义语言。可以把它想象成"着色器编程语言" —— 每个 `.mdl` 文件描述了光线如何与表面交互（颜色、粗糙度、金属度、透明度等）。

### Isaac Sim 如何查找 MDL 文件

当 Isaac Sim 加载一个引用了 MDL 材质的 USD 文件时，它需要在磁盘上定位到实际的 `.mdl` 文件。搜索顺序如下：

```
1. 从 USD 文件位置的相对路径
   例如，USD 位于 /a/b/c.usd，引用 ./Materials/mat.mdl
         → 查找 /a/b/Materials/mat.mdl

2. MDL_SYSTEM_PATH 环境变量（冒号分隔的目录）
   例如，MDL_SYSTEM_PATH=/path1:/path2
         → 查找 /path1/mat.mdl，然后 /path2/mat.mdl

3. Isaac Sim 内置 MDL 路径
   例如，/isaac-sim/materials/
         → 标准 NVIDIA 材质库

4. carb.settings: /app/mdl/additionalSystemPaths
   → MDL_SYSTEM_PATH 的编程等效方式
```

### MDL 解析失败时会发生什么？

当 MDL 编译器找不到被引用的 `.mdl` 文件时，Omniverse 会用**纯红色错误材质**来渲染物体。这是一个故意的视觉信号，表示"出问题了" —— 不是微妙的 bug，而是直接告诉你"我找不到你的材质"。

---

## 3. 根因分析

### 3.1 USD 文件引用了什么

在 microwave USD 文件内部，我们找到了 13 个 MDL 材质引用，类似这样：

```usda
# 在 USD 文件内部
asset inputs:mdl_file = @./Materials/MI_DefaultMaterial_5b7cc2b6b53276768d3b1abc.mdl@
```

这些 MDL 文件又依赖于自定义的 MDL 模块：
- `KooPbr::KooMtl` — 基础材质着色器
- `KooPbr_maps::KooPbr_falloff` — 纹理映射工具

### 3.2 目录结构不匹配

根本原因是原始 GRScenes-100 数据集与重组后的 GRScenes-test1 版本之间的**目录结构变化**：

**原始 GRScenes-100（正常工作）：**
```
home_scenes/
├── Materials/              ← MDL 文件在这里（1679 个文件）
│   ├── MI_DefaultMaterial_xxx.mdl
│   ├── KooPbr.mdl
│   └── ...
└── microwave/
    └── <uid>/
        ├── instance.usd    ← 引用 ./Materials/MI_xxx.mdl
        └── Materials -> ../../../../../Materials  ← 符号链接存在！
```

符号链接 `Materials -> ../../../../../Materials` 使得相对路径 `./Materials/MI_xxx.mdl` 能正确解析。

**GRScenes-test1（损坏）：**
```
GRScenes-test1/
├── Material/               ← 注意：是 "Material" 而不是 "Materials"
│   └── mdl/                ← 额外的子目录层级！
│       ├── MI_DefaultMaterial_xxx.mdl
│       ├── KooPbr.mdl
│       └── ...
└── GRScenes_assets/
    └── microwave/
        └── <uid>/
            └── usd/
                ├── <uid>.usd      ← 引用 ./Materials/MI_xxx.mdl
                ├── textures -> ... ← 纹理符号链接存在
                └── (没有 Materials 符号链接！)  ← 缺失！
```

**三个问题：**

| 问题 | 原始 | GRScenes-test1 |
|---|----------|----------------|
| 符号链接 | `Materials -> ../../../../../Materials` 存在 | **缺失** |
| 目录名 | `Materials/` | `Material/`（没有 "s"） |
| 结构 | `Materials/MI_xxx.mdl` | `Material/mdl/MI_xxx.mdl`（多一层） |

重组时创建了纹理文件的 `textures` 符号链接，但**忘记创建 MDL 文件的 `Materials` 符号链接**。即使符号链接存在，目录命名变化（`Materials/` → `Material/mdl/`）仍然会破坏它。

### 3.3 为什么 MDL_SYSTEM_PATH 能修复它

当你设置 `MDL_SYSTEM_PATH` 包含 `.mdl` 文件的目录时：

```bash
export MDL_SYSTEM_PATH=/cpfs/.../home_scenes/Materials:
```

MDL 编译器会将此目录添加到其搜索路径。当遇到 `MI_DefaultMaterial_xxx.mdl` 时，它：
1. 首先尝试相对路径 `./Materials/MI_xxx.mdl` → **失败**（没有符号链接）
2. 然后搜索 `MDL_SYSTEM_PATH` 目录 → **在** `home_scenes/Materials/` 中找到它
3. 材质成功加载 → 物体以正确外观渲染

### 3.4 之前的临时方案（Material 符号链接）

在早期开发中，我们在项目根目录创建了一个符号链接：
```
render-usd/Material -> usd-scene-physics-prep/GRScenes-test1/Material
```

这种方式很脆弱，因为：
- 它只在 USD 文件从特定相对路径加载时才有效
- 切换机器或重新配置 DLC 节点时，符号链接会丢失
- 它不能解决命名不匹配（`Materials/` vs `Material/mdl/`）

---

## 4. 方案设计

### 设计目标

1. **可靠**：必须在本地开发和 DLC 容器环境都有效
2. **无符号链接**：不依赖可能丢失的文件系统符号链接
3. **可配置**：允许添加新的 MDL 搜索路径而无需修改代码
4. **非破坏性**：必须保留 Isaac Sim 内置材质路径
5. **简单**：最少的代码更改，不过度设计

### 方法：双层 MDL 路径注册

我们在**两个独立层**实现 MDL 搜索路径，以获得最大可靠性：

```
┌─────────────────────────────────────────────┐
│                    层 1：Shell                    │
│   run_task.sh 导出 MDL_SYSTEM_PATH                │
│   (环境变量，Isaac Sim 启动时读取)             │
├─────────────────────────────────────────────┤
│                   层 2：Python                     │
│   cli.py 调用 carb.settings API                     │
│   /app/mdl/additionalSystemPaths                     │
│   (编程方式，SimulationApp 初始化后)            │
└─────────────────────────────────────────────┘
```

**为什么两层？**
- 环境变量（`MDL_SYSTEM_PATH`）作为**安全网** —— 它是最简单、最通用的机制
- `carb.settings` API 是**官方 Omniverse 方式** —— 更精确，可以动态配置
- 如果任一层失败，另一层仍然提供 MDL 路径

### 路径收集优先级

来自三个来源的所有 MDL 路径被**合并**（不是覆盖）：

```
1. --mdl_paths CLI 参数     ← 用户显式传递路径
2. MDL_SYSTEM_PATH 环境变量      ← 在 shell 或 run_task.sh 中设置
3. DEFAULT_MDL_SEARCH_PATHS     ← settings.py 中硬编码的已知良好默认值
```

重复路径会被去重。不存在的路径会被静默跳过。

### 为什么用 carb.settings 而不是只用 MDL_SYSTEM_PATH？

我们在 Isaac Sim 自己的源代码（`omni.mdl.usd_converter`）中找到了完全相同的模式：

```python
# 来自 /isaac-sim/extscache/omni.mdl.usd_converter-1.0.24+d02c707b/
# omni/mdl/usd_converter/usd_converter.py:40-47
import carb.settings
settings = carb.settings.get_settings()
mdl_paths = settings.get("/app/mdl/additionalSystemPaths") or []
mdl_paths.append(new_path)
settings.set_string_array("/app/mdl/additionalSystemPaths", mdl_paths)
```

这是 NVIDIA 内部使用的相同机制 —— 是最可靠的方法。

---

## 5. 实现细节

### 5.1 `src/render_usd/config/settings.py` — 默认路径

```python
# GRScenes 材质解析的默认 MDL 搜索路径
# 这些目录包含 GRScenes USD 资产所需的 MI_*.mdl 文件和 KooPbr 模块
DEFAULT_MDL_SEARCH_PATHS = [
    "/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl",
    "/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials",
]
```

默认配置了两个路径 —— 两者都包含相同的 GRScenes MDL 文件集（1679-1725 个文件）。有两个可以确保当一个位置不可用时提供冗余。

### 5.2 `src/render_usd/cli.py` — 核心逻辑

在 CONFIG 定义和 `main()` 之间添加了两个新函数：

**`_collect_mdl_paths(cli_paths)`** — 从三个来源合并 MDL 路径：
```python
def _collect_mdl_paths(cli_paths):
    """从 CLI 参数、环境变量和默认值收集 MDL 搜索路径。"""
    paths = []
    seen = set()

    def _add(p):
        p = os.path.abspath(p)
        if p not in seen and os.path.isdir(p):  # 只包含存在的目录
            seen.add(p)
            paths.append(p)

    # 1. CLI 路径（最高优先级）
    if cli_paths:
        for p in cli_paths:
            _add(p)

    # 2. 环境变量（冒号分隔）
    env_val = os.environ.get("MDL_SYSTEM_PATH", "")
    if env_val:
        for p in env_val.split(":"):
            if p.strip():
                _add(p.strip())

    # 3. settings.py 中的默认值
    for p in DEFAULT_MDL_SEARCH_PATHS:
        _add(p)

    return paths
```

**`_configure_mdl_search_paths(mdl_paths)`** — 通过 carb.settings 注册路径：
```python
def _configure_mdl_search_paths(mdl_paths):
    """在 SimulationApp 初始化后通过 carb.settings 注册 MDL 搜索路径。"""
    if not mdl_paths:
        return

    import carb.settings  # 必须在 SimulationApp 初始化后导入
    settings = carb.settings.get_settings()
    existing = settings.get("/app/mdl/additionalSystemPaths") or []
    merged = list(existing)
    for p in mdl_paths:
        if p not in merged:
            merged.append(p)
    settings.set_string_array("/app/mdl/additionalSystemPaths", merged)
    print(f"[CLI] MDL 搜索路径已配置: {merged}")
```

**`main()` 中的执行顺序：**
```python
def main():
    # 1. 解析参数（包括 --mdl_paths）
    args = parser.parse_args()

    # 2. 在 SimulationApp 初始化之前收集 MDL 路径
    #    （从环境变量 + 默认值读取）
    mdl_paths = _collect_mdl_paths(args.mdl_paths)

    # 3. 初始化 Isaac Sim
    kit = SimulationApp(CONFIG)

    # 4. 通过 carb.settings 在 SimulationApp 之后配置 MDL 路径
    #    （carb 模块只在 SimulationApp 初始化后可用）
    _configure_mdl_search_paths(mdl_paths)

    # 5. 导入渲染模块并继续...
    from render_usd.core.renderer import RenderManager
    renderer = RenderManager(kit)
    # ... 渲染 USD 文件 —— MDL 材质现在可以正确解析
```

**为什么这个顺序很重要：**
- `carb.settings` 是 Omniverse 运行时的一部分，它只在 `SimulationApp()` 初始化 Omniverse Kit 内核后**才可用**
- 但我们需要在 `SimulationApp()` **之前**收集路径（从环境变量、CLI 参数、settings.py），因为这只是纯 Python —— 没有 Omniverse 依赖
- 实际的 `carb.settings.set_string_array()` 调用必须在 `SimulationApp()` **之后**但**任何 USD stage 加载之前**

### 5.3 `scripts/dlc/run_task.sh` — 环境变量兜底

```bash
# 设置 MDL 搜索路径（与 cli.py 中的 carb.settings 方案配合，作为双保险）
MDL_PATHS="/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl"
MDL_PATHS="$MDL_PATHS:/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials"
export MDL_SYSTEM_PATH="${MDL_SYSTEM_PATH:+$MDL_SYSTEM_PATH:}$MDL_PATHS"
echo "MDL_SYSTEM_PATH=$MDL_SYSTEM_PATH"
```

`${MDL_SYSTEM_PATH:+$MDL_SYSTEM_PATH:}` 语法意思是：如果 `MDL_SYSTEM_PATH` 已经设置，用冒号分隔符在其值前面追加；否则从头开始。这会保留任何预先存在的路径。

---

## 6. 测试与验证

### 测试计划

| 步骤 | 操作 | 预期结果 |
|---|--------|-----------------|
| 1 | 提交之前渲染全红的相同 microwave USD 的 DLC 任务 | 材质正确渲染（不再红色） |
| 2 | 检查任务日志中出现 `[CLI] MDL 搜索路径已配置: [...]` | 确认 carb.settings 路径注册 |
| 3 | 验证输出 PNG 显示正确的 microwave 外观 | 视觉确认 |

### DLC 测试任务

```bash
# 提交的测试任务
bash scripts/dlc/launch_job.sh \
  test_mdl_fix 0 1 \
  "d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz" \
  "single /cpfs/.../microwave/23fa2734dd917d97b308fbe494284597/usd/23fa2734dd917d97b308fbe494284597.usd /cpfs/.../render-usd/output_test_mdl_fix"
```

- **任务名称**: `test_mdl_fix_0_1`
- **任务 ID**: `dlc1k9aayxi3arv6`
- **输出目录**: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_test_mdl_fix/`

### 验证命令

```bash
# 检查是否生成了输出图像
ls /cpfs/shared/simulation/zhuzihou/dev/render-usd/output_test_mdl_fix/

# 预期：4 个 PNG 文件（microwave 的前、左、后、右视角）
```

---

## 7. 使用指南

### 默认行为（最常见）

对于 GRScenes 资产，**无需额外配置**。`settings.py` 中的默认路径会自动注册：

```bash
# 照常运行即可 —— MDL 路径自动配置
python -m render_usd.cli single --usd_path /path/to/grscenes/asset.usd --output_dir ./output
```

### 通过 CLI 自定义 MDL 路径

如果你的 MDL 文件在非默认位置：

```bash
python -m render_usd.cli \
  --mdl_paths /path/to/custom/mdl/dir /another/mdl/dir \
  single --usd_path /path/to/asset.usd --output_dir ./output
```

注意：`--mdl_paths` 必须位于子命令（`single`、`grscenes100` 等）**之前**。

### 通过环境变量自定义 MDL 路径

```bash
export MDL_SYSTEM_PATH="/path/to/mdl/dir1:/path/to/mdl/dir2"
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output
```

### 添加永久默认路径

编辑 `src/render_usd/config/settings.py`：

```python
DEFAULT_MDL_SEARCH_PATHS = [
    "/cpfs/.../existing/path",
    "/cpfs/.../your/new/mdl/directory",  # 在这里添加新路径
]
```

---

## 8. 常见问题

### Q: 为什么不直接重建 Materials 符号链接？

符号链接很脆弱：
- 切换机器或重新配置 DLC 容器时会丢失
- 只对从特定相对路径加载的文件有效
- 不能解决命名不匹配（`Materials/` vs `Material/mdl/`）
- 跨不同数据集版本时难以维护

`carb.settings` 方式是**无符号链接、到处可用、且是 NVIDIA 官方机制**。

### Q: 这会减慢渲染速度吗？

不会。MDL 路径注册在启动时发生一次（在所有渲染之前）。MDL 编译器会缓存已解析的路径，后续材质查找很快。

### Q: 如果我添加一个不存在的路径会怎样？

它会被静默跳过。`_collect_mdl_paths()` 函数检查 `os.path.isdir(p)` 并且只包含实际存在于磁盘上的目录。

### Q: 是否需要环境变量和 carb.settings 两种方式？

技术上，任何一种单独都应该可以工作。我们使用两种作为"双保险"策略：
- 环境变量确保 MDL 路径在最早可能时刻可用（Python 甚至启动前）
- `carb.settings` 调用确保路径通过官方 API 注册

### Q: 能否用于非 GRScenes 资产？

可以。`--mdl_paths` CLI 参数和 `MDL_SYSTEM_PATH` 环境变量适用于任何数据集。只需将它们指向包含你的 `.mdl` 文件的目录即可。

---

## 修改的文件

| 文件 | 更改 |
|---|--------|
| `src/render_usd/config/settings.py` | 添加 `DEFAULT_MDL_SEARCH_PATHS` 列表 |
| `src/render_usd/cli.py` | 添加 `_collect_mdl_paths()`、`_configure_mdl_search_paths()`、`--mdl_paths` CLI 参数 |
| `scripts/dlc/run_task.sh` | 添加 `MDL_SYSTEM_PATH` 环境变量导出 |
