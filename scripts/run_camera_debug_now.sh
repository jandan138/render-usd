#!/usr/bin/env bash
#
# One-shot camera distance debug script.
# Run this directly in your terminal:
#   bash scripts/run_camera_debug_now.sh
#
# It will run all 3 tests (A/B/C) sequentially and save logs.

set -euo pipefail
cd /cpfs/shared/simulation/zhuzihou/dev/render-usd

USD_PATH="/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets/bed/0a85b986de35ccfdec7c686d791fd747/usd/0a85b986de35ccfdec7c686d791fd747.usd"
LOG_DIR="test_outputs/debug_logs"

source miniconda/bin/activate render-usd
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
export OMNI_KIT_ACCEPT_EULA=YES

mkdir -p test_outputs/debug_A test_outputs/debug_B test_outputs/debug_C "$LOG_DIR"

echo "====== Environment Check ======"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
which python
python --version
echo "================================"

echo ""
echo "====== Test A: Baseline ======"
python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_A \
    --naming_style view \
    --overwrite 2>&1 | tee "$LOG_DIR/test_A.log"
echo "[Test A] DONE"

echo ""
echo "====== Test B: RENDER_SKIP_LOOP_RESET=1 ======"
RENDER_SKIP_LOOP_RESET=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_B \
    --naming_style view \
    --overwrite 2>&1 | tee "$LOG_DIR/test_B.log"
echo "[Test B] DONE"

echo ""
echo "====== Test C: RENDER_SKIP_ALPHA=1 ======"
RENDER_SKIP_ALPHA=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir test_outputs/debug_C \
    --naming_style view \
    --overwrite 2>&1 | tee "$LOG_DIR/test_C.log"
echo "[Test C] DONE"

echo ""
echo "====== Summary ======"
echo "Test A output:" && ls -la test_outputs/debug_A/
echo "Test B output:" && ls -la test_outputs/debug_B/
echo "Test C output:" && ls -la test_outputs/debug_C/
echo ""
echo "DEBUG-CAM lines from all tests:"
grep "\[DEBUG-CAM\]" "$LOG_DIR"/test_*.log || echo "(no DEBUG-CAM lines found)"
echo ""
echo "All tests complete. Logs saved to: $LOG_DIR/"
