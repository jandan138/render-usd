# DLC 脚本使用文档

[English](README.md)

本目录包含用于在深度学习集群 (DLC) 或基于 Kubernetes 的环境中提交和管理渲染作业的实用脚本。

## 脚本概览

### `launch_job.sh`
一个包装脚本，用于设置环境并执行单个作业块的渲染命令。

*   **用法**: `bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES]`
*   **作用**: 容器的入口点。它配置环境变量、PYTHONPATH，并执行 `run_task.sh`。

### `run_task.sh`
内部执行脚本，运行实际的 Python 渲染命令。

*   **用法**: `bash run_task.sh <CHUNK_ID> <CHUNK_TOTAL>`
*   **作用**: 激活 Conda 环境（如果需要），设置特定的环境变量（如 `OMNI_KIT_ACCEPT_EULA`），并调用 `python -m render_usd.cli`。

### `submit_batch.py`
一个 Python 脚本，用于自动向集群提交多个作业。

*   **用法**: `python submit_batch.py --total <TOTAL_CHUNKS> --name <TASK_NAME>`
*   **作用**: 循环遍历总块数，并为每个块调用 `dlc submit`（通过 `launch_job.sh`）。

## 环境要求

要使用这些脚本，您的集群环境必须满足以下条件：

1.  **DLC CLI**: 必须安装 `dlc` 命令行工具并配置有效的凭据。
2.  **挂载点**:
    *   **代码**: 仓库代码必须挂载到 `/cpfs/shared/simulation/zhuzihou/dev/render-usd`（或通过 `DLC_CODE_ROOT` 配置）。
    *   **数据**: 输入资产和输出目录必须可访问（例如 `/cpfs/user/...` 或 OSS 路径）。
3.  **Docker 镜像**: 有效的 Isaac Sim 镜像，支持 Python 环境（例如 `pj4090/yangsizhe:isaacsim41-cuda118`）。

## 配置

您可以在运行 `submit_batch.py` 之前通过设置环境变量来自定义作业提交：

*   `DLC_WORKSPACE_ID`: 您的 DLC 工作区 ID。
*   `DLC_RESOURCE_ID`: 资源配额 ID。
*   `DLC_IMAGE`: Docker 镜像地址。
*   `DLC_CODE_ROOT`: 代码在容器中挂载的路径。

## 示例

提交一批 30 个作业来渲染 GRScenes 数据集：

```bash
export DLC_CODE_ROOT=/root/render-usd
python scripts/dlc/submit_batch.py --total 30 --name grscenes_render
```
