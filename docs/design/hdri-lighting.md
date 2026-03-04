# HDRI 环境光照技术方案

## 1. 问题背景

在使用 NVIDIA Isaac Sim 的 PathTracing 渲染器生成 3D 物体缩略图时，默认的照明方案存在严重的可视性问题：

- **白色物体在白色 DomeLight 下不可见**：当使用 `UsdLux.DomeLight` 并设置白色（1.0, 1.0, 1.0）作为颜色时，白色或浅色物体与纯白背景融为一体，无法区分物体轮廓。
- **DomeLight Color 同时控制背景色和光照色**：USD 的 DomeLight 没有独立的背景颜色属性——`Color` 属性既决定了环境光的颜色，也决定了渲染背景的颜色。无法单独调整其中一项而不影响另一项。

## 2. 方案选型

### 方案 A：修改 DomeLight 颜色

将 DomeLight 颜色从白色改为灰色（如 0.18, 0.18, 0.18），使背景变暗。

**缺点**：DomeLight Color 同时影响光照，灰色光源导致整体场景变暗，物体表面也变得黯淡无光，渲染质量下降。

### 方案 B：暗 DomeLight + DistantLight 补光

使用暗色 DomeLight 作为背景，再添加 `DistantLight` 从特定方向补充照明。

**缺点**：DistantLight 是单方向平行光，缺少环境光的漫反射效果，物体光照不够自然均匀，容易出现明显的阴影分界线。

### 方案 C：HDRI + backgroundZeroAlpha + Alpha 合成 ★

使用 HDRI（High Dynamic Range Image）作为 DomeLight 贴图提供真实的环境光照，同时通过 RTX 渲染器的 `backgroundZeroAlpha` 功能将背景设为透明（alpha=0），最后在后处理阶段将前景物体通过 alpha 合成到指定颜色的纯色背景上。

**优点**：
- HDRI 提供摄影棚级别的真实环境光照，光照自然均匀
- 背景颜色完全可控，不受光照影响
- 适用于任何颜色的物体，不存在可见性问题

**结论**：选择方案 C。

## 3. 技术实现

### 3.1 scene.py：HDRI DomeLight + 背景透明

在 `setup_environment()` 函数中，当环境 USD 文件不存在时（fallback 分支），动态查找 Isaac Sim 内置的 HDRI 贴图并创建 HDRI DomeLight：

```python
# 查找 Isaac Sim 内置的 HDRI 贴图
import isaacsim
candidate = os.path.join(
    os.path.dirname(os.path.dirname(isaacsim.__file__)),
    "isaacsim", "extscache",
    "omni.kit.widget.material_preview-1.0.16",
    "data", "photo_studio_01_4k.hdr")

# 创建 DomeLight 并设置 HDRI 贴图
dome_light = UsdLux.DomeLight.Define(stage, "/World/default_dome_light")
dome_light.CreateTextureFormatAttr(UsdLux.Tokens.latlong)
dome_light.CreateIntensityAttr(1500)
dome_light.CreateTextureFileAttr(hdri_path)
dome_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
```

然后通过 carb settings 启用背景透明：

```python
settings = carb.settings.get_settings()
settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
settings.set("/app/captureFrame/setAlphaTo1", False)
```

如果找不到 HDRI 贴图，则回退到灰色 DomeLight（intensity=1000, color=0.18）。

### 3.2 camera.py：新增 get_rgba() 函数

新增 `get_rgba()` 函数，返回完整的 4 通道 RGBA 数据（包含 alpha 通道），用于后续的 alpha 合成：

```python
def get_rgba(camera: Camera) -> Optional[np.ndarray]:
    frame = camera.get_rgba()
    if isinstance(frame, np.ndarray) and frame.size > 0:
        return frame
    else:
        return None
```

同时在 `get_src()` 调度函数中注册了 `"rgba"` 类型，使其可通过统一接口获取 RGBA 数据。

原有的 `get_rgb()` 函数也更新为调用 `camera.get_rgba()` 后截取前 3 通道，保持向后兼容。

### 3.3 renderer.py：Alpha 合成

在 `render_thumbnail_wo_bg()` 方法中，渲染流程改为：

1. 通过 `get_src(camera, "rgba")` 获取 RGBA 4 通道图像
2. 提取 alpha 通道并归一化到 [0, 1]
3. 创建深灰色背景 RGB(40, 40, 40)
4. 使用标准 alpha 合成公式混合前景和背景

```python
rgba = get_src(camera, "rgba")
if rgba is not None and rgba.shape[2] == 4:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)  # 深灰色 RGB(40,40,40)
    rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
else:
    rgb = get_src(camera, "rgb")  # fallback
```

**合成公式**：`output = foreground * alpha + background * (1 - alpha)`

- alpha=1 的像素（物体区域）显示物体本身的颜色
- alpha=0 的像素（背景区域）显示深灰色 (40, 40, 40)
- 物体边缘的半透明像素自然过渡，避免锯齿

## 4. RTX Settings 说明

| Setting | 值 | 作用 |
|---|---|---|
| `/rtx/post/backgroundZeroAlpha/enabled` | `True` | 启用背景透明功能，使 HDRI 天空盒区域的 alpha 值为 0，而物体区域的 alpha 为 255 |
| `/rtx/post/backgroundZeroAlpha/backgroundComposite` | `False` | 禁止渲染器自动将背景合成到输出帧中，保持背景区域为纯透明 |
| `/rtx/post/backgroundZeroAlpha/outputAlphaInComposite` | `True` | 确保合成输出中保留 alpha 通道信息，使 `camera.get_rgba()` 能获取到有效的 alpha 数据 |
| `/app/captureFrame/setAlphaTo1` | `False` | 禁止截图时将所有像素的 alpha 强制设为 1（不透明），否则会覆盖掉 backgroundZeroAlpha 的效果 |

这四个设置缺一不可，共同确保渲染器输出的 RGBA 帧中：
- 物体像素：alpha = 255（完全不透明）
- 背景像素：alpha = 0（完全透明）
- 边缘像素：alpha 介于 0-255（半透明抗锯齿）

## 5. HDRI 来源

使用的 HDRI 文件为 Isaac Sim 内置的 `photo_studio_01_4k.hdr`，位于 Isaac Sim 扩展缓存目录中：

```
{isaacsim_root}/isaacsim/extscache/omni.kit.widget.material_preview-1.0.16/data/photo_studio_01_4k.hdr
```

这是一个 4K 分辨率的摄影棚风格 HDRI 环境贴图，具有以下特点：

- **摄影棚布光**：模拟专业摄影棚的柔和均匀光照，适合产品级物体展示
- **无明显方向性**：光照来自多个方向，物体各面都能获得适当照明
- **中性色温**：不会给物体带来明显的色偏

代码通过 `isaacsim` 包的安装路径动态定位该文件，无需额外下载或配置。如果查找失败，自动回退到灰色 DomeLight 方案。
