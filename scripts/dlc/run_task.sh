#!/bin/bash
# 任务执行脚本 (run_task.sh)
# 该脚本在 DLC 容器内部运行，负责设置环境并执行 Python 渲染命令

# 定义代码根目录
# 默认为 /cpfs/shared/simulation/zhuzihou/dev/render-usd
# 该路径必须与 DLC 挂载路径或本地测试路径一致
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

# 设置环境 (Setup environment)
# 策略 1: 优先尝试使用项目目录下安装的 miniconda (最稳健的方式)
LOCAL_CONDA="$CODE_ROOT/miniconda/bin/activate"
if [ -f "$LOCAL_CONDA" ]; then
    # 如果找到了本地 conda 激活脚本
    echo "Found local miniconda at $LOCAL_CONDA, activating..."
    source "$LOCAL_CONDA" render-usd # 激活名为 render-usd 的环境
else
    # 策略 2: 如果本地 conda 不存在，尝试使用系统 conda (例如 Docker 镜像自带的)
    echo "Local miniconda not found, trying system conda..."
    # 尝试加载用户的 bashrc (如果有)
    if [ -f "/cpfs/user/caopeizhou/.bashrc" ]; then
        source /cpfs/user/caopeizhou/.bashrc
    fi
    # 初始化 conda shell hook
    eval "$(conda shell.bash hook)"
    # 尝试激活 render-usd 环境，如果失败则打印警告
    conda activate render-usd || echo "WARNING: Failed to activate render-usd env"
fi

# 3. 确保 render-usd 包已安装 (Ensure the package is installed)
# 检查是否能导入 render_usd 包
if ! python -c "import render_usd" &> /dev/null; then
    # 如果导入失败，说明未安装，执行 pip install -e . 安装
    echo "Package 'render-usd' not found in current environment. Installing..."
    pip install -e "$CODE_ROOT"
else
    # 如果导入成功，跳过安装
    echo "Package 'render-usd' is already installed."
fi

# 设置 Python 路径 (Setup Python path)
# 将 src 目录添加到 PYTHONPATH，确保可以直接导入模块
export PYTHONPATH=$PYTHONPATH:$CODE_ROOT/src
# 设置 Isaac Sim 相关的环境变量 (接受 EULA 协议)
export OMNI_KIT_ACCEPT_EULA=YES
# 设置 Python 输出无缓冲，确保日志实时打印
export PYTHONUNBUFFERED=1

# 检查运行模式 (Check mode)
# $1 是第一个参数，如果是 "single" 则进入单文件测试模式
if [ "$1" == "single" ]; then
    # 单文件模式 (Single file mode for testing)
    # 用法: bash run_task.sh single <usd_path> <output_dir>
    USD_PATH=$2 # 参数2: USD 文件路径
    # 参数3: 输出目录 (可选)，默认为 output_test_single
    OUTPUT_DIR=${3:-"$CODE_ROOT/output_test_single"}
    
    echo "Running Single Render Task: $USD_PATH"
    
    # 调用 Python CLI 执行单文件渲染
    python -m render_usd.cli single \
        --usd_path "$USD_PATH" \
        --output_dir "$OUTPUT_DIR"

else
    # 批量模式 (Batch mode) - DLC 默认模式
    CHUNK_ID=$1    # 参数1: 当前分块 ID
    CHUNK_TOTAL=$2 # 参数2: 总分块数
    
    # 参数3: 资产根目录 (可选)
    ASSETS_DIR=${3:-"/cpfs/shared/simulation/zhuzihou/assets/GRScenes100-for-render/GRScenes_assets"}
    # 参数4: 结果保存目录 (可选)
    SAVE_DIR=${4:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_dlc_result"}
    
    echo "Running Batch Render Task: Chunk $CHUNK_ID / $CHUNK_TOTAL"
    
    # 调用 Python CLI 执行 GRScenes100 批量渲染
    python -m render_usd.cli grscenes100 \
        --chunk_id $CHUNK_ID \
        --chunk_total $CHUNK_TOTAL \
        --assets_dir "$ASSETS_DIR" \
        --save_dir "$SAVE_DIR"
fi
