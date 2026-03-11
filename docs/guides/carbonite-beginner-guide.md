# Carbonite (carb) 新手入门指南

> 适用于 Isaac Sim 4.x / Omniverse Kit 106.x
> 面向：使用 Isaac Sim Python API 的开发者，不需要 C++ 基础

## 目录

1. [一句话理解 Carbonite](#1-一句话理解-carbonite)
2. [Carbonite 在技术栈中的位置](#2-carbonite-在技术栈中的位置)
3. [为什么要了解 carb](#3-为什么要了解-carb)
4. [核心模块速查](#4-核心模块速查)
5. [carb.settings — 最常用的模块](#5-carbsettings--最常用的模块)
6. [carb 日志系统](#6-carb-日志系统)
7. [carb.tokens — 路径变量解析](#7-carbtokens--路径变量解析)
8. [carb.events — 事件系统](#8-carbevents--事件系统)
9. [启动顺序：为什么 carb 必须在 SimulationApp 之后用](#9-启动顺序为什么-carb-必须在-simulationapp-之后用)
10. [本项目中的 carb 使用](#10-本项目中的-carb-使用)
11. [常见问题](#11-常见问题)
12. [参考资料](#12-参考资料)

---

## 1. 一句话理解 Carbonite

**Carbonite 是 Omniverse 的"操作系统内核"** — 它提供插件加载、配置管理、日志、事件、文件系统等基础设施。所有 Omniverse 应用（Isaac Sim、USD Composer 等）都运行在它之上。

你不需要深入了解 Carbonite 的 C++ 内部实现，但需要知道如何使用它的 Python API（特别是 `carb.settings`），因为 **Isaac Sim 的几乎所有运行时配置都通过 carb.settings 管理**。

---

## 2. Carbonite 在技术栈中的位置

```
┌──────────────────────────────────────────────────┐
│              你的 Python 代码                     │
│    SimulationApp, render_usd 管道, 自定义脚本     │
├──────────────────────────────────────────────────┤
│           Isaac Sim 扩展 (87 个)                  │
│   isaacsim.core.api, isaacsim.sensors.camera 等   │
│   位置: /isaac-sim/exts/                          │
├──────────────────────────────────────────────────┤
│           物理引擎扩展 (35 个)                     │
│   omni.physx, omni.physics.tensors 等             │
│   位置: /isaac-sim/extsPhysics/                   │
├──────────────────────────────────────────────────┤
│        Omniverse Kit 扩展 (427 个)                │
│   渲染器、USD、UI、Replicator、动画、材质 等       │
│   位置: /isaac-sim/extscache/                     │
├──────────────────────────────────────────────────┤
│           Omniverse Kit 框架                      │
│   应用生命周期、扩展管理、USD Stage 管理           │
│   可执行文件: /isaac-sim/kit/kit                  │
├──────────────────────────────────────────────────┤
│       ★ Carbonite (carb) ★  ← 你在这里           │
│   插件系统、Settings、日志、事件、文件系统、        │
│   任务调度、性能分析、窗口管理、输入处理           │
│   核心库: /isaac-sim/kit/libcarb.so               │
│   插件: /isaac-sim/kit/kernel/plugins/            │
│   Python API: /isaac-sim/kit/kernel/py/carb/      │
├──────────────────────────────────────────────────┤
│           操作系统 / GPU 驱动 / CUDA              │
└──────────────────────────────────────────────────┘
```

**类比**：如果把 Isaac Sim 比作一台电脑——
- Carbonite = BIOS + 操作系统内核（启动、加载驱动、管理资源）
- Kit = 桌面环境（管理应用窗口、文件关联、系统设置面板）
- 扩展 = 应用程序（浏览器、编辑器、渲染器…各司其职）
- 你的 Python 代码 = 用户（使用应用来完成任务）

---

## 3. 为什么要了解 carb

作为 Isaac Sim 用户，你主要会在以下场景用到 carb：

| 场景 | 用到的 carb 功能 |
|------|-----------------|
| 配置渲染器参数（分辨率、采样数、光线反弹…） | `carb.settings` |
| 注册 MDL 材质搜索路径 | `carb.settings` |
| 启用/禁用透明背景 | `carb.settings` |
| 在代码中输出日志 | `carb.log_info/warn/error` |
| 解析 Omniverse 路径变量（`${kit}`、`${app}`…） | `carb.tokens` |
| 监听运行时配置变化 | `carb.settings` 订阅 |
| 响应仿真事件（播放/暂停/停止） | `carb.events` |

**90% 的使用场景是 `carb.settings`**。

---

## 4. 核心模块速查

| 模块 | 一句话说明 | 使用频率 |
|------|-----------|---------|
| `carb.settings` | 全局配置键值对树，用来读写所有运行时设置 | ★★★★★ |
| `carb.log_*` | 统一日志输出（自动带文件名、行号） | ★★★★ |
| `carb.tokens` | 解析路径变量（`${kit}` → `/isaac-sim/kit`） | ★★★ |
| `carb.events` | 事件发布/订阅系统 | ★★ |
| `carb.profiler` | 性能分析（`@carb.profiler.profile` 装饰器） | ★ |
| `carb.dictionary` | 底层嵌套字典（settings 的底层实现） | ★ |
| `carb.input` | 键盘/鼠标/手柄输入 | ★ |

---

## 5. carb.settings — 最常用的模块

### 5.1 基本概念

`carb.settings` 是一个**全局的层级键值对存储**，路径用正斜杠分隔（类似文件系统）：

```
/app/
  ├── renderer/
  │   ├── active           = "PathTracing"
  │   └── resolution/
  │       ├── width        = 1280
  │       └── height       = 720
  ├── mdl/
  │   ├── additionalSystemPaths = ["/path/to/mdl"]
  │   └── additionalUserPaths   = []
  └── window/
      └── title            = "Isaac Sim Python"
/rtx/
  ├── pathtracing/
  │   ├── spp              = 64
  │   └── maxBounces       = 4
  └── post/
      └── backgroundZeroAlpha/
          └── enabled      = true
```

Isaac Sim 的每个组件都通过这棵树来读写配置。你修改树上的值，对应的功能就会改变。

### 5.2 基本用法

```python
# ⚠️ 必须在 SimulationApp 初始化之后才能用！
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

# 获取 settings 单例
import carb.settings
settings = carb.settings.get_settings()

# === 读取 ===
width = settings.get("/app/renderer/resolution/width")          # → 1280
title = settings.get("/app/window/title")                       # → "Isaac Sim Python"
mdl_paths = settings.get("/app/mdl/additionalSystemPaths")      # → [...] 或 None

# 类型安全的读取（读取失败时返回默认值，不抛异常）
width = settings.get_as_int("/app/renderer/resolution/width")   # → 1280，失败返回 0
title = settings.get_as_string("/app/window/title")             # → "..."，失败返回 ""
enabled = settings.get_as_bool("/rtx/ecoMode/enabled")          # → False，失败返回 False

# === 写入 ===
settings.set("/app/renderer/resolution/width", 512)             # 自动推断类型
settings.set_int("/app/renderer/resolution/width", 512)         # 显式指定类型
settings.set_string("/app/window/title", "My App")
settings.set_bool("/rtx/post/backgroundZeroAlpha/enabled", True)

# 写入数组
settings.set_string_array("/app/mdl/additionalSystemPaths", [
    "/path/to/mdl/dir1",
    "/path/to/mdl/dir2",
])

# 只在值不存在时设置（不会覆盖已有值）
settings.set_default_int("/my/custom/setting", 42)

# === 删除 ===
settings.destroy_item("/some/temporary/setting")
```

### 5.3 监听配置变化

当你需要在某个设置被修改时自动执行代码：

```python
import carb.settings

settings = carb.settings.get_settings()

# 监听单个键
def on_change(item, event_type):
    if event_type == carb.settings.ChangeEventType.CHANGED:
        new_value = settings.get("/rtx/pathtracing/spp")
        print(f"SPP changed to: {new_value}")

sub = settings.subscribe_to_node_change_events(
    "/rtx/pathtracing/spp", on_change
)

# 监听整个子树
sub2 = settings.subscribe_to_tree_change_events(
    "/rtx/pathtracing/", on_change
)

# 取消监听（必须在不需要时调用，否则内存泄漏）
settings.unsubscribe_to_change_events(sub)
settings.unsubscribe_to_change_events(sub2)
```

### 5.4 常用 Settings 路径速查

| 路径 | 类型 | 说明 |
|------|------|------|
| `/app/renderer/resolution/width` | int | 渲染宽度 |
| `/app/renderer/resolution/height` | int | 渲染高度 |
| `/app/window/title` | string | 窗口标题 |
| `/app/mdl/additionalSystemPaths` | string[] | MDL 材质搜索路径 |
| `/persistent/app/stage/upAxis` | string | Stage 上方向（"Y" 或 "Z"） |
| `/rtx/pathtracing/spp` | int | 每像素采样数 |
| `/rtx/pathtracing/maxBounces` | int | 最大光线反弹次数 |
| `/rtx/post/backgroundZeroAlpha/enabled` | bool | 透明背景 |
| `/rtx/ecoMode/enabled` | bool | 省电模式 |
| `/physics/updateToUsd` | bool | 物理结果同步到 USD |

---

## 6. carb 日志系统

```python
import carb

carb.log_info("正常信息：加载了 42 个资产")
carb.log_warn("警告：找不到 HDRI 文件，使用默认灯光")
carb.log_error("错误：USD 文件不存在")
carb.log_verbose("调试：相机位置 = (1.0, 2.0, 3.0)")  # 仅在 verbose 模式显示
```

**输出格式**（自动包含来源信息）：
```
2026-03-11 10:30:00 [Info] [my_script.py:42] 正常信息：加载了 42 个资产
```

**vs `print()`**：`carb.log_*` 会写入 Omniverse 日志文件（`~/.nvidia-omniverse/logs/`），而 `print()` 只到标准输出。生产代码建议用 `carb.log_*`。

---

## 7. carb.tokens — 路径变量解析

Omniverse 内部大量使用 `${token}` 风格的路径变量。当你需要获取 Kit 安装路径、临时目录等时：

```python
import carb.tokens
tokens = carb.tokens.get_tokens_interface()

# 解析内置 token
kit_root = tokens.resolve("${kit}")       # → /isaac-sim/kit 的某个子目录
app_root = tokens.resolve("${app}")       # → /isaac-sim/apps
temp_dir = tokens.resolve("${temp}")      # → /tmp/carb.xxxxx
log_dir  = tokens.resolve("${logs}")      # → ~/.nvidia-omniverse/logs/...

# 解析环境变量
home = tokens.resolve("${env:HOME}")      # → /root

# 设置自定义 token
tokens.set_value("my_project", "/cpfs/shared/simulation/my_project")
resolved = tokens.resolve("${my_project}/data/assets")
# → "/cpfs/shared/simulation/my_project/data/assets"
```

**常用内置 Token**：

| Token | 解析为 |
|-------|--------|
| `${kit}` | Kit SDK 根目录 |
| `${app}` | 应用配置目录（.kit 文件所在） |
| `${temp}` | 临时目录 |
| `${logs}` | 日志目录 |
| `${data}` | 用户数据目录 |
| `${cache}` | 缓存目录 |
| `${env:VAR_NAME}` | 环境变量 |

---

## 8. carb.events — 事件系统

用于组件间通信。最常见的场景是监听仿真时间线事件：

```python
import carb.events
import omni.timeline

# 获取时间线事件流
timeline = omni.timeline.get_timeline_interface()
event_stream = timeline.get_timeline_event_stream()

# 订阅事件
def on_timeline_event(event: carb.events.IEvent):
    if event.type == int(omni.timeline.TimelineEventType.PLAY):
        print("仿真开始播放")
    elif event.type == int(omni.timeline.TimelineEventType.STOP):
        print("仿真停止")

sub = event_stream.create_subscription_to_pop(
    on_timeline_event,
    name="MyTimelineHandler"
)

# 取消订阅
sub = None  # 设为 None 即可自动取消
```

创建自定义事件流：

```python
import carb.events

# 创建事件流
events = carb.events.get_events_interface()
my_stream = events.create_event_stream("MyCustomEvents")

# 定义事件类型
MY_EVENT = carb.events.type_from_string("my_app@data_loaded")

# 发送事件
my_stream.push(MY_EVENT, {"file_count": 42, "path": "/data"})

# 订阅事件
def on_my_event(event: carb.events.IEvent):
    print(f"收到事件：{event.payload}")

sub = my_stream.create_subscription_to_pop(on_my_event)
```

---

## 9. 启动顺序：为什么 carb 必须在 SimulationApp 之后用

```python
# ❌ 这会崩溃（Carbonite 运行时还不存在）
import carb.settings
settings = carb.settings.get_settings()

# ✅ 正确顺序
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})   # ← 初始化 Carbonite + Kit + 所有扩展

import carb.settings                      # ← 现在 carb C++ 后端已经就绪
settings = carb.settings.get_settings()   # ← 可以使用
```

**`SimulationApp()` 内部做了什么**（简化版）：

```
SimulationApp.__init__()
  │
  ├─ 1. import carb（加载 Python binding）
  │
  ├─ 2. carb.get_framework().load_plugins(["omni.kit.app.plugin"])
  │     └── 初始化 Carbonite 运行时：
  │         ├── libcarb.settings.plugin.so   ← settings 系统启动
  │         ├── libcarb.events.plugin.so     ← 事件系统启动
  │         ├── libcarb.tokens.plugin.so     ← token 解析启动
  │         └── ... 其他核心插件
  │
  ├─ 3. omni.kit.app.get_app().startup()
  │     └── 读取 .kit 配置文件
  │         └── 加载所有扩展（渲染器、USD、物理引擎…）
  │
  └─ 4. 返回 → 你的代码可以开始使用 carb.* 和 omni.* 了
```

**关键约束**：步骤 2 之前 `carb.settings.get_settings()` 会段错误，因为 `libcarb.settings.plugin.so` 还没加载。这就是为什么所有 carb 调用必须在 `SimulationApp()` 之后。

---

## 10. 本项目中的 carb 使用

`render-usd` 项目在两个地方使用了 carb：

### 10.1 MDL 材质搜索路径注册（`cli.py`）

```python
# 在 SimulationApp 初始化之后
import carb.settings
settings = carb.settings.get_settings()
existing = settings.get("/app/mdl/additionalSystemPaths") or []
merged = list(existing)
for p in mdl_paths:
    if p not in merged:
        merged.append(p)
settings.set_string_array("/app/mdl/additionalSystemPaths", merged)
```

**作用**：把 GRScenes 的 `Material/mdl/` 目录注册到 MDL 搜索路径。这样 MDL 编译器在遇到 `import ::KooPbr::KooMtl` 时能找到 `KooPbr.mdl`。

等价于在命令行设置 `export MDL_SYSTEM_PATH=/path/to/Material/mdl`，但更可控（可以合并多个来源、去重、检查目录是否存在）。

### 10.2 透明背景配置（`scene.py`）

```python
settings = carb.settings.get_settings()
settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
settings.set("/app/captureFrame/setAlphaTo1", False)
```

**作用**：让 RTX 渲染器输出透明背景的 RGBA 图像，用于 HDRI 光照 + 暗背景的合成方案。

---

## 11. 常见问题

### Q: carb.settings 和环境变量有什么区别？

| | carb.settings | 环境变量 |
|---|---|---|
| 设置时机 | SimulationApp 之后，任意时刻 | 进程启动前 |
| 粒度 | 上千个路径，树形结构 | 扁平的键值对 |
| 动态修改 | 运行时可随时读写 | 运行时修改不影响已启动的子系统 |
| 监听变化 | 支持订阅回调 | 不支持 |
| 适用场景 | 运行时配置调整 | 启动时环境设置 |

对于 MDL 搜索路径，两者最终都是往同一个搜索列表里添加目录。`MDL_SYSTEM_PATH` 更简单，`carb.settings` 更灵活。

### Q: 如何查看当前所有的 settings 值？

```python
import carb.settings
settings = carb.settings.get_settings()

# 查看特定路径下的所有子项
# 目前没有直接的 "dump all" API，但可以查看已知路径：
for path in ["/app/renderer", "/rtx/pathtracing", "/app/mdl"]:
    print(f"{path} = {settings.get(path)}")
```

### Q: settings 的值从哪里来？

优先级从高到低：
1. **Python 代码** `settings.set(...)` — 运行时最高优先级
2. **命令行参数** `--/app/renderer/resolution/width=512`
3. **`.kit` 配置文件**（如 `isaacsim.exp.base.python.kit`）中的 `[settings]` 段
4. **扩展** `extension.toml` 中的 `[[settings]]` 段
5. **默认值**（硬编码在各组件中）

### Q: `set()` 和 `set_default()` 的区别？

```python
settings.set("/my/path", 42)           # 无条件覆盖
settings.set_default("/my/path", 42)   # 只在路径不存在时设置，已有值不覆盖
```

`set_default` 适合扩展初始化时设置默认配置，不会覆盖用户已经设置的值。

---

## 12. 参考资料

- [Carbonite SDK 官方文档](https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/index.html)
- [carb.settings API（Kit Manual）](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.settings.html)
- [Settings 开发者指南](https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/settings.html)
- [Kit 架构概述](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/kit_architecture.html)
- [Events 系统](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/events.html)
- [Carbonite 架构设计](https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/docs/Architecture.html)
- [本项目 MDL 修复报告](../design/mdl-material-fix-correction.md) — carb.settings 的实际应用案例
