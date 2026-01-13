# DLC Scripts Documentation

[中文版](README_zh.md)

This directory contains utility scripts for submitting and managing rendering jobs on the Deep Learning Cluster (DLC) or Kubernetes-based environments.

## Scripts Overview

### `launch_job.sh`
A wrapper script that sets up the environment and executes the rendering command for a single job chunk.

*   **Usage**: `bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES]`
*   **Role**: Entry point for the container. It configures environment variables, PYTHONPATH, and executes `run_task.sh`.

### `run_task.sh`
The internal execution script that runs the actual Python rendering command.

*   **Usage**: `bash run_task.sh <CHUNK_ID> <CHUNK_TOTAL>`
*   **Role**: Activates Conda environments (if needed), sets specific env vars (e.g., `OMNI_KIT_ACCEPT_EULA`), and calls `python -m render_usd.cli`.

### `submit_batch.py`
A Python script to automate the submission of multiple jobs to the cluster.

*   **Usage**: `python submit_batch.py --total <TOTAL_CHUNKS> --name <TASK_NAME>`
*   **Role**: Loops through the total number of chunks and calls `dlc submit` (via `launch_job.sh`) for each one.

## Environment Requirements

To use these scripts, your cluster environment must meet the following criteria:

1.  **DLC CLI**: The `dlc` command-line tool must be installed and configured with valid credentials.
2.  **Mount Points**:
    *   **Code**: The repository code must be mounted to `/cpfs/shared/simulation/zhuzihou/dev/render-usd` (or configured via `DLC_CODE_ROOT`).
    *   **Data**: Input assets and output directories must be accessible (e.g., `/cpfs/user/...` or OSS paths).
3.  **Docker Image**: A valid Isaac Sim image with Python environment support (e.g., `pj4090/yangsizhe:isaacsim41-cuda118`).

## Configuration

You can customize the job submission by setting environment variables before running `submit_batch.py`:

*   `DLC_WORKSPACE_ID`: Your DLC workspace ID.
*   `DLC_RESOURCE_ID`: Resource quota ID.
*   `DLC_IMAGE`: Docker image address.
*   `DLC_CODE_ROOT`: Path where the code is mounted in the container.

## Example

Submit a batch of 30 jobs to render the GRScenes dataset:

```bash
export DLC_CODE_ROOT=/root/render-usd
python scripts/dlc/submit_batch.py --total 30 --name grscenes_render
```
