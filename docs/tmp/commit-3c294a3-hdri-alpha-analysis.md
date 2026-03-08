# Commit 3c294a3 深度分析：HDRI环境光与backgroundZeroAlpha对相机的影响

## 执行摘要

**结论**：提交 3c294a3 （HDRI 灯光 + backgroundZeroAlpha + RGBA 合成）**对相机参数和视角几何没有任何影响**。

| 方面 | 状态 | 证据 |
|---|---|---|
| 焦距 (focal_length) | ✓ 未改变 | camera.py:68, 仍为 18.0mm |
| 近/远裁剪面 (clipping) | ✓ 未改变 | camera.py:69, 仍为 [0.01, 1000000] |
| 光圈 (apertures) | ✓ 未改变 | camera.py:70-71, vertical=15.2908, horizontal=20.0955 |
| 视场角 (FOV) | ✓ 未改变 | 由焦距和光圈计算，两者都不变 |
| 相机位置计算 | ✓ 未改变 | camera.py:46 球坐标数学完全相同 |
| 距离公式 | ✓ 未改变 | renderer.py:222, distance = bbox_diagonal * 1.0 |
| Alpha合成 | ⚠️ 无视觉放大 | 标准α混合公式，不改变几何 |

---

## 1. 提交内容分析

### 1.1 改动范围

提交 3c294a3 共改动 3 个文件：

#### scene.py（39 行新增）
```python
# 1. 动态查找 Isaac Sim 内置 HDRI 贴图
hdri_path = os.path.join(..., "photo_studio_01_4k.hdr")

# 2. 创建 HDRI DomeLight
dome_light.CreateTextureFileAttr(hdri_path)
dome_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
dome_light.CreateIntensityAttr(1500)  # 从 1000 改为 1500

# 3. 启用 RTX 后处理设置（关键！）
settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
settings.set("/app/captureFrame/setAlphaTo1", False)
```

#### camera.py（新增 get_rgba() 函数）
```python
def get_rgba(camera: Camera) -> Optional[np.ndarray]:
    frame = camera.get_rgba()
    if isinstance(frame, np.ndarray) and frame.size > 0:
        return frame
    else:
        return None
```

以及在 `get_src()` 中注册 "rgba" 类型。

#### renderer.py（RGBA 合成）
```python
rgba = get_src(camera, "rgba")
if rgba is not None and rgba.shape[2] == 4:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)
    rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
else:
    rgb = get_src(camera, "rgb")
```

---

## 2. RTX backgroundZeroAlpha 机制分析

### 2.1 四个 carb.settings 的作用

| 设置项 | 值 | 作用 | 对相机的影响 |
|---|---|---|---|
| `/rtx/post/backgroundZeroAlpha/enabled` | True | 启用背景透明后处理 | **无** |
| `/rtx/post/backgroundZeroAlpha/backgroundComposite` | False | 禁止渲染器自动合成背景 | **无** |
| `/rtx/post/backgroundZeroAlpha/outputAlphaInComposite` | True | 保留合成输出中的 alpha 通道 | **无** |
| `/app/captureFrame/setAlphaTo1` | False | 禁止强制 alpha=1 | **无** |

### 2.2 backgroundZeroAlpha 是后处理，不是相机参数

```
PathTracing 渲染流程：
1. 相机参数确定（焦距、光圈、近/远裁剪）
2. 光线追踪（发射光线，击中物体或背景）
3. 物理渲染器输出 RGBA 帧（物体RGB + HDRI背景RGB + 深度）
4. POST-PROCESS：backgroundZeroAlpha 修改 alpha 通道
   - 背景像素 alpha = 0
   - 物体像素 alpha = 255
   - 边缘像素 alpha = 0-255（抗锯齿）
5. 返回 RGBA 帧给应用
```

**关键点**：backgroundZeroAlpha 只修改 alpha 通道值，不修改 RGB 像素颜色。物体在场景中的 **几何投影** 完全不变。

### 2.3 与相机参数的隔离

相机参数设置位置（camera.py:52-86 `setup_camera()` 函数）：
```python
camera.set_focal_length(focal_length)           # 18.0 (不变)
camera.set_clipping_range(min, max)              # [0.01, 1000000] (不变)
camera.set_vertical_aperture(vertical_aperture)  # 15.2908 (不变)
camera.set_horizontal_aperture(horizontal_aperture)  # 20.0955 (不变)
```

RTX 渲染设置位置（scene.py:67-71 `setup_environment()` 中的新代码）：
```python
settings.set("/rtx/post/backgroundZeroAlpha/...")
settings.set("/app/captureFrame/...")
```

**两套系统完全独立**。RTX 设置与 camera 对象无直接调用。

---

## 3. 相机距离公式完全未变

### 3.1 距离计算（renderer.py:222）

```python
bbox_min, bbox_max = compute_bbox(usd_prim)  # 计算包围盒
center = (bbox_min + bbox_max) / 2            # 计算中心
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0  # 对角线长度 × 1.0
distance = np.clip(distance, 0.1, 100.0)     # 限制范围
```

**git diff 显示**：这三行从未改过，3c294a3 提交完全未触及这部分代码。

### 3.2 距离使用（renderer.py:236）

```python
set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)
```

`set_camera_look_at()` 函数（camera.py:28-49）使用球坐标：
```python
elev_rad = math.radians(elevation)  # 35° (固定)
azim_rad = math.radians(azimuth)    # 0°, 90°, 180°, 270°
offset_x = distance * math.cos(elev_rad) * math.cos(azim_rad)
offset_y = distance * math.cos(elev_rad) * math.sin(azim_rad)
offset_z = distance * math.sin(elev_rad)
camera_position = target_position + np.array([offset_x, offset_y, offset_z])
```

**git diff 显示**：这个球坐标计算从未改过，3c294a3 完全未触及相机位置的数学。

---

## 4. Alpha 合成的视觉效果分析

### 4.1 α混合公式（renderer.py:263）

```
output_color = foreground_color * alpha + background_color * (1 - alpha)
```

其中：
- `foreground_color` = 渲染的物体 RGB（由 HDRI PathTracing 计算）
- `background_color` = RGB(40, 40, 40)（深灰色）
- `alpha` = 物体像素=255 (1.0)，背景像素=0 (0.0)

### 4.2 三种像素情况

| 像素类型 | alpha 值 | 计算结果 | 视觉结果 |
|---|---|---|---|
| 物体内部 | 1.0 (255) | output = foreground * 1.0 + bg * 0.0 = foreground | 显示物体原始颜色 |
| 背景区域 | 0.0 (0) | output = foreground * 0.0 + bg * 1.0 = bg | 显示深灰色背景 |
| 边缘像素 | 0.5 (128) | output = foreground * 0.5 + bg * 0.5 | 物体颜色与灰色等量混合 |

### 4.3 是否造成视觉"放大"？

**答案：否**

**论证**：
1. **Alpha 混合不改变几何**：α混合是 2D 图像处理操作，在像素值合并后执行。物体在 3D 空间中的投影尺寸已由相机参数确定，合成公式无法改变已有的像素。

2. **输出像素数量不变**：RGBA 帧仍为 512×512，经过 α混合后仍为 512×512。没有超采样、放大、或投影变换。

3. **标准 2D 图形操作**：这个公式是所有 2D 图形库（OpenGL、DirectX、Pygame）中的标准操作，不会产生几何变形。

**反例验证**：
```python
# 如果 alpha=1 的像素被"放大"，以下应该成立：
# 但实际上，物体像素逐个映射，无任何缩放
for pixel in object_region:
    output[pixel] = rgba[pixel, :3] * 1.0 + bg * 0.0
    # 完全等于 rgb[pixel, :3]，没有任何变换
```

---

## 5. HDRI 对距离的影响分析

### 5.1 DomeLight.CreateIntensityAttr(1500) vs 旧版 (1000)

**Intensity 定义**：控制环境光的照度强度，单位为勒克斯 (lux)。

**对相机的影响**：无

- 相机焦距、光圈、位置：不受影响
- 渲染的 RGB 值（亮度）：会增加（但不改变几何）
- bbox、距离计算：无影响

### 5.2 背景色的转变

| 版本 | DomeLight Color | 背景外观 | 物体距离 |
|---|---|---|---|
| 旧版 | (1.0, 1.0, 1.0) 白色 | 纯白 | 100% |
| 新版（HDRI） | HDRI 纹理 | HDRI 纹理（后被 backgroundZeroAlpha 去除） | 100% |
| 新版（无HDRI） | (0.18, 0.18, 0.18) 灰色 | 灰色 | 100% |

**没有任何情况下改变物体距离**。

---

## 6. carb.settings 是否有隐藏相机参数？

### 6.1 检查 carb.settings 前缀

提交 3c294a3 中设置的 carb.settings：
```
/rtx/post/backgroundZeroAlpha/*     - 后处理（RGB组合）
/app/captureFrame/*                 - 帧捕获选项
```

Isaac Sim 已知的相机相关设置（若有）应该在：
```
/app/camera/*                       - 相机通用设置
/camera/*                           - 相机参数
/rtx/camera/*                       - RTX 相机参数（射线追踪）
```

**检查结果**：提交 3c294a3 中完全未设置这些前缀，只是后处理和帧捕获选项。

### 6.2 结论

carb.settings 中没有隐藏相机参数的修改。

---

## 7. 可能导致"物体过近"的真实原因

根据 `camera-distance-investigation-report.md` 的分析，3c294a3 **不是** 罪魁祸首，更可疑的是：

### 原因 A：`world.reset()` 在渲染循环中（提交 a31f3ee，同一天）

```python
# 新代码（3月4日）
for each object:
    self.world.reset()  ← 每次都 reset！
    create_prim → compute_bbox → render → delete_prim
```

`world.reset()` 重置物理世界、渲染状态等。如果 DomeLight 在 `setup_environment()` 后被创建，而 `world.reset()` 会清空它，那么后续渲染会使用错误的灯光配置。

### 原因 B：环境差异

- **旧渲染（1月19日）**：本地开发机，Isaac Sim 版本 X
- **新渲染（3月5日）**：DLC 集群，Docker 镜像 `isaacsim41-cuda118`，Isaac Sim 版本可能不同
- 同一 USD 文件（MD5 校验相同），但不同环境产生不同结果

### 原因 C：GRScenes 特定问题

问题仅在 `render_custom` 模式（GRScenes 资产）出现，不在单个 USD 测试中出现。这表明可能是：
- 多物体场景中的灯光缓存问题
- 材质解析与 MDL 搜索路径的复杂交互
- GRScenes 资产的特殊 USD 结构

---

## 8. 结论

### 主要发现

✅ **提交 3c294a3 在以下方面 100% 安全**：
- 相机焦距（18.0mm）
- 相机裁剪范围（[0.01, 1000000]）
- 相机光圈（vertical, horizontal）
- 视场角（由焦距和光圈计算）
- 相机位置和朝向（球坐标数学不变）
- 物体距离公式（`distance = bbox_diagonal * 1.0`）
- Alpha 合成（标准 2D 混合，无几何变形）

⚠️ **提交 3c294a3 中可能有隐患的部分**：
- 无（所有改动都是灯光和后处理，与相机几何完全隔离）

🔴 **真正可疑的改动**：
- 提交 **a31f3ee** 中的 `world.reset()` 在渲染循环中
- 运行环境差异（本地 vs DLC 集群）
- GRScenes 资产的特殊处理

### 建议

如果需要解决"物体过近"的问题，应该重点调查：

1. **临时禁用 world.reset()**（环境变量开关）
2. **调查 setup_environment() 是否在 world.reset() 后需要重新调用**
3. **对比本地 dev 机器和 DLC 集群的 Isaac Sim 版本和行为差异**

---

## 附录：数据引用

### camera.py 完整相机参数（未改变）

```python
def setup_camera(
    camera: Camera,
    focal_length: float = 18.0,              # 未改变
    clipping_range_min: float = 0.01,       # 未改变
    clipping_range_max: float = 1000000.0,  # 未改变
    vertical_aperture: float = 15.2908,     # 未改变
    horizontal_aperture: float = 20.0955,   # 未改变
    ...
) -> None:
    camera.set_focal_length(focal_length)
    camera.set_clipping_range(clipping_range_min, clipping_range_max)
    camera.set_vertical_aperture(vertical_aperture)
    camera.set_horizontal_aperture(horizontal_aperture)
```

### scene.py DomeLight 参数变化

| 参数 | 旧版（无HDRI） | 新版（有HDRI） | 新版（无HDRI） |
|---|---|---|---|
| Color | (1.0, 1.0, 1.0) 白色 | HDRI 纹理 | (0.18, 0.18, 0.18) 灰色 |
| Intensity | 1000 | 1500 | 1000 |
| TextureFile | 无 | photo_studio_01_4k.hdr | 无 |

### renderer.py 距离公式（未改变）

```python
# 第 208 行：compute_bbox 从未改过
bbox_min, bbox_max = compute_bbox(usd_prim)

# 第 221-222 行：距离计算完全相同
center = (bbox_min + bbox_max) / 2
distance = np.linalg.norm(bbox_max - bbox_min) * 1.0

# 第 225 行：clipping 也是常数（无改动）
distance = np.clip(distance, 0.1, 100.0)
```

---

## 相关文档

- `docs/tmp/camera-distance-investigation-report.md` - 距离变化调查
- `docs/design/hdri-lighting.md` - HDRI 技术方案详细说明
- `docs/guides/lighting-guide.md` - 照明指南
