#!/bin/bash
CHUNK_ID=$1
CHUNK_TOTAL=$2

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

echo "Running Render Task: Chunk $CHUNK_ID / $CHUNK_TOTAL"

# Install dependencies if needed (optional, slows down startup)
# pip install -e $CODE_ROOT

# Run CLI
python -m render_usd.cli grscenes100 \
    --chunk_id $CHUNK_ID \
    --chunk_total $CHUNK_TOTAL \
    --assets_dir /cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all \
    --save_dir /oss-caopeizhou/data/GRScenes-100/all_assets_renderings
