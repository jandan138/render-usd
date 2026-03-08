#!/usr/bin/env bash
#
# debug_camera_distance.sh - Debug camera distance issues by running render
# with different environment variable flags.
#
# Usage:
#   bash scripts/debug_camera_distance.sh /path/to/asset.usd
#
# This script runs three separate rendering tests:
#   A (Baseline)    - No extra env vars, standard rendering
#   B (Skip reset)  - RENDER_SKIP_LOOP_RESET=1, skips per-loop reset logic
#   C (Skip alpha)  - RENDER_SKIP_ALPHA=1, skips alpha compositing
#
# Each test launches an independent Python process because Isaac Sim's
# SimulationApp can only be initialized once per process.
#
# Output directories:
#   test_outputs/debug_A/
#   test_outputs/debug_B/
#   test_outputs/debug_C/

set -euo pipefail

# --- Validate arguments ---
if [ $# -lt 1 ]; then
    echo "Usage: bash $0 <usd_file_path>"
    echo "Example: bash $0 /cpfs/shared/simulation/data/assets/Chair/chair01/chair01.usd"
    exit 1
fi

USD_PATH="$1"

if [ ! -f "$USD_PATH" ]; then
    echo "[ERROR] USD file not found: $USD_PATH"
    exit 1
fi

# --- Setup environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "============================================"
echo "  Camera Distance Debug Script"
echo "============================================"
echo "Project dir : $PROJECT_DIR"
echo "USD file    : $USD_PATH"
echo "============================================"
echo ""

source miniconda/bin/activate render-usd
export PYTHONPATH="${PYTHONPATH:-}:${PROJECT_DIR}/src"
export OMNI_KIT_ACCEPT_EULA=YES

# --- Output directories ---
OUT_A="$PROJECT_DIR/test_outputs/debug_A"
OUT_B="$PROJECT_DIR/test_outputs/debug_B"
OUT_C="$PROJECT_DIR/test_outputs/debug_C"

# --- Test A: Baseline (no extra env vars) ---
echo "============================================"
echo "  Test A: Baseline (no extra env vars)"
echo "============================================"
rm -rf "$OUT_A"
mkdir -p "$OUT_A"

python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir "$OUT_A" \
    --naming_style view \
    --overwrite

echo ""
echo "[Test A] Done. Output: $OUT_A"
echo ""

# --- Test B: Skip per-loop reset ---
echo "============================================"
echo "  Test B: RENDER_SKIP_LOOP_RESET=1"
echo "============================================"
rm -rf "$OUT_B"
mkdir -p "$OUT_B"

RENDER_SKIP_LOOP_RESET=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir "$OUT_B" \
    --naming_style view \
    --overwrite

echo ""
echo "[Test B] Done. Output: $OUT_B"
echo ""

# --- Test C: Skip alpha compositing ---
echo "============================================"
echo "  Test C: RENDER_SKIP_ALPHA=1"
echo "============================================"
rm -rf "$OUT_C"
mkdir -p "$OUT_C"

RENDER_SKIP_ALPHA=1 python -m render_usd.cli single \
    --usd_path "$USD_PATH" \
    --output_dir "$OUT_C" \
    --naming_style view \
    --overwrite

echo ""
echo "[Test C] Done. Output: $OUT_C"
echo ""

# --- Summary ---
echo "============================================"
echo "  All tests complete!"
echo "============================================"
echo "  A (Baseline)   : $OUT_A"
echo "  B (Skip reset) : $OUT_B"
echo "  C (Skip alpha) : $OUT_C"
echo ""
echo "Compare outputs to identify camera distance issues."
echo "============================================"
