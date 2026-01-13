#!/bin/bash
# Code root should match what is mounted/expected
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

# Setup environment
# 1. Try to use the local miniconda installed in the project directory (Most Robust)
LOCAL_CONDA="$CODE_ROOT/miniconda/bin/activate"
if [ -f "$LOCAL_CONDA" ]; then
    echo "Found local miniconda at $LOCAL_CONDA, activating..."
    source "$LOCAL_CONDA" render-usd
else
    # 2. Fallback to system conda (e.g. from .bashrc or Docker image)
    echo "Local miniconda not found, trying system conda..."
    if [ -f "/cpfs/user/caopeizhou/.bashrc" ]; then
        source /cpfs/user/caopeizhou/.bashrc
    fi
    eval "$(conda shell.bash hook)"
    conda activate render-usd || echo "WARNING: Failed to activate render-usd env"
fi

# 3. Ensure the package is installed
if ! python -c "import render_usd" &> /dev/null; then
    echo "Package 'render-usd' not found in current environment. Installing..."
    pip install -e "$CODE_ROOT"
else
    echo "Package 'render-usd' is already installed."
fi

# Setup Python path
export PYTHONPATH=$PYTHONPATH:$CODE_ROOT/src
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1

# Check mode
if [ "$1" == "single" ]; then
    # Single file mode for testing
    # Usage: bash run_task.sh single <usd_path> <output_dir>
    USD_PATH=$2
    OUTPUT_DIR=${3:-"$CODE_ROOT/output_test_single"}
    
    echo "Running Single Render Task: $USD_PATH"
    
    python -m render_usd.cli single \
        --usd_path "$USD_PATH" \
        --output_dir "$OUTPUT_DIR"

else
    # Batch mode (DLC default)
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
