# 工具 API 参考

[English](utils.md)

用于 USD 操作、图像处理和配置的辅助函数。

## USD 工具

**源码**: `src/render_usd/utils/usd_utils/`

### `prim_utils.py`
*   `compute_bbox(prim)`: 计算 prim 的 3D 边界框。
*   `set_prim_cast_shadow_true(prim)`: 启用 prim 的阴影投射。

### `stage_utils.py`
*   `get_all_mesh_prims(stage)`: 递归查找所有 Mesh prim。
*   `switch_all_lights(stage, status)`: 打开/关闭所有灯光。

### `mdl_utils.py`
*   `fix_mdls(scene_path, mdl_base_path)`: 修复 USD 文件中损坏的 MDL 路径。

## 通用工具

**源码**: `src/render_usd/utils/common_utils/`

### `images_utils.py`
*   `draw_bbox2d(image, bbox_data)`: 在图像上绘制 2D 边界框矩形。

### `path_utils.py`
*   `find_all_files_in_folder(folder, extension)`: 递归查找具有给定扩展名的文件。

---

# 配置

**模块**: `src.render_usd.config.settings`  
**源码**: [`src/render_usd/config/settings.py`](../../src/render_usd/config/settings.py)

包含全局常量：
*   `DEFAULT_MDL_PATH`: 默认材质库的路径。
*   `DEFAULT_ENVIRONMENT_PATH`: 默认环境贴图 (`background.usd`) 的路径。
