# 重构计划：Isaac Sim 渲染项目工程化

我将把 `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/object_rendering` 升级为一个标准的 Python 工程。

## 1. 推荐的项目目录结构

```text
render-usd/
├── README.md                   # 项目文档（安装、运行、目录说明）
├── environment.yml             # Conda 环境配置
├── pyproject.toml              # 项目包配置 (使得 render_usd 可被 pip install)
├── src/
│   └── render_usd/             # 核心源码包
│       ├── __init__.py
│       ├── cli.py              # 统一入口 (原 object_rendering.py 的入口逻辑)
│       ├── config.py           # 配置管理 (路径、默认值)
│       ├── core/               # 核心渲染逻辑
│       │   ├── __init__.py
│       │   └── renderer.py     # 渲染器类 (抽离 render_thumbnail_*)
│       └── utils/              # 工具函数 (原 utils 迁移至此)
│           ├── __init__.py
│           ├── common/
│           └── usd/
├── scripts/                    # 任务提交与辅助脚本
│   ├── dlc/
│   │   ├── launch_job.sh       # 通用 DLC 提交脚本 (原 launch_*.sh)
│   │   ├── run_task.sh         # DLC 内部运行入口 (原 render_*.sh)
│   │   └── submit_batch.py     # 批量提交工具 (原 submit_*.py)
│   └── local/
│       └── demo.sh             # 本地最小运行示例
└── assets/                     # (可选) 默认素材，如 background.usd
```

## 2. 模块职责说明

*   **`src/render_usd/cli.py`**:
    *   程序的唯一入口。
    *   负责初始化 `SimulationApp` (必须在导入 omni 模块前)。
    *   负责解析命令行参数 (`argparse`)。
    *   根据参数调用 `core` 中的渲染逻辑。
*   **`src/render_usd/core/renderer.py`**:
    *   包含 `render_thumbnail_wo_bg` 和 `render_thumbnail_with_bg` 的核心逻辑。
    *   接收明确的参数（路径、配置对象），不再依赖全局硬编码路径。
*   **`src/render_usd/config.py`**:
    *   定义默认路径常量 (如 `DEFAULT_MDL_PATH`)。
    *   管理不同数据集的配置映射。
*   **`src/render_usd/utils/`**:
    *   包含现有的 `common_utils` 和 `usd_utils`，调整 import 路径以适应新结构。
*   **`scripts/dlc/`**:
    *   **`launch_job.sh`**: 负责调用 `dlc` 命令行工具，参数化镜像、挂载点、资源ID。
    *   **`run_task.sh`**: 容器内执行的脚本，负责设置环境变量、安装/激活包、调用 `python -m render_usd.cli`。
    *   **`submit_batch.py`**: 负责生成 chunk ID 并循环调用 `launch_job.sh`。

## 3. 关键模块重构方案

### 3.1 入口 `src/render_usd/cli.py`
将 `SimulationApp` 的启动与参数解析分离。

```python
import argparse
import sys
import os
from pathlib import Path

# 1. 必须最先初始化 SimulationApp
from isaacsim import SimulationApp
CONFIG = {"headless": True, "anti_aliasing": 4, "multi_gpu": False, "renderer": "PathTracing"}

def main():
    parser = argparse.ArgumentParser(description="Render USD assets using Isaac Sim")
    parser.add_argument('--mode', type=str, choices=['grscenes', 'grscenes100'], required=True, help="Rendering mode/dataset")
    parser.add_argument('--chunk_id', type=int, default=0, help="Chunk ID for parallel rendering")
    parser.add_argument('--chunk_total', type=int, default=1, help="Total number of chunks")
    parser.add_argument('--input_dir', type=str, required=True, help="Root directory of assets")
    parser.add_argument('--output_dir', type=str, required=True, help="Directory to save results")
    # ... 其他参数
    args = parser.parse_args()

    # 启动 Isaac Sim
    kit = SimulationApp(CONFIG)

    # 2. 只有在 SimulationApp 启动后才能导入 omni 相关模块
    # 使用延迟导入或在 main 内部导入
    from render_usd.core.renderer import RenderManager
    from render_usd.utils.common.path_utils import find_all_files_in_folder
    
    try:
        renderer = RenderManager(kit)
        if args.mode == 'grscenes100':
            renderer.render_grscenes100(
                input_dir=Path(args.input_dir),
                output_dir=Path(args.output_dir),
                chunk_id=args.chunk_id,
                chunk_total=args.chunk_total
            )
        # ... 其他模式
    finally:
        kit.close()

if __name__ == "__main__":
    main()
```

### 3.2 渲染核心 `src/render_usd/core/renderer.py`
将原有函数封装进类或独立函数，去除硬编码。

```python
import os
from pathlib import Path
from tqdm import tqdm
import omni
from pxr import Usd
# ... 导入其他 utils ...

class RenderManager:
    def __init__(self, app):
        self.app = app

    def render_grscenes100(self, input_dir: Path, output_dir: Path, chunk_id: int, chunk_total: int):
        # 1. 获取所有资产列表
        # 2. 根据 chunk_id 切分
        # 3. 循环调用 render_thumbnail_wo_bg
        pass
        
    def render_thumbnail_wo_bg(self, object_usd_paths, save_root_dir, ...):
        # 原有逻辑，但要把 print 改为 logging (可选)，路径改为参数传入
        pass
```

## 4. 环境配置 `environment.yml`

```yaml
name: render-usd
channels:
  - defaults
dependencies:
  - python=3.10
  - pip
  - pip:
    - numpy
    - opencv-python
    - tqdm
    - natsort
    # 关键依赖
    - torch==2.4.0 --index-url https://download.pytorch.org/whl/cu118
    - isaacsim==4.1.0 --extra-index-url https://pypi.nvidia.com
    - isaacsim-extscache-physics==4.1.0 --extra-index-url https://pypi.nvidia.com
    - isaacsim-extscache-kit==4.1.0 --extra-index-url https://pypi.nvidia.com
    - isaacsim-extscache-kit-sdk==4.1.0 --extra-index-url https://pypi.nvidia.com
```

## 5. DLC 脚本改造方案

### 5.1 通用提交脚本 `scripts/dlc/launch_job.sh`
```bash
#!/bin/bash
# 接收参数：任务名, chunk_id, chunk_total, 挂载源, 输出路径等
TASK_NAME=$1
CHUNK_ID=$2
CHUNK_TOTAL=$3
DATA_SOURCE=$4

# 允许环境变量覆盖配置
WORKSPACE_ID=${DLC_WORKSPACE_ID:-"270969"}
IMAGE=${DLC_IMAGE:-"pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118"}

dlc submit pytorchjob \
    --name="${TASK_NAME}_${CHUNK_ID}" \
    --data_sources="${DATA_SOURCE}" \
    --command="bash /root/code/render-usd/scripts/dlc/run_task.sh ${CHUNK_ID} ${CHUNK_TOTAL}" \
    # ... 其他参数 ...
```

### 5.2 任务运行脚本 `scripts/dlc/run_task.sh`
```bash
#!/bin/bash
CHUNK_ID=$1
CHUNK_TOTAL=$2

# 设置环境
export PYTHONPATH=$PYTHONPATH:/root/code/render-usd/src
# 如果需要安装依赖
# pip install -e /root/code/render-usd

python -m render_usd.cli \
    --mode grscenes100 \
    --chunk_id $CHUNK_ID \
    --chunk_total $CHUNK_TOTAL \
    --input_dir /mnt/data/GRScenes-100 \
    --output_dir /mnt/output
```

确认计划后，我将开始创建文件并重构代码。