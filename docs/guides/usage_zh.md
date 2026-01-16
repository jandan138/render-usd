# 使用指南

[English](usage_en.md)

## 环境准备 (重要!)

在运行任何命令之前，必须先激活正确的环境并配置 Python 路径。否则会导致 `ModuleNotFoundError`。

**1. 激活 Conda 环境**
```bash
source miniconda/bin/activate render-usd
```

**2. 配置 PYTHONPATH**
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

> **注意**: 如果您使用的是 `scripts/dlc/run_task.sh`，脚本会自动处理这些步骤。但在手动执行 CLI 命令时，您**必须**手动执行上述操作。

## 命令行界面 (CLI)

该工具的主要入口点是 `src/render_usd/cli.py`。您可以使用 `python -m render_usd.cli` 来执行它。

### 单文件渲染

将单个 USD 文件渲染到指定的输出目录。

```bash
python -m render_usd.cli single \
    --usd_path /path/to/your/asset.usd \
    --output_dir /path/to/output
```

**参数**:
*   `--usd_path`: 目标 `.usd` 文件的绝对路径。
*   `--output_dir`: 保存渲染图像的目录。
*   `--naming_style`: 输出文件的命名方式。
    *   `index` (默认): `{object_name}_{idx}.png` (例如 `Chair_0.png`)
    *   `view`: `front.png`, `left.png`, `back.png`, `right.png`

### 自定义结构渲染

处理嵌套目录结构 (`Category/UID/usd/UID.usd`)，并将图片直接输出到 UID 目录 (`Category/UID/`)。

```bash
python -m render_usd.cli render_custom \
    --assets_dir /path/to/GRScenes_assets \
    --naming_style view
```

**参数**:
*   `--assets_dir`: 包含资产类别的根目录。
*   `--naming_style`: 同上 (默认为 `view`)。

## 输出文件说明

渲染器会为每个对象生成 4 张缩略图。

**默认命名 (`index`):**
*   **`_0.png`**: **前视图 (Front)** (方位角 0°, +X 轴)
*   **`_1.png`**: **左视图 (Left)** (方位角 90°, +Y 轴)
*   **`_2.png`**: **后视图 (Back)** (方位角 180°, -X 轴)
*   **`_3.png`**: **右视图 (Right)** (方位角 270°, -Y 轴)

**语义命名 (`view`):**
*   **`front.png`**: 前视图
*   **`left.png`**: 左视图
*   **`back.png`**: 后视图
*   **`right.png`**: 右视图

> 注意：所有视角均以 **35° 俯仰角 (Elevation)** 拍摄。

### 批量渲染 (待定)

*目前正在开发中。*

## DLC 任务提交

对于集群（使用 DLC/Kubernetes）上的大规模渲染任务，请使用 `scripts/dlc/` 中提供的脚本。

### 1. 启动作业 (`launch_job.sh`)
此脚本封装了单文件渲染命令。

```bash
bash scripts/dlc/launch_job.sh <usd_path> <output_dir>
```

### 2. 提交批处理 (`submit_batch.py`)
向集群提交多个作业。

```bash
python scripts/dlc/submit_batch.py --input_list assets_list.txt
```

**DLC 先决条件**:
*   确保您的集群环境可以访问 `render-usd` 代码和必要的卷。
*   在 `scripts/dlc/config.json` 中配置您的 DLC 凭据和端点（如果适用）。
