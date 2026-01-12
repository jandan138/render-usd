# Getting Started

## Prerequisites

Before installing `render-usd`, ensure you have the following requirements met:

*   **Operating System**: Linux (Ubuntu 20.04+ recommended)
*   **Hardware**: NVIDIA GPU with RTX support (required for Isaac Sim rendering)
*   **Software**:
    *   [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
    *   [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim) (The package is designed to run within the Isaac Sim python environment)

## Installation

### 1. Clone the Repository
```bash
git clone <repository_url>
cd render-usd
```

### 2. Set up Conda Environment

We recommend using a dedicated Conda environment to manage dependencies.

```bash
# Create environment from provided YAML file
conda env create -f environment.yml

# Activate the environment
conda activate render-usd
```

### 3. Install the Package

Install the package in editable mode to allow for development changes to take effect immediately.

```bash
pip install -e .
```

## Setting up Assets

The renderer relies on certain assets (e.g., environment maps, materials). Ensure these are placed in the correct directory:

*   `assets/environments/`: Contains environment USD files (e.g., `background.usd`).
*   `assets/materials/`: Contains MDL material files (e.g., `default.mdl`).

> **Note**: If `background.usd` is missing, the renderer will automatically fallback to a default Dome Light.
