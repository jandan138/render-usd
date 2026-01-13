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

### 3. 本地测试 (Local Testing)
在提交到 DLC 之前，您可以在本地运行脚本以验证环境和渲染逻辑。

**渲染单个文件:**
```bash
bash scripts/dlc/run_task.sh single /path/to/asset.usd [output_dir]
```

**运行批量分块 (试运行):**
```bash
# 处理 100 个分块中的第 0 个 (将扫描资产但在本地机器上运行)
bash scripts/dlc/run_task.sh 0 100
```

**原位渲染 (In-place Rendering):**
如果希望将渲染图像保存在与 USD 文件相同的目录中（而不是单独的输出文件夹），请使用 "inplace" 作为保存目录参数：
```bash
bash scripts/dlc/run_task.sh 0 1 "/path/to/assets" "inplace"
```

### 4. DLC 环境变量配置

您可以在运行 `submit_batch.py` 之前通过设置环境变量来自定义作业提交。**务必**根据您的 DLC 环境验证这些值。

*   `DLC_WORKSPACE_ID`: 您的 DLC 工作区 ID (默认: `270969`)。
*   `DLC_RESOURCE_ID`: 资源配额 ID (默认: `quotalplclkpgjgv`)。
*   `DLC_IMAGE`: Docker 镜像地址 (默认: `pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118`)。
*   `DLC_CODE_ROOT`: 代码在容器中挂载的路径 (默认: `/cpfs/shared/simulation/zhuzihou/dev/render-usd`)。

### 数据源 (Data Sources)
`launch_job.sh` 脚本默认使用特定的数据源 ID：`d-phhmdh73h3zzv7pqh0,d-r70bzlwqnstu3rg55l,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz`。
请确保这些 ID 对您的数据集是正确的，或者将其作为第 4 个参数传递给 `launch_job.sh`。

## 示例

提交一批 30 个作业来渲染 GRScenes 数据集：

```bash
export DLC_CODE_ROOT=/root/render-usd
python scripts/dlc/submit_batch.py --total 30 --name grscenes_render
```
