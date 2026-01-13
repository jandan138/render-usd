# 架构概览

[English](architecture.md)

## 系统设计

`render-usd` 是一个基于 NVIDIA Isaac Sim Python API 构建的模块化渲染管线。它将场景管理、相机控制和高层渲染流程分离开来。

### 核心模块

核心逻辑位于 `src/render_usd/core/`：

1.  **[Renderer](api/core_zh.md#renderer)** (`renderer.py`):
    *   **角色**: 编排者 (Orchestrator)。
    *   **职责**: 管理主渲染循环，协调 Scene 和 Camera 模块，处理文件 I/O，并执行渲染步骤。
    *   **核心类**: `RenderManager`

2.  **[Scene](api/core_zh.md#scene)** (`scene.py`):
    *   **角色**: 舞台管理者 (Stage Manager)。
    *   **职责**: 初始化 Isaac Sim `World`，加载 USD 舞台，设置环境光照 (Dome Light/HDRI)，并管理对象语义。

3.  **[Camera](api/core_zh.md#camera)** (`camera.py`):
    *   **角色**: 传感器管理者 (Sensor Manager)。
    *   **职责**: 创建和配置相机，处理坐标变换（注视点逻辑），并提取传感器数据（RGB、深度、边界框）。

## 目录结构

```
render-usd/
├── assets/                 # 外部资产（环境、材质）
├── docs/                   # 文档（即当前位置）
├── examples/               # 示例 USD 文件和输出
├── scripts/                # 实用脚本（DLC 提交、批处理）
├── src/
│   └── render_usd/
│       ├── config/         # 配置设置
│       ├── core/           # 核心渲染模块 (renderer, scene, camera)
│       └── utils/          # 辅助工具 (USD, images, math)
├── environment.yml         # Conda 环境定义
└── pyproject.toml          # 项目元数据
```

## 数据流

1.  **输入**: 用户通过 CLI 提供 USD 文件或目录的路径。
2.  **初始化**: `RenderManager` 通过 `Scene` 模块初始化 `World`。
3.  **设置**:
    *   `Scene` 加载 USD 舞台并设置光照。
    *   `Camera` 根据配置初始化传感器。
4.  **渲染循环**:
    *   `RenderManager` 遍历定义的视点。
    *   `Camera` 更新位姿（位置/方向）。
    *   `World` 步进物理/渲染模拟。
5.  **提取**: `Camera` 提取渲染产物（RGB 图像、BBox 数据）。
6.  **输出**: 图像和元数据保存到指定的输出目录。
