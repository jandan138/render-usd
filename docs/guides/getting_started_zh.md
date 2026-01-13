# 入门指南

[English](getting_started.md)

## 先决条件

在安装 `render-usd` 之前，请确保满足以下要求：

*   **操作系统**: Linux (推荐 Ubuntu 20.04+)
*   **硬件**: 支持 RTX 的 NVIDIA GPU (Isaac Sim 渲染必需)
*   **软件**:
    *   [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 或 Anaconda
    *   [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim) (本包设计为在 Isaac Sim python 环境中运行)

## 安装

### 1. 克隆仓库
```bash
git clone <repository_url>
cd render-usd
```

### 2. 设置 Conda 环境

建议使用专用的 Conda 环境来管理依赖。

```bash
# 从提供的 YAML 文件创建环境
conda env create -f environment.yml

# 激活环境
conda activate render-usd
```

### 3. 安装包

以可编辑模式安装包，以便开发更改立即生效。

```bash
pip install -e .
```

## 环境设置

渲染器依赖于某些资产（例如环境贴图、材质）。请确保这些文件放置在正确的目录中：

*   `assets/environments/`: 包含环境 USD 文件（例如 `background.usd`）。
*   `assets/materials/`: 包含 MDL 材质文件（例如 `default.mdl`）。

> **注意**: 如果缺少 `background.usd`，渲染器将自动回退到默认的圆顶光 (Dome Light)。
