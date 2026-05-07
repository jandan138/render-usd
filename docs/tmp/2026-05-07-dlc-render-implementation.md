# DLC Batch Rendering Implementation Record

**Date:** 2026-05-07
**Branch:** feat/dlc-render-update
**Author:** OpenCode Agent

## Changes Summary

### 1. scripts/dlc/launch_job.sh
**Status:** Hardened with reference script improvements

**Key Changes:**
- Added `set -euo pipefail` strict mode
- Added parameter count validation (requires ≥3 args)
- Added integer validation for CHUNK_ID and CHUNK_TOTAL
- Updated default DATA_SOURCES to 4 sources (added `d-f1dsz5nbamclxgydo8` for `/cpfs/user/zhuzihou` access)
- Fixed `--overwrite` handling with word-based matching (prevents partial match issues like `my--overwrite-dir`)
- Added DLC binary executable check
- Added resolved config logging (GPU/CPU/Memory/Resource/Timeout)
- Added job timeout default (480 minutes = 8 hours)
- Kept render-usd specific settings (Isaac Sim 4.1.0 image, CODE_ROOT)

**Security Improvements:**
- Strict mode prevents silent failures
- Parameter validation prevents invalid job submissions
- Binary check catches missing DLC CLI early

### 2. scripts/dlc/run_task.sh
**Status:** Security vulnerabilities fixed

**Key Changes:**
- Replaced `eval "$CMD"` with direct execution (prevents command injection)
- Added `ASSETS_DIR` existence pre-check
- Kept all existing modes (single, render_custom, grscenes, batch)

**Security Improvements:**
- Eliminates eval-based command injection risk
- Early validation prevents cascading errors

### 3. src/render_usd/core/renderer.py
**Status:** View-mode skip logic fixed

**Key Changes:**
- Modified `render_thumbnail_wo_bg()` skip detection logic
- View mode now checks for `front.png`, `back.png`, `left.png`, `right.png`
- Index mode preserved (checks for `object_name_{idx}.png`)
- Only applies fix when `naming_style == "view"` and `sample_number == 4`

**Bug Fixed:**
- Previously: `f.startswith(object_name)` never matched view-style filenames
- Now: Correctly detects existing view renders, enabling skip/断点续传

## Testing

### Syntax Validation
- `bash -n scripts/dlc/launch_job.sh` ✅ Pass
- `bash -n scripts/dlc/run_task.sh` ✅ Pass

### Dry-Run
- `DLC_BIN=/bin/echo bash scripts/dlc/launch_job.sh test_task 0 75` ✅
- Correctly outputs submit command with all 4 data sources
- Resource config logged correctly

### Code Review
- All 3 files reviewed by parallel agents (security, resources, business logic)
- Agent findings integrated into implementation

## Known Issues

1. **Python Import Test Failed:** `omni` module not available outside Isaac Sim environment (expected)
2. **Dry-Run Quoting:** /bin/echo displays merged args, but actual dlc submit handles quoting correctly

## Verification Checklist

- [x] launch_job.sh has strict mode
- [x] launch_job.sh validates arguments
- [x] launch_job.sh has 4 data sources
- [x] launch_job.sh checks DLC binary
- [x] run_task.sh has no eval
- [x] run_task.sh checks assets_dir
- [x] renderer.py detects view files
- [x] renderer.py preserves index mode
- [x] Syntax checks pass
- [x] Dry-run succeeds

## Next Steps

1. Submit actual DLC batch job:
```bash
python scripts/dlc/submit_batch.py \
    --total 75 \
    --name test0_render_views \
    --data_sources "d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8" \
    --command_args "render_custom /cpfs/user/zhuzihou/assets/dedup_workspaces/test0_transitive_apply_parallel/dataset/GRScenes_assets view {chunk_id} {chunk_total} --overwrite"
```

2. Monitor first few chunks for successful rendering
3. Verify output structure matches expected: `<category>/<uid>/{front,back,left,right}.png`
