#!/bin/bash
CHUNK_ID=$1
CHUNK_TOTAL=$2

# Code root should match what is mounted/expected
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

# Setup environment
# Source bashrc if needed for conda
if [ -f "/cpfs/user/caopeizhou/.bashrc" ]; then
    source /cpfs/user/caopeizhou/.bashrc
fi

# Activate environment if needed (legacy behavior preserved)
# source activate omniscenes || echo "Conda env omniscenes not found, using default"

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
