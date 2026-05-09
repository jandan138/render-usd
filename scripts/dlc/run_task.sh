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

# 设置 MDL 材质搜索路径 (MDL material search paths for GRScenes)
# Python CLI also configures this via carb.settings; env var provides a fallback
MDL_PATHS="/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/Material/mdl"
MDL_PATHS="$MDL_PATHS:/cpfs/shared/simulation/liyangzi/grutopia/assets/scenes/GRScenes-100/home_scenes/Materials"
export MDL_SYSTEM_PATH="${MDL_SYSTEM_PATH:+$MDL_SYSTEM_PATH:}$MDL_PATHS"
echo "MDL_SYSTEM_PATH=$MDL_SYSTEM_PATH"

# 检查运行模式 (Check mode)
# $1 是第一个参数，决定运行哪种渲染模式
if [ "$1" == "single" ]; then
    # 单文件模式 (Single file mode for testing)
    # 用法: bash run_task.sh single <usd_path> [output_dir]
    USD_PATH=$2
    OUTPUT_DIR=${3:-"$CODE_ROOT/output_test_single"}

    echo "Running Single Render Task: $USD_PATH"

    python -m render_usd.cli single \
        --usd_path "$USD_PATH" \
        --output_dir "$OUTPUT_DIR"

elif [ "$1" == "render_custom" ]; then
    # 自定义目录渲染模式 (Custom directory structure rendering)
    # 用法: bash run_task.sh render_custom <assets_dir> [naming_style] [chunk_id] [chunk_total] [overwrite]
    # 资产结构: assets_dir/Category/UID/usd/UID.usd
    ASSETS_DIR=$2
    NAMING_STYLE=${3:-"view"}
    CHUNK_ID=${4:-0}
    CHUNK_TOTAL=${5:-1}
    OVERWRITE=${6:-""}

    echo "Running Render Custom Task: $ASSETS_DIR (naming: $NAMING_STYLE, chunk: $CHUNK_ID/$CHUNK_TOTAL, overwrite: ${OVERWRITE:-false})"

    # 验证 assets_dir 存在
    if [ ! -d "$ASSETS_DIR" ]; then
        echo "ERROR: Assets directory does not exist: $ASSETS_DIR"
        exit 1
    fi

    # 直接执行，避免 eval 命令注入风险
    python -m render_usd.cli render_custom \
        --assets_dir "$ASSETS_DIR" \
        --naming_style "$NAMING_STYLE" \
        --chunk_id "$CHUNK_ID" \
        --chunk_total "$CHUNK_TOTAL" \
        ${OVERWRITE:+--overwrite}

elif [ "$1" == "render_manifest" ]; then
    # Manifest subset rendering mode
    # Usage: bash run_task.sh render_manifest <manifest_csv> <output_root> [chunk_id] [chunk_total] [overwrite]
    if [ $# -lt 3 ]; then
        echo "Usage: bash run_task.sh render_manifest <manifest_csv> <output_root> [chunk_id] [chunk_total] [overwrite]"
        exit 1
    fi

    MANIFEST_CSV=$2
    OUTPUT_ROOT=$3
    CHUNK_ID=${4:-0}
    CHUNK_TOTAL=${5:-1}
    OVERWRITE=${6:-""}
    OVERWRITE_FLAG=""

    if [ "$OVERWRITE" == "true" ] || [ "$OVERWRITE" == "--overwrite" ]; then
        OVERWRITE_FLAG="--overwrite"
    elif [ -n "$OVERWRITE" ] && [ "$OVERWRITE" != "false" ]; then
        echo "ERROR: overwrite must be 'true', 'false', or '--overwrite', got: $OVERWRITE"
        exit 1
    fi

    echo "Running Render Manifest Task: $MANIFEST_CSV -> $OUTPUT_ROOT (chunk: $CHUNK_ID/$CHUNK_TOTAL, overwrite: ${OVERWRITE:-false})"

    if [ ! -f "$MANIFEST_CSV" ]; then
        echo "ERROR: Manifest CSV does not exist: $MANIFEST_CSV"
        exit 1
    fi

    if [ -e "$OUTPUT_ROOT" ] && [ ! -d "$OUTPUT_ROOT" ]; then
        echo "ERROR: Output root exists but is not a directory: $OUTPUT_ROOT"
        exit 1
    fi

    OUTPUT_PARENT=$(dirname "$OUTPUT_ROOT")
    if [ ! -d "$OUTPUT_PARENT" ]; then
        echo "ERROR: Output root parent does not exist: $OUTPUT_PARENT"
        exit 1
    fi

    python "$CODE_ROOT/scripts/tools/render_rerender_manifest.py" \
        --manifest_csv "$MANIFEST_CSV" \
        --output_root "$OUTPUT_ROOT" \
        --chunk_id "$CHUNK_ID" \
        --chunk_total "$CHUNK_TOTAL" \
        --naming_style view \
        $OVERWRITE_FLAG

elif [ "$1" == "grscenes" ]; then
    # GRScenes 场景渲染模式 (GRScenes scene-level rendering)
    # 用法: bash run_task.sh grscenes <part> <usd> [scene]
    PART=$2
    USD=$3
    SCENE=${4:-""}

    echo "Running GRScenes Task: part=$PART usd=$USD scene=$SCENE"

    CMD="python -m render_usd.cli grscenes --part $PART --usd $USD"
    if [ -n "$SCENE" ]; then
        CMD="$CMD --scene $SCENE"
    fi
    eval "$CMD"

else
    # 批量模式 (Batch mode) - DLC 默认模式
    # 用法: bash run_task.sh <chunk_id> <chunk_total> [assets_dir] [save_dir]
    CHUNK_ID=$1
    CHUNK_TOTAL=$2
    ASSETS_DIR=${3:-"/cpfs/shared/simulation/zhuzihou/assets/GRScenes100-for-render/GRScenes_assets"}
    SAVE_DIR=${4:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_dlc_result"}

    echo "Running Batch Render Task: Chunk $CHUNK_ID / $CHUNK_TOTAL"

    python -m render_usd.cli grscenes100 \
        --chunk_id $CHUNK_ID \
        --chunk_total $CHUNK_TOTAL \
        --assets_dir "$ASSETS_DIR" \
        --save_dir "$SAVE_DIR"
fi
