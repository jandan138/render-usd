# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`render-usd` is a modular rendering pipeline for USD assets using NVIDIA Isaac Sim (PathTracing renderer). It generates multi-view thumbnail images of 3D objects from USD files.

## Environment Setup

This project runs inside Isaac Sim's Python environment. Before running any commands:

```bash
# 1. Activate the conda environment (uses local miniconda)
source miniconda/bin/activate render-usd

# 2. Add src to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# 3. Accept Isaac Sim EULA (required)
export OMNI_KIT_ACCEPT_EULA=YES

# 4. (Optional) Set MDL search paths for GRScenes materials
# The CLI also configures this via carb.settings; env var is a fallback
export MDL_SYSTEM_PATH="/path/to/Material/mdl:/path/to/Materials"
```

The `scripts/dlc/run_task.sh` handles these steps automatically for DLC jobs.

## Key Commands

```bash
# Install package in editable mode
pip install -e .

# Render a single USD file (4 views: front/left/back/right)
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output

# Render single file with semantic view names (front.png, left.png, etc.)
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output --naming_style view

# Render assets in Category/UID/usd/UID.usd structure
python -m render_usd.cli render_custom --assets_dir /path/to/assets --naming_style view

# Render GRScenes-100 dataset (chunked for cluster)
python -m render_usd.cli grscenes100 --chunk_id 0 --chunk_total 10 --assets_dir /path/to/assets --save_dir ./output

# Submit batch DLC jobs
python scripts/dlc/submit_batch.py --total 10 --name render_grscenes100

# Run task via shell (handles env setup automatically)
bash scripts/dlc/run_task.sh single /path/to/asset.usd ./output
bash scripts/dlc/run_task.sh 0 10  # batch mode: chunk_id chunk_total
```

## Architecture

The pipeline has three core modules in `src/render_usd/core/`:

- **`renderer.py` (`RenderManager`)**: Orchestrator. Runs the main loop over USD files, coordinates scene/camera setup, handles skip-if-done logic, writes output PNGs.
- **`scene.py`**: Initializes Isaac Sim `World`, loads USD stages, sets up environment lighting (loads `assets/environments/background.usd` or falls back to a Dome Light).
- **`camera.py`**: Creates `omni.isaac.sensor.Camera` instances, positions them using spherical coordinates (azimuth/elevation/distance), extracts RGB/depth/bbox data.

**Data flow**: CLI parses args → `RenderManager.__init__` calls `init_world()` → `render_thumbnail_wo_bg` or `render_thumbnail_with_bg` called → for each USD: load prim, compute bbox, position cameras at 4 viewpoints, step simulation 100+8 times, extract RGB, save PNG.

**Important constraint**: `SimulationApp` must be initialized before any `omni`/`isaacsim` imports. This is why `RenderManager` and other Isaac Sim imports happen after `kit = SimulationApp(CONFIG)` in `cli.py`.

## Key Configuration

`src/render_usd/config/settings.py` defines:
- `DEFAULT_MDL_PATH`: `assets/materials/default.mdl`
- `DEFAULT_ENVIRONMENT_PATH`: `assets/environments/background.usd` (gitignored — must be provided)
- `DEFAULT_MDL_SEARCH_PATHS`: GRScenes MDL directories for material resolution (configured at startup via `carb.settings` `/app/mdl/additionalSystemPaths`)
- Default data paths pointing to `/cpfs/user/caopeizhou/...` (override via CLI args)

MDL search paths can also be set via `--mdl_paths` CLI arg or `MDL_SYSTEM_PATH` env var (colon-separated). All sources are merged.

## Asset Structure Conventions

Two supported input structures:
1. **GRScenes-100**: `Category/AssetID/AssetID.usd`
2. **render_custom**: `Category/UID/usd/UID.usd` → outputs to `Category/UID/`

Output images: 4 PNG files per object at 35° elevation, 512×512px. Skip logic prevents re-rendering already-completed objects (checks for existing PNGs matching `{object_name}_{idx}.png` pattern).

## Utils Layout

- `utils/usd_utils/`: USD stage/prim/MDL manipulation (`stage_utils.py`, `prim_utils.py`, `mdl_utils.py`)
- `utils/common_utils/`: Path helpers, image drawing, semantic label utilities
- `utils/caption_utils/`: GPT/Qwen captioning and visualization (post-processing step, not part of main render loop)

## DLC Cluster Scripts

`scripts/dlc/submit_batch.py` calls `scripts/dlc/launch_job.sh` for each chunk. `launch_job.sh` submits a DLC/Kubernetes job that runs `run_task.sh` inside a container. The container mounts the CPFS volume at the same path as the dev machine.

## Agent Team Documentation Rule

When working in an agent team, **every agent must document its work**:

1. **Research agents** (explorer, researcher, investigator): Write findings into `docs/design/` or `docs/tmp/` — include what was investigated, key discoveries, data/evidence collected, and conclusions.
2. **Implementation agents** (implementer, bug-fixer, refactorer): Write a technical report documenting the problem analysis, solution design, code changes (with file paths and key snippets), and rationale for design decisions.
3. **Testing agents** (tester, validator): Document test plan, commands executed, job IDs, expected vs actual results, and pass/fail status.
4. **Operations agents** (dlc-operator): Document job configurations, submission details, and any environment changes.

**Documentation requirements:**
- Each agent should write documentation **as it works**, not as an afterthought.
- Documents go in `docs/` under the appropriate subdirectory (`design/`, `dlc/`, `guides/`, `tmp/` for scratch notes).
- Use clear structure: Problem → Investigation → Solution → Results.
- Write in a way that is detailed, thorough, and easy to understand for someone unfamiliar with the context.
- If an agent **does not have write permissions** (e.g., read-only agents like `codebase-explorer` or `render-validator`), it must send its findings to the **docs-writer agent** (or team lead) and request that documentation be written on its behalf.
- The team lead should ensure a comprehensive final report exists in `docs/design/` covering the entire workflow (research + implementation + testing) before closing the team.
