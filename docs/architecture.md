# Architecture Overview

## System Design

`render-usd` is designed as a modular rendering pipeline built on top of NVIDIA Isaac Sim's Python API. It separates the concerns of scene management, camera control, and high-level rendering flow.

### Core Modules

The core logic resides in `src/render_usd/core/`:

1.  **[Renderer](api/core.md#renderer)** (`renderer.py`):
    *   **Role**: Orchestrator.
    *   **Responsibilities**: Manages the main rendering loop, coordinates between Scene and Camera modules, handles file I/O, and executes rendering steps.
    *   **Key Class**: `RenderManager`

2.  **[Scene](api/core.md#scene)** (`scene.py`):
    *   **Role**: Stage Manager.
    *   **Responsibilities**: Initializes the Isaac Sim `World`, loads USD stages, sets up environment lighting (Dome Light/HDRI), and manages object semantics.

3.  **[Camera](api/core.md#camera)** (`camera.py`):
    *   **Role**: Sensor Manager.
    *   **Responsibilities**: Creates and configures cameras, handles coordinate transformations (look-at logic), and extracts sensor data (RGB, Depth, Bounding Boxes).

## Directory Structure

```
render-usd/
├── assets/                 # External assets (environments, materials)
├── docs/                   # Documentation (You are here)
├── examples/               # Example USD files and outputs
├── scripts/                # Utility scripts (DLC submission, batch processing)
├── src/
│   └── render_usd/
│       ├── config/         # Configuration settings
│       ├── core/           # Core rendering modules (renderer, scene, camera)
│       └── utils/          # Helper utilities (USD, images, math)
├── environment.yml         # Conda environment definition
└── pyproject.toml          # Project metadata
```

## Data Flow

1.  **Input**: The user provides a path to a USD file or a directory via CLI.
2.  **Initialization**: `RenderManager` initializes the `World` via `Scene` module.
3.  **Setup**:
    *   `Scene` loads the USD stage and sets up lighting.
    *   `Camera` initializes sensors based on configuration.
4.  **Rendering Loop**:
    *   `RenderManager` iterates through defined viewpoints.
    *   `Camera` updates pose (position/orientation).
    *   `World` steps the physics/rendering simulation.
5.  **Extraction**: `Camera` extracts render products (RGB images, BBox data).
6.  **Output**: Images and metadata are saved to the specified output directory.
