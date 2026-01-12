# 使用指南

[English](usage.md)

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
