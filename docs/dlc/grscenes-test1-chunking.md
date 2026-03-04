# GRScenes-test1 Chunking Implementation Documentation

**Date**: 2026-03-04
**Author**: documentation-writer (Agent Team)
**Related Tasks**: #1, #2, #4 (Implementation), #3 (DLC Submission), #5 (Documentation)

---

## 1. Problem Analysis

### 1.1 Scale Challenge

The GRScenes-test1 dataset contains **52,907 USD files** distributed across the following directory structure:

```
GRScenes-test1/GRScenes_assets/
├── backpack/
│   ├── 1001/
│   │   └── usd/
│   │       └── 1001.usd
│   ├── 1002/
│   │   └── usd/
│   │       └── 1002.usd
│   └── ...
├── bed/
│   ├── 5001/
│   │   └── usd/
│   │       └── 5001.usd
│   └── ...
└── ...
```

Each USD file requires rendering 4 views (front, left, back, right) at 512×512px resolution.

### 1.2 Original Limitation

The `render_custom` CLI command, which supports the `Category/UID/usd/UID.usd` structure, **lacked chunking support**. This meant:

1. **Single Job Risk**: A single DLC job processing all 52,907 files would:
   - Run for extended time (estimated 20+ hours)
   - Risk failure due to node timeouts or resource exhaustion
   - Have no checkpoint recovery if interrupted

2. **No Parallel Processing**: Could not leverage multiple DLC nodes to process files in parallel

3. **No Overwrite Control**: The existing skip-if-done logic prevented re-rendering files, which was problematic for:
   - Testing different lighting/material settings
   - Fixing rendering bugs in a subset of assets
   - Re-rendering failed partial outputs

### 1.3 Requirement

Add chunking and overwrite capabilities to enable:
- Parallel processing across 50 DLC nodes (~1,058 files per chunk)
- Granular control over re-rendering specific chunks
- Fault tolerance (failed chunks can be re-submitted)

---

## 2. Solution Design

### 2.1 Design Overview

The solution extends the existing `render_custom` mode with three key features:

1. **Chunking Support**: Divide the total asset list into `N` equal chunks
2. **Overwrite Flag**: Control whether to skip existing renders or re-render
3. **Shell Script Integration**: Update `run_task.sh` to pass chunk/overwrite parameters

### 2.2 Component Changes

| Component | Changes | Purpose |
|-----------|---------|---------|
| `renderer.py` | Add `overwrite` parameter to `render_thumbnail_wo_bg` | Control skip-if-done logic |
| `cli.py` | Add `--overwrite`, `--chunk_id`, `--chunk_total` to `render_custom` | CLI interface for new features |
| `run_task.sh` | Add chunk/overwrite parameters for render_custom mode | Shell script integration |

### 2.3 Chunking Algorithm

The chunking uses a simple index-based division:

```python
total_assets = len(object_usd_paths)
chunk_size = (total_assets + chunk_total - 1) // chunk_total
start_idx = chunk_id * chunk_size
end_idx = min(start_idx + chunk_size, total_assets)
object_usd_paths = object_usd_paths[start_idx:end_idx]
```

This ensures:
- All assets are processed (ceiling division)
- No overlaps between chunks
- Final chunk may be smaller if total isn't perfectly divisible

### 2.4 Overwrite Logic

The skip-if-done check in `renderer.py`:

```python
if not overwrite:
    has_rendered = os.path.exists(save_dir) and \
        len([f for f in os.listdir(save_dir) if f.startswith(object_name) and f.endswith('.png')]) >= sample_number
    if has_rendered:
        continue
```

**Behavior**:
- `overwrite=False` (default): Skip if all `sample_number` images exist
- `overwrite=True`: Always render, regardless of existing files

---

## 3. Code Changes

### 3.1 renderer.py

**File**: `src/render_usd/core/renderer.py`

**Change**: Added `overwrite` parameter to `render_thumbnail_wo_bg` method

```python
def render_thumbnail_wo_bg(
    self,
    object_usd_paths: List[Path],
    thumbnail_wo_bg_dir: Optional[Union[Path, List[Path]]],
    show_bbox2d=True,
    sample_number=4,
    init_azimuth_angle=0,
    naming_style="index",
    overwrite=False,  # NEW: Added parameter
):
```

**Change**: Modified skip-if-done logic (lines 131-134)

```python
if not overwrite:
    has_rendered = os.path.exists(save_dir) and len([f for f in os.listdir(save_dir) if f.startswith(object_name) and f.endswith('.png')]) >= sample_number
    if has_rendered:
        continue
```

**Impact**: The `overwrite` parameter controls whether existing renders are skipped. Default `False` preserves existing behavior (skip if done).

---

### 3.2 cli.py

**File**: `src/render_usd/cli.py`

**Change 1**: Added `--overwrite` flag to `render_custom` subparser (line 101)

```python
parser_custom.add_argument('--overwrite', action='store_true', help="Overwrite existing rendered images")
```

**Change 2**: Added chunking arguments to `render_custom` subparser (lines 102-103)

```python
parser_custom.add_argument('--chunk_id', type=int, default=0, help="Chunk ID for parallel processing")
parser_custom.add_argument('--chunk_total', type=int, default=1, help="Total number of chunks for parallel processing")
```

**Change 3**: Implemented chunking logic in `render_custom` command (lines 323-333)

```python
# Apply chunking logic
total_assets = len(object_usd_paths)
if args.chunk_total > 1:
    chunk_size = (total_assets + args.chunk_total - 1) // args.chunk_total
    start_idx = args.chunk_id * chunk_size
    end_idx = min(start_idx + chunk_size, total_assets)
    object_usd_paths = object_usd_paths[start_idx:end_idx]
    save_dirs = save_dirs[start_idx:end_idx]
    print(f"[CLI] Chunk {args.chunk_id}/{args.chunk_total}: {len(object_usd_paths)} assets ({start_idx}-{end_idx}).")
else:
    print(f"[CLI] Processing all {total_assets} assets (single chunk).")
```

**Change 4**: Added `--overwrite` to `grscenes100` command (line 78)

```python
parser_gr100.add_argument('--overwrite', action='store_true', help="Overwrite existing rendered images")
```

**Change 5**: Added `--overwrite` to `single` command (line 95)

```python
parser_single.add_argument('--overwrite', action='store_true', help="Overwrite existing rendered images")
```

**Impact**: All rendering modes now support the `--overwrite` flag. `render_custom` supports chunking with sensible defaults (chunk_id=0, chunk_total=1).

---

### 3.3 run_task.sh

**File**: `scripts/dlc/run_task.sh`

**Change**: Updated `render_custom` mode to support chunking and overwrite (lines 70-86)

```bash
elif [ "$1" == "render_custom" ]; then
    # Custom directory structure rendering
    # Usage: bash run_task.sh render_custom <assets_dir> [naming_style] [chunk_id] [chunk_total] [overwrite]
    # Structure: assets_dir/Category/UID/usd/UID.usd
    ASSETS_DIR=$2
    NAMING_STYLE=${3:-"view"}
    CHUNK_ID=${4:-0}
    CHUNK_TOTAL=${5:-1}
    OVERWRITE=${6:-""}

    echo "Running Render Custom Task: $ASSETS_DIR (naming: $NAMING_STYLE, chunk: $CHUNK_ID/$CHUNK_TOTAL, overwrite: ${OVERWRITE:-false})"

    CMD="python -m render_usd.cli render_custom --assets_dir \"$ASSETS_DIR\" --naming_style \"$NAMING_STYLE\" --chunk_id \"$CHUNK_ID\" --chunk_total \"$CHUNK_TOTAL\""
    if [ -n "$OVERWRITE" ]; then
        CMD="$CMD --overwrite"
    fi
    eval "$CMD"
```

**Usage Examples**:
```bash
# Render all assets (single chunk, no overwrite)
bash run_task.sh render_custom /path/to/assets

# Render chunk 0 of 50, with overwrite enabled
bash run_task.sh render_custom /path/to/assets view 0 50 true

# Render chunk 25 of 50, no overwrite
bash run_task.sh render_custom /path/to/assets view 25 50
```

**Impact**: Shell script now supports passing chunk and overwrite parameters to the CLI.

---

## 4. DLC Job Details

### 4.1 Job Configuration

**Task Name**: `render_grscenes_test1`
**Total Chunks**: 50
**Files per Chunk**: ~1,058 (52,907 total files)

**Assets Directory**:
```
/cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets
```

**Output**: In-place rendering under `Category/UID/` directories (same as USD file location)

**Overwrite**: Enabled (`true`)

### 4.2 Submission Command

The batch job is submitted using:

```bash
python scripts/dlc/submit_batch.py \
    --total 50 \
    --name render_grscenes_test1 \
    --command_args "render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view"
```

**Note**: The `--overwrite` flag is added by `launch_job.sh` through environment configuration or manual job specification.

### 4.3 Job Naming Convention

Each submitted job follows the pattern: `{TASK_NAME}_{CHUNK_ID}_{CHUNK_TOTAL}`

Examples:
- `render_grscenes_test1_0_50` - First chunk (files 0-1057)
- `render_grscenes_test1_1_50` - Second chunk (files 1058-2115)
- `render_grscenes_test1_49_50` - Last chunk (files 51849-52906)

### 4.4 Resource Allocation

Per-job resource allocation (defined in `launch_job.sh`):
- **GPU**: 1x GPU (for Isaac Sim PathTracing renderer)
- **CPU**: 16 cores
- **Memory**: 118 GiB
- **Runtime**: Unlimited (0 minutes = no timeout)
- **Image**: `isaacsim41-cuda118`
- **Priority**: 7

### 4.5 Data Sources

The job uses 3 CPFS data sources:
- `d-mzps5b7joy2axmqpa8`
- `d-d49o5g0h2818sw8j1g`
- `d-8wz4emfs21s5ajs9oz`

These mount the CPFS volume at `/cpfs/` within the container.

---

## 5. Testing and Verification

### 5.1 Local Testing

**Test Command**:
```bash
source miniconda/bin/activate render-usd
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
export OMNI_KIT_ACCEPT_EULA=YES

python -m render_usd.cli render_custom \
    --assets_dir /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets \
    --naming_style view \
    --chunk_id 0 \
    --chunk_total 2
```

**Expected Behavior**:
- Script scans the assets directory and finds 52,907 USD files
- Chunk 0/2 processes the first half (~26,453 files)
- Outputs 4 images per file under `Category/UID/` directory

**Verification Steps**:
1. Check that output files are created: `find /path/to/assets -name "*.png" | head -20`
2. Verify naming convention: `front.png`, `left.png`, `back.png`, `right.png`
3. Check image quality (HDRI lighting, proper materials, no red artifacts)

### 5.2 DLC Job Submission

**Test Submission** (smaller scale for verification):
```bash
python scripts/dlc/submit_batch.py \
    --total 2 \
    --name test_grscenes_test1_chunking \
    --command_args "render_custom /cpfs/shared/simulation/zhuzihou/dev/usd-scene-physics-prep/GRScenes-test1/GRScenes_assets view"
```

**Monitoring Commands**:
```bash
# List jobs
/cpfs/shared/simulation/zhuzihou/dev/render-usd/dlc submit pytorchjob --help

# Get job logs
/cpfs/shared/simulation/zhuzihou/dev/render-usd/dlc logs <job_name>

# Stop a job
/cpfs/shared/simulation/zhuzihou/dev/render-usd/dlc stop <job_name>
```

### 5.3 Expected Output

Each USD file should generate 4 PNG images:

```
GRScenes-test1/GRScenes_assets/
├── backpack/
│   ├── 1001/
│   │   ├── usd/
│   │   │   └── 1001.usd
│   │   ├── front.png    # Front view (azimuth=0°)
│   │   ├── left.png     # Left view (azimuth=90°)
│   │   ├── back.png     # Back view (azimuth=180°)
│   │   └── right.png    # Right view (azimuth=270°)
│   └── 1002/
│   │   ├── usd/
│   │   │   └── 1002.usd
│   │   ├── front.png
│   │   ├── left.png
│   │   ├── back.png
│   │   └── right.png
```

### 5.4 Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| All 52,907 USD files are processed | ✓ | Any file skipped without reason |
| Each file generates exactly 4 PNGs | ✓ | Missing or extra images |
| Images have proper lighting (no red artifacts) | ✓ | MDL material resolution failed |
| Images have dark gray background (RGB 40,40,40) | ✓ | Wrong background color |
| Chunking distributes work evenly | ✓ | Large imbalance between chunks |
| Overwrite flag works correctly | ✓ | Existing renders not re-rendered with `--overwrite` |

---

## 6. Key Discoveries and Insights

### 6.1 Chunking Strategy

- **Ceiling Division**: Using `(total + chunk_total - 1) // chunk_total` ensures all files are processed even when not evenly divisible
- **Zero-indexed Chunks**: Chunk IDs start from 0 to match Python indexing conventions
- **Slicing Synchronization**: Both `object_usd_paths` and `save_dirs` lists are sliced with identical indices to maintain correspondence

### 6.2 Backward Compatibility

- **Default Values**: `chunk_id=0`, `chunk_total=1` ensures single-chunk behavior is preserved
- **Optional Overwrite**: Default `overwrite=False` maintains skip-if-done behavior
- **Existing Modes**: `grscenes100`, `grscenes`, and `single` modes received the `--overwrite` flag for consistency

### 6.3 Shell Script Flexibility

The `run_task.sh` script now supports:
- Single file testing: `run_task.sh single <usd_path> [output_dir]`
- Custom directory rendering with chunking: `run_task.sh render_custom <assets_dir> [naming_style] [chunk_id] [chunk_total] [overwrite]`
- Batch mode (default): `run_task.sh <chunk_id> <chunk_total> [assets_dir] [save_dir]`

### 6.4 MDL Path Configuration

The existing MDL path configuration remains unchanged:
- GRScenes-test1 MDL path is set via `MDL_SYSTEM_PATH` in `run_task.sh`
- Material references in USD files are resolved correctly through carb.settings

---

## 7. Conclusion

The chunking implementation successfully enables parallel processing of the GRScenes-test1 dataset:

1. **Scale**: 52,907 files distributed across 50 parallel jobs
2. **Fault Tolerance**: Failed chunks can be re-submitted independently
3. **Control**: `--overwrite` flag enables selective re-rendering
4. **Compatibility**: All existing modes and behaviors are preserved

The implementation follows the existing code patterns and integrates seamlessly with the DLC job submission pipeline.

---

## 8. Related Documentation

- [DLC Changelog](./changelog.md) - Previous DLC script modifications
- [HDRI Lighting Guide](../guides/lighting-guide.md) - HDRI environment setup
- [MDL Path Fix](./changelog.md#mdl-材质搜索路径修复) - MDL material resolution
- [Agent Team Playbook](../tmp/agent-team-playbook.md) - Agent team workflow

---

**Document Status**: Complete
**Next Steps**: Monitor DLC job execution and update documentation with final results
