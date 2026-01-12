# Utilities API Reference

[中文版](utils_zh.md)

Helper functions for USD manipulation, image processing, and configuration.

## USD Utilities

**Source**: `src/render_usd/utils/usd_utils/`

### `prim_utils.py`
*   `compute_bbox(prim)`: Computes the 3D bounding box of a prim.
*   `set_prim_cast_shadow_true(prim)`: Enables shadow casting for a prim.

### `stage_utils.py`
*   `get_all_mesh_prims(stage)`: Recursively finds all Mesh prims.
*   `switch_all_lights(stage, status)`: Turns all lights on/off.

### `mdl_utils.py`
*   `fix_mdls(scene_path, mdl_base_path)`: Fixes broken MDL paths in a USD file.

## Common Utilities

**Source**: `src/render_usd/utils/common_utils/`

### `images_utils.py`
*   `draw_bbox2d(image, bbox_data)`: Draws a 2D bounding box rectangle on an image.

### `path_utils.py`
*   `find_all_files_in_folder(folder, extension)`: Recursively finds files with a given extension.

---

# Configuration

**Module**: `src.render_usd.config.settings`  
**Source**: [`src/render_usd/config/settings.py`](../../src/render_usd/config/settings.py)

Contains global constants:
*   `DEFAULT_MDL_PATH`: Path to the default material library.
*   `DEFAULT_ENVIRONMENT_PATH`: Path to the default environment map (`background.usd`).
