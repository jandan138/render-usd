# Core API Reference

[中文版](core_zh.md)

This section documents the core modules responsible for the rendering pipeline.

## Renderer

**Module**: `src.render_usd.core.renderer`  
**Source**: [`src/render_usd/core/renderer.py`](../../src/render_usd/core/renderer.py)

### `RenderManager`

The main class that orchestrates the rendering process.

#### `__init__(self, app=None)`
Initialize the RenderManager.
*   **app**: The simulation application instance (optional).

#### `render_thumbnail_wo_bg(self, object_usd_paths, thumbnail_wo_bg_dir, ...)`
Render thumbnails for objects without a background (using a default environment).
*   **object_usd_paths** (`List[Path]`): List of paths to the object USD files.
*   **thumbnail_wo_bg_dir** (`Path`): Directory to save the rendered thumbnails.
*   **show_bbox2d** (`bool`): Whether to draw 2D bounding boxes.
*   **sample_number** (`int`): Number of views to render per object.

#### `render_thumbnail_with_bg(self, scene_usd_path, object_usd_dir, ...)`
Render thumbnails for objects within a scene background.
*   **scene_usd_path**: Path to the scene USD file.
*   **object_usd_dir**: Directory containing object models.

---

## Camera

**Module**: `src.render_usd.core.camera`  
**Source**: [`src/render_usd/core/camera.py`](../../src/render_usd/core/camera.py)

### Initialization

#### `init_camera(camera_name, image_width, image_height, ...)`
Creates a new Camera prim in the USD stage.

#### `setup_camera(camera, focal_length, ...)`
Configures camera parameters (focal length, aperture) and attaches annotators (RGB, Depth, BBox).

### Manipulation

#### `set_camera_look_at(camera, target, distance, elevation, azimuth)`
Sets the camera pose to look at a target from a spherical coordinate position.

### Data Extraction

#### `get_src(camera, type)`
Generic getter for sensor data.
*   **type** (`str`): One of `'rgb'`, `'depth'`, `'bbox2d_tight'`, etc.

---

## Scene

**Module**: `src.render_usd.core.scene`  
**Source**: [`src/render_usd/core/scene.py`](../../src/render_usd/core/scene.py)

#### `init_world(stage_units_in_meters, ...)`
Initializes the Isaac Sim `World` instance.

#### `setup_environment(env_path)`
Loads the environment lighting. If `env_path` is missing, creates a fallback Dome Light.

#### `setup_instance_scene(stage)`
Iterates through the stage and assigns semantic labels to object prims.
