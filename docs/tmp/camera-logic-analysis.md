# Camera Distance Calculation Logic Analysis

> Analyzed by: code-analyzer agent
> Date: 2026-03-08
> Scope: Complete logic chain from USD loading to camera positioning

---

## 1. Overview: End-to-End Data Flow

```
CLI (cli.py)
  -> RenderManager.__init__() -> init_world() [stage_units_in_meters=1.0]
  -> render_thumbnail_wo_bg() or render_thumbnail_with_bg()
       -> create_prim(show_prim_path, position=(0,0,0), scale=(1,1,1), usd_path=...)
       -> compute_bbox(usd_prim)  [world-space AABB]
       -> center = (bbox_min + bbox_max) / 2
       -> distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
       -> distance = np.clip(distance, 0.1, 100.0)
       -> set_camera_look_at(camera, center, azimuth, elevation, distance)
            -> spherical-to-cartesian offset
            -> camera.set_world_pose(position, orientation)
```

---

## 2. Prim Loading (scene.py + renderer.py)

### 2.1 `render_thumbnail_wo_bg()` (renderer.py:188-191)

```python
show_prim_path = "/World/Show"
usd_prim = create_prim(show_prim_path, position=(0, 0, 0), scale=(1, 1, 1), usd_path=str(object_usd_path))
```

- Uses `omni.isaac.core.utils.prims.create_prim` from Isaac Sim
- Position is always `(0, 0, 0)`, scale is always `(1, 1, 1)`
- **No normalization or fit-to-view**: the object is loaded at its original size and placed at origin
- The prim inherits whatever transforms are baked into the USD file itself

### 2.2 `render_thumbnail_with_bg()` (renderer.py:324)

```python
add_reference_to_stage(str(scene_usd_path), "/World/scene")
```

- Scene is loaded as a reference; individual mesh prims are iterated from the scene hierarchy
- No explicit scale/transform is applied by the code
- Objects retain their scene-space transforms

### 2.3 `init_world()` (scene.py:17-28)

```python
world = World(stage_units_in_meters=1.0, ...)
```

- `stage_units_in_meters=1.0` means 1 USD unit = 1 meter
- **If the USD file was authored with different stage units** (e.g., centimeters), this could cause a size mismatch. However, Isaac Sim's `create_prim` with `usd_path` typically respects the referenced file's layer metrics.

---

## 3. Bounding Box Computation (prim_utils.py:114-131)

```python
def compute_bbox(prim: Usd.Prim) -> np.ndarray:
    imageable = UsdGeom.Imageable(prim)
    time = Usd.TimeCode.Default()
    bound = imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
    bound_range = bound.ComputeAlignedBox()
    bbox_min = bound_range.min
    bbox_max = bound_range.max
    return np.array([bbox_min, bbox_max])
```

### Key Properties:

1. **`ComputeWorldBound()`**: This is a USD API that computes the **world-space** bounding box. It **includes all transforms** in the prim hierarchy (translate, rotate, scale, including parent transforms).

2. **`ComputeAlignedBox()`**: Converts the oriented bounding box to an **axis-aligned bounding box (AABB)** in world space.

3. **Transform-aware**: Because `ComputeWorldBound` traverses the full transform hierarchy, any `xformOp:scale`, `xformOp:translate`, or `xformOp:rotateXYZ` on the prim or its ancestors **are fully accounted for**.

4. **Returns world-space coordinates**: The bbox min/max are in world space, which is consistent with how the camera is positioned.

### Potential Issues:

- If the prim at `/World/Show` has identity transform (position=0, scale=1) but the internal USD has deeply nested transforms, those are correctly captured by `ComputeWorldBound`.
- **No issue with scale not being reflected in bbox** -- `ComputeWorldBound` handles this correctly.

---

## 4. Distance Calculation (renderer.py:221-225)

```python
center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0
distance = np.clip(distance, 0.1, 100.0)
```

### Analysis:

- `bbox_max - bbox_min` is the **AABB diagonal vector** `(dx, dy, dz)`
- `np.linalg.norm(bbox_max - bbox_min)` = `sqrt(dx^2 + dy^2 + dz^2)` = **the spatial diagonal length of the bounding box**
- The multiplier is `* 1.0` (effectively no scaling)
- Distance is clamped to `[0.1, 100.0]` meters

### What this means geometrically:

- **distance = diagonal of the AABB**
- For a cube of side `s`, diagonal = `s * sqrt(3)` ~= `1.73s`
- For a flat/elongated object, the diagonal is dominated by the longest dimension

### Is this a good camera distance?

The distance determines how far the camera is from the object center. Whether the object fits in the frame depends on:
1. The distance (diagonal of AABB)
2. The camera's field of view (FOV)
3. The elevation angle (35 degrees, which slightly increases the effective distance to the object center)

**Camera FOV calculation** (from `setup_camera` defaults):
- `focal_length = 18.0 mm`
- `horizontal_aperture = 20.0955 mm`
- `vertical_aperture = 15.2908 mm`
- Horizontal FOV = `2 * atan(horizontal_aperture / (2 * focal_length))` = `2 * atan(20.0955 / 36)` = `2 * atan(0.558)` = `2 * 29.15 deg` = **~58.3 degrees**
- Vertical FOV = `2 * atan(15.2908 / 36)` = `2 * atan(0.4247)` = `2 * 23.03 deg` = **~46.1 degrees**

**Fit check**: At distance `d` with horizontal half-FOV `theta`:
- Visible half-width at target = `d * tan(theta)`
- With `d = diagonal`, `theta = 29.15 deg`:
  - Visible half-width = `diagonal * tan(29.15 deg)` = `diagonal * 0.558`
  - Full visible width = `diagonal * 1.116`

For the object to fit horizontally, we need `object_width <= visible_width`:
- Object width (max) ~= diagonal (for a cube), so `diagonal <= diagonal * 1.116` -- **barely fits for cubic objects**
- For elongated objects viewed from certain angles, the object could clip

**At 35-degree elevation**, the camera is raised, so the projected size of the object is slightly smaller, giving a bit more margin.

### Conclusion on distance formula:

The formula `distance = AABB_diagonal * 1.0` places the camera at roughly the diagonal distance, which makes the object **fill most of the frame** for typical objects. This is reasonable but could be tight for objects that are much wider than tall (or vice versa) when viewed from certain angles.

---

## 5. Camera Positioning (camera.py:28-49)

```python
def set_camera_look_at(camera, target, distance=0.4, elevation=90.0, azimuth=0.0):
    target_position = target  # (or XFormPrim world pose)

    elev_rad = math.radians(elevation)
    azim_rad = math.radians(azimuth)
    offset_x = distance * math.cos(elev_rad) * math.cos(azim_rad)
    offset_y = distance * math.cos(elev_rad) * math.sin(azim_rad)
    offset_z = distance * math.sin(elev_rad)
    camera_position = target_position + np.array([offset_x, offset_y, offset_z])

    rot = R.from_euler("xyz", [0, elevation, azimuth - 180], degrees=True)
    quaternion = rot.as_quat()  # scipy returns [x, y, z, w]
    quaternion = np.array([quaternion[3], quaternion[0], quaternion[1], quaternion[2]])  # convert to [w, x, y, z]
    camera.set_world_pose(position=camera_position, orientation=quaternion)
```

### Spherical Coordinate System:

- **Azimuth**: Angle in the XY plane from +X axis, counter-clockwise
  - `azimuth=0` -> +X direction (front)
  - `azimuth=90` -> +Y direction (left)
  - `azimuth=180` -> -X direction (back)
  - `azimuth=270` -> -Y direction (right)
- **Elevation**: Angle above the XY plane
  - `elevation=35` -> camera is 35 degrees above horizontal
- **Distance**: Radial distance from target to camera

### Camera position:

At elevation=35, azimuth=0:
- `offset_x = d * cos(35) * cos(0) = d * 0.819 * 1.0 = 0.819d`
- `offset_y = d * cos(35) * sin(0) = 0`
- `offset_z = d * sin(35) = d * 0.574`
- Camera is at `(center_x + 0.819d, center_y, center_z + 0.574d)`

### Camera orientation:

- `R.from_euler("xyz", [0, 35, -180])` - rotates camera to look back toward target
- The `azimuth - 180` makes the camera face the opposite direction of its offset (i.e., look at the target)

### Horizontal distance to target:

The actual horizontal distance from camera to target center is `distance * cos(elevation)`:
- At elevation=35: horizontal_distance = `d * cos(35)` = `0.819d`
- This means the projected size of the object in the camera is slightly larger than if the camera were at the full distance `d`

---

## 6. `render_thumbnail_with_bg()` Specifics (renderer.py:305-440)

Differences from `wo_bg`:
- Uses `focal_length=9.0` (vs default 18.0) -- **wider FOV, roughly doubled**
- Image size `600x450` (vs `512x512`)
- 6 cameras (3 top + 3 bottom) instead of 4
- Same distance formula: `distance = np.linalg.norm(bbox_max - bbox_min) * 1.0`
- Azimuth starts at 30 degrees with 120-degree increments (for 3 views per hemisphere)
- Elevation: +35 for top views, -35 for bottom views

With `focal_length=9.0`:
- Horizontal FOV = `2 * atan(20.0955 / 18)` = `2 * atan(1.116)` = `2 * 48.15 deg` = **~96.3 degrees**
- This much wider FOV means objects appear much smaller relative to frame -- more context visible

---

## 7. Summary of Key Findings

### Distance Formula
```
distance = ||bbox_max - bbox_min||_2  (AABB diagonal, world-space)
clamped to [0.1, 100.0]
```

### Bbox Computation
- Uses `UsdGeom.Imageable.ComputeWorldBound()` -- **correctly includes all transforms**
- Returns axis-aligned world-space bounding box
- **No transform/scale mismatch issues detected**

### No Fit-to-View or Normalization
- No automatic scaling/normalization of objects
- Objects are loaded at their native USD scale at origin
- Camera distance is purely derived from AABB diagonal

### Potential Issues Identified

1. **Tight framing for cubic objects**: With `distance = diagonal` and FOV ~58 degrees, cubic objects nearly fill the frame. If there's any rendering margin (anti-aliasing, slight positioning offsets), parts could clip.

2. **No aspect-ratio adaptation**: The distance formula uses the full 3D diagonal regardless of which dimension faces the camera. An elongated object viewed from its narrow side will appear small, while viewed from its long side it may clip.

3. **Elevation reduces effective horizontal distance**: At 35 degrees elevation, horizontal distance is `0.819 * diagonal`, which means the object's horizontal extent could potentially exceed the visible width for wide objects.

4. **Distance clamp at 100.0**: Objects with AABB diagonal > 100 meters will have the camera too close, causing clipping. Objects with diagonal < 0.1 meters will have the camera too far.

5. **Center calculation assumes AABB center**: For asymmetric objects, the visual center and AABB center may differ, potentially causing the object to appear off-center.

6. **No per-view distance adjustment**: The same distance is used for all viewpoints, but the projected size of the object varies with azimuth (especially for non-cubic objects).

### Constants Summary

| Parameter | `wo_bg` mode | `with_bg` mode |
|---|---|---|
| Image size | 512x512 | 600x450 |
| Focal length | 18.0 mm | 9.0 mm |
| H-aperture | 20.0955 mm | 20.0955 mm |
| V-aperture | 15.2908 mm | 15.2908 mm |
| H-FOV | ~58.3 deg | ~96.3 deg |
| V-FOV | ~46.1 deg | ~77.8 deg |
| Elevation | 35 deg | +/-35 deg |
| Distance multiplier | 1.0 | 1.0 |
| Distance clamp | [0.1, 100.0] | [0.1, 100.0] |
| Num views | 4 | 6 |
| Azimuth start | 0 deg | 30 deg |
| Azimuth step | 90 deg | 120 deg |

---

## 8. File Reference

| File | Key Lines | Function |
|---|---|---|
| `src/render_usd/core/renderer.py` | L208-225 | bbox computation + distance formula |
| `src/render_usd/core/renderer.py` | L191 | prim creation with scale=(1,1,1) |
| `src/render_usd/core/renderer.py` | L234-236 | camera look-at call |
| `src/render_usd/core/camera.py` | L28-49 | `set_camera_look_at()` spherical positioning |
| `src/render_usd/core/camera.py` | L52-86 | `setup_camera()` FOV/aperture defaults |
| `src/render_usd/utils/usd_utils/prim_utils.py` | L114-131 | `compute_bbox()` world-space AABB |
| `src/render_usd/core/scene.py` | L17-28 | `init_world()` with stage_units=1.0 |
| `src/render_usd/cli.py` | L115 | SimulationApp initialization |
