# 核心 API 参考

[English](core.md)

本节记录了负责渲染管线的核心模块。

## Renderer

**模块**: `src.render_usd.core.renderer`  
**源码**: [`src/render_usd/core/renderer.py`](../../src/render_usd/core/renderer.py)

### `RenderManager`

协调渲染过程的主类。

#### `__init__(self, app=None)`
初始化 RenderManager。
*   **app**: 模拟应用程序实例（可选）。

#### `render_thumbnail_wo_bg(self, object_usd_paths, thumbnail_wo_bg_dir, ...)`
渲染无背景的对象缩略图（使用默认环境）。
*   **object_usd_paths** (`List[Path]`): 对象 USD 文件路径列表。
*   **thumbnail_wo_bg_dir** (`Path`): 保存渲染缩略图的目录。
*   **show_bbox2d** (`bool`): 是否绘制 2D 边界框。
*   **sample_number** (`int`): 每个对象渲染的视图数量。

#### `render_thumbnail_with_bg(self, scene_usd_path, object_usd_dir, ...)`
在场景背景中渲染对象缩略图。
*   **scene_usd_path**: 场景 USD 文件路径。
*   **object_usd_dir**: 包含对象模型的目录。

---

## Camera

**模块**: `src.render_usd.core.camera`  
**源码**: [`src/render_usd/core/camera.py`](../../src/render_usd/core/camera.py)

### 初始化

#### `init_camera(camera_name, image_width, image_height, ...)`
在 USD 舞台中创建一个新的 Camera prim。

#### `setup_camera(camera, focal_length, ...)`
配置相机参数（焦距、光圈）并附加标注器（RGB、深度、BBox）。

### 操作

#### `set_camera_look_at(camera, target, distance, elevation, azimuth)`
设置相机位姿，使其从球坐标位置看向目标。

### 数据提取

#### `get_src(camera, type)`
传感器数据的通用获取器。
*   **type** (`str`): `'rgb'`, `'depth'`, `'bbox2d_tight'` 等之一。

---

## Scene

**模块**: `src.render_usd.core.scene`  
**源码**: [`src/render_usd/core/scene.py`](../../src/render_usd/core/scene.py)

#### `init_world(stage_units_in_meters, ...)`
初始化 Isaac Sim `World` 实例。

#### `setup_environment(env_path)`
加载环境光照。如果缺少 `env_path`，则创建回退的 Dome Light。

#### `setup_instance_scene(stage)`
遍历舞台并将语义标签分配给对象 prim。
