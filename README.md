# Render USD Pipeline

This project provides a scalable pipeline for rendering USD assets using NVIDIA Isaac Sim, designed for cluster deployment (DLC) and local development.

## Project Structure

```text
render-usd/
├── src/render_usd/         # Core Python package
│   ├── cli.py              # Main entry point (CLI)
│   ├── core/               # Rendering logic (Renderer class)
│   ├── config/             # Configuration and default paths
│   └── utils/              # Shared utilities (USD, Image, Sim)
├── scripts/dlc/            # DLC cluster submission scripts
│   ├── launch_job.sh       # Generic job launcher
│   ├── run_task.sh         # Task execution script (runs inside container)
│   └── submit_batch.py     # Batch submission tool
├── environment.yml         # Conda environment definition
└── pyproject.toml          # Python package configuration
```

## Installation

### 1. Environment Setup
Create a Conda environment with the required dependencies (Isaac Sim 4.1.0, PyTorch 2.4.0):

```bash
conda env create -f environment.yml
conda activate render-usd
```

### 2. Install Package
Install the package in editable mode:

```bash
pip install -e .
```

## Usage

### Local Execution

You can run the rendering pipeline locally using the CLI:

```bash
# Render GRScenes-100 dataset (Chunk 0 of 1)
python -m render_usd.cli grscenes100 \
    --chunk_id 0 \
    --chunk_total 1 \
    --assets_dir /cpfs/user/caopeizhou/data/GRScenes-100/Asset_Library_all \
    --save_dir ./output_test

### Render Single File

To render a specific USD file (e.g., for testing):

```bash
python -m render_usd.cli single \
    --usd_path /path/to/file.usd \
    --output_dir ./output_single
```

### DLC Cluster Submission

The `scripts/dlc` directory contains tools for submitting jobs to the Deep Learning Cluster.

**Submit a Batch of Jobs:**
To submit 30 parallel jobs to process the entire dataset:

```bash
python scripts/dlc/submit_batch.py --total 30
```

**Launch a Single Job Manually:**
```bash
bash scripts/dlc/launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL>
```

## Configuration

Default paths and simulation settings are defined in `src/render_usd/config/settings.py`. 
Key configurations include:
- `DEFAULT_GRSCENES100_ASSETS_DIR`
- `DEFAULT_GRSCENES100_SAVE_DIR`
- `SIM_CONFIG` (Headless mode, anti-aliasing, etc.)

## Development

- **Adding new features**: Add logic to `src/render_usd/core/`.
- **New datasets**: Extend `RenderManager` in `src/render_usd/core/renderer.py` and add a new command in `src/render_usd/cli.py`.
