# Usage Guide

## Command Line Interface (CLI)

The primary entry point for the tool is `src/render_usd/cli.py`. You can execute it using `python -m render_usd.cli`.

### Single File Rendering

Render a single USD file to a specified output directory.

```bash
python -m render_usd.cli single \
    --usd_path /path/to/your/asset.usd \
    --output_dir /path/to/output
```

**Parameters**:
*   `--usd_path`: Absolute path to the target `.usd` file.
*   `--output_dir`: Directory where rendered images will be saved.

### Batch Rendering (TBD)

*Currently under development.*

## DLC Job Submission

For large-scale rendering tasks on a cluster (using DLC/Kubernetes), use the scripts provided in `scripts/dlc/`.

### 1. Launch Job (`launch_job.sh`)
This script wraps the single rendering command.

```bash
bash scripts/dlc/launch_job.sh <usd_path> <output_dir>
```

### 2. Submit Batch (`submit_batch.py`)
Submits multiple jobs to the cluster.

```bash
python scripts/dlc/submit_batch.py --input_list assets_list.txt
```

**Prerequisites for DLC**:
*   Ensure your cluster environment has access to the `render-usd` code and necessary volumes.
*   Configure your DLC credentials and endpoints in `scripts/dlc/config.json` (if applicable).
