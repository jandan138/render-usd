# DLC Scripts Documentation

[中文版](README_zh.md)

This directory contains utility scripts for submitting and managing rendering jobs on the Deep Learning Cluster (DLC) or Kubernetes-based environments.

## 1. Workflow & Architecture

Running tasks on DLC typically involves two environments:
1.  **Submission Environment (DSW/Local)**: Your development machine (e.g., DSW instance or local PC). You write code and **submit** tasks here.
2.  **Execution Environment (DLC Cluster)**: Alibaba Cloud's compute cluster. Once submitted, tasks launch new containers (Workers) here to **execute** rendering.

**Call Chain:**

```mermaid
graph LR
    A[DSW/Local Terminal] -- 1. python submit_batch.py --> B(dlc submit command)
    B -- 2. Submit Task Description (JSON/YAML) --> C[Alibaba Cloud DLC Cluster]
    C -- 3. Schedule & Launch Worker Container --> D[Worker Node]
    D -- 4. Mount Code & Data --> E(Run launch_job.sh)
    E -- 5. Setup System Env --> F(Run run_task.sh)
    F -- 6. Activate Conda & Run Python --> G[render_usd.cli]
```

---

## 2. Scripts Details

### 2.1 `submit_batch.py` (Dispatcher)
*   **Location**: DSW or Local Dev Machine.
*   **Role**: Automates batch submission. It loops through chunks and calls the `dlc` CLI tool to submit them one by one.
*   **Logic**:
    ```python
    # Pseudo-code
    for chunk_id in range(total_chunks):
        cmd = "bash launch_job.sh ..." # Construct launch command
        subprocess.run(f"dlc submit ... --command '{cmd}'") # Call Alibaba Cloud CLI
    ```
*   **Usage**:
    ```bash
    python scripts/dlc/submit_batch.py --total 30 --name grscenes_render
    ```

### 2.2 `launch_job.sh` (Container Entrypoint)
*   **Location**: Inside DLC Cluster Worker (First script executed on startup).
*   **Role**:
    1.  **Env Init**: Sets `PYTHONPATH`, exports necessary env vars (e.g., `WORKSPACE_ID`).
    2.  **Bridge Args**: Receives args from `dlc submit` (e.g., `CHUNK_ID`).
    3.  **Launch Task**: Calls `run_task.sh`.
*   **Usage**: Typically called automatically by `submit_batch.py`, not manually (unless for debugging).

### 2.3 `run_task.sh` (Task Executor)
*   **Location**: Inside DLC Cluster Worker.
*   **Role**:
    1.  **Env Activation**: Auto-detects and activates the project-local Miniconda environment (`render-usd`) to ensure Python dependencies are correct.
    2.  **Dependency Check**: Installs the package (`pip install -e .`) if missing.
    3.  **Execution**: Calls the core Python rendering command (`python -m render_usd.cli`).
*   **Usage**:
    ```bash
    # Local Debug/Run
    bash scripts/dlc/run_task.sh 0 100
    ```

---

## 3. DSW Setup Guide

If you encounter "command not found" or "auth failed" errors when running submission scripts in DSW, check the following.

### 3.1 Why Configuration is Needed?
DSW is just a development environment. To send tasks to the DLC cluster, you need the Alibaba Cloud Client Tool —— **`dlc` CLI**.
1.  **Tool Dependency**: Your DSW environment must have the `dlc` CLI installed.
2.  **Authentication**: The tool needs to know "who you are" (AccessKey) to have permission to submit tasks.

### 3.2 Check & Configure Steps

**Step 1: Check if `dlc` is installed**
Run in terminal:
```bash
which dlc
# If no output, it is not installed or not in PATH
```
*If missing*, you usually need to install the Alibaba Cloud PAI-DLC SDK or CLI package.

**Step 2: Configure Credentials (Critical)**
Even if installed, you must configure your Alibaba Cloud AccessKey before first use.
```bash
dlc config
```
You will be prompted to enter:
*   **AccessKey ID**
*   **AccessKey Secret**
*   **Endpoint**: DLC service endpoint (e.g., `dlc.cn-beijing.aliyuncs.com`).
*   **Region**: (e.g., `cn-beijing`).

**Step 3: Verify**
After config, try listing current jobs:
```bash
dlc get jobs
```
If it lists jobs, your environment is ready to run `submit_batch.py`.

---

## 4. Local Testing

You can run the script locally to verify the environment and rendering logic before submitting to DLC.

**Render a single file:**
```bash
bash scripts/dlc/run_task.sh single /path/to/asset.usd [output_dir]
```

**Run a batch chunk (dry run):**
```bash
# Processes chunk 0 of 100 (will scan assets but run on local machine)
bash scripts/dlc/run_task.sh 0 100
```

**In-place Rendering:**
To save rendered images in the same directory as the USD file (instead of a separate output folder), use "inplace" as the save directory argument:
```bash
bash scripts/dlc/run_task.sh 0 1 "/path/to/assets" "inplace"
```

---

## 5. DLC Environment Variables

You can customize the job submission by setting environment variables before running `submit_batch.py`. It is **CRITICAL** to verify these values against your DLC environment.

*   `DLC_WORKSPACE_ID`: Your DLC workspace ID (default: `270969`).
*   `DLC_RESOURCE_ID`: Resource quota ID (default: `quotalplclkpgjgv`).
*   `DLC_IMAGE`: Docker image address (default: `pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118`).
*   `DLC_CODE_ROOT`: Path where the code is mounted in the container (default: `/cpfs/shared/simulation/zhuzihou/dev/render-usd`).

### Data Sources
The `launch_job.sh` script uses specific data source IDs by default: `d-phhmdh73h3zzv7pqh0,d-r70bzlwqnstu3rg55l,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz`.
Ensure these are correct for your dataset or pass them as the 4th argument to `launch_job.sh`.
