# 渲染管线环境光照入门指南

> 面向不了解 Isaac Sim 的新人，深入浅出地介绍 render-usd 项目中环境光照的工作原理。

---

## 1. 为什么需要环境光照？

想象你在一间**完全没有窗户、没有灯的暗房**里拍照——按下快门，得到的只是一片漆黑。

3D 渲染也是同理。在虚拟场景里，如果没有任何光源，渲染器「看不到」物体，输出的图片就是纯黑一片。反过来，如果灯太亮、太集中，就像拿手电筒直射——物体表面一片死白（过曝），细节全丢了。

所以，我们需要一个「摄影棚级别」的灯光系统：亮度合适、方向均匀，让物体的形状、颜色和材质都能被清晰地呈现出来。

---

## 2. 什么是 DomeLight？

DomeLight（穹顶灯）可以理解为一个**包裹整个场景的巨大发光球体**。

生活中最接近的例子是**阴天的天空**——阴天时，云层把太阳光打散，从四面八方均匀地照下来。站在户外，你不会看到明显的影子，光线柔和而均匀。DomeLight 就是在虚拟世界中模拟这种「无处不在的柔和光」。

在我们的代码中（`scene.py`），创建 DomeLight 的关键代码如下：

```python
dome_light = UsdLux.DomeLight.Define(stage, "/World/default_dome_light")
dome_light.CreateIntensityAttr(1500)   # 光照强度
dome_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))  # 白色光
```

- `IntensityAttr(1500)` 控制亮度，数值越大越亮
- `ColorAttr` 控制光的颜色，`(1.0, 1.0, 1.0)` 是纯白光

---

## 3. 什么是 HDRI？

HDRI（High Dynamic Range Image，高动态范围图像）是一种特殊的**360 度全景照片**。

你可以这样理解：

1. 站在真实世界的摄影棚里，用全景相机拍一张照片
2. 这张照片记录了**每个方向**的光照强度和颜色——天花板上的灯、窗户透进来的日光、墙壁反射的暖色调……
3. 把这张全景照片「贴」在 DomeLight 的球体内壁上

这样一来，DomeLight 就不再是单调的白光球，而是像真实摄影棚一样，从不同方向发出不同强度和颜色的光。物体被照亮后，会呈现出非常自然的光影效果——高光、反光、阴影都像在真实环境中拍摄的一样。

在代码中，HDRI 纹理的加载方式：

```python
dome_light.CreateTextureFileAttr(hdri_path)   # 加载 HDRI 全景图
dome_light.CreateTextureFormatAttr(UsdLux.Tokens.latlong)  # 使用经纬度映射格式
```

我们项目使用的 HDRI 文件是 `photo_studio_01_4k.hdr`，这是一个摄影棚环境的 4K 全景图，随 Isaac Sim 附带。

---

## 4. 白色物体为什么看不见？

这是一个非常常见的问题。

物理学原理很简单：**物体的颜色 = 它反射的光的颜色**。一个白色的杯子之所以看起来白，是因为它几乎把所有照射到它身上的光都反射回来了。

现在想象这样的场景：

- 背景：纯白色
- 灯光：纯白色的 DomeLight
- 物体：一个白色的花瓶

结果就是——花瓶反射了白色的光，背景也是白色，两者完全融为一体，你根本看不出花瓶在哪里。就像在白纸上用白色笔画画一样。

不仅白色物体有这个问题，任何浅色、高反射率的物体（银色金属、浅灰色塑料等）在均匀白光+白色背景下都会「消失」。

---

## 5. 我们的解决方案 —— 绿幕原理！

你看过电影幕后花絮吗？演员站在一面巨大的**绿色幕布**前表演，后期制作时用软件把绿色替换成太空、城市、魔法森林……绿幕本身不会出现在最终画面里，但拍摄时灯光是真实打在演员身上的。

我们的管线做的事情**完全一样**，只不过分三步：

### 第一步：用 HDRI DomeLight 照亮物体

HDRI 提供真实的光照环境，物体被自然地照亮，有高光、有阴影。这一步保证物体好看。

### 第二步：用 RTX backgroundZeroAlpha 让背景透明

这是 NVIDIA RTX 渲染器的一个特殊设置。开启后，渲染器会把「没有物体的区域」标记为透明（alpha = 0），而物体本身保持不透明（alpha = 1）。

就像绿幕拍摄——灯光真实地照亮了演员（物体），但背景被标记为「可替换」。

代码中的关键设置（`scene.py`）：

```python
settings = carb.settings.get_settings()
settings.set("/rtx/post/backgroundZeroAlpha/enabled", True)
settings.set("/rtx/post/backgroundZeroAlpha/backgroundComposite", False)
settings.set("/rtx/post/backgroundZeroAlpha/outputAlphaInComposite", True)
settings.set("/app/captureFrame/setAlphaTo1", False)
```

- `enabled = True`：开启背景透明功能
- `backgroundComposite = False`：不自动合成背景
- `outputAlphaInComposite = True`：在输出图中保留 alpha 通道
- `setAlphaTo1 = False`：不要强制把 alpha 设为 1（否则透明就没用了）

### 第三步：Alpha 合成 —— 把透明背景换成深灰色

渲染器输出的是 RGBA 图像（4 个通道：红、绿、蓝、透明度）。我们用一个简单的公式，把透明背景替换成深灰色：

```
最终颜色 = 物体颜色 x 不透明度 + 背景颜色 x (1 - 不透明度)
```

用生活中的例子来理解：

- **不透明度 = 1**（物体所在的像素）：最终颜色 = 物体颜色 x 1 + 背景颜色 x 0 = 物体颜色。物体完整保留。
- **不透明度 = 0**（空白背景的像素）：最终颜色 = 物体颜色 x 0 + 背景颜色 x 1 = 背景颜色。显示纯灰色。
- **不透明度 = 0.5**（物体边缘的像素）：两者各占一半，产生平滑的过渡效果。

代码中的实现（`renderer.py`）：

```python
rgba = get_src(camera, "rgba")                              # 获取 RGBA 图像
alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0         # 提取 alpha 通道，归一化到 0~1
bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)    # 创建深灰色背景 RGB(40,40,40)
rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
```

这样，白色物体就能在深灰色背景上清晰可见了！

---

## 6. 如何自定义

### 6.1 更换 HDRI 文件

HDRI 文件决定了光照的「氛围」。不同的 HDRI 会产生不同的光影效果——室内暖光、户外日光、冷色调工作室……

修改 `scene.py` 中的 HDRI 路径即可：

```python
# 当前默认路径（Isaac Sim 自带的摄影棚 HDRI）
candidate = os.path.join(
    os.path.dirname(os.path.dirname(isaacsim.__file__)),
    "isaacsim", "extscache",
    "omni.kit.widget.material_preview-1.0.16",
    "data", "photo_studio_01_4k.hdr"
)

# 要换成自己的 HDRI，直接修改路径，例如：
hdri_path = "/path/to/your/custom_environment.hdr"
```

常用的免费 HDRI 资源网站：[Poly Haven](https://polyhaven.com/hdris)，下载 `.hdr` 格式文件即可。

### 6.2 调整光照强度

修改 `scene.py` 中 `CreateIntensityAttr` 的数值：

```python
dome_light.CreateIntensityAttr(1500)  # 当前值
```

| 数值 | 效果 |
|------|------|
| 500 | 较暗，类似黄昏 |
| 1000 | 适中 |
| 1500 | 明亮（当前默认值） |
| 3000 | 非常亮，可能过曝 |

建议范围：800 ~ 2000。具体效果取决于 HDRI 本身的亮度分布。

### 6.3 修改背景颜色

修改 `renderer.py` 中 `np.full_like(..., 40, ...)` 的 `40` 这个数值：

```python
bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)
#                                  ^^
#                            修改这个数字
```

| 数值 | 效果 |
|------|------|
| 0 | 纯黑背景 |
| 40 | 深灰色（当前默认值） |
| 128 | 中灰色 |
| 200 | 浅灰色 |
| 255 | 纯白背景 |

注意：如果使用纯白背景（255），白色物体又会「消失」，回到我们第 4 节描述的问题。深灰色（30~60）是最安全的选择。

---

## 7. 常见问题

### Q: 渲染出来的图片全是红色的？

**原因**：MDL 材质路径断裂。

USD 文件中的 3D 物体通常会引用 MDL 材质文件来定义表面外观（颜色、金属度、粗糙度等）。如果材质文件的路径找不到，Isaac Sim 会用一个醒目的红色来表示「材质缺失」。

**解决方法**：

检查 USD 文件中引用的 MDL 材质路径是否正确。通常需要在资产目录中创建 `Material` 符号链接，指向实际的材质文件夹。项目中的 `mdl_utils.py` 里的 `fix_mdls()` 函数可以自动修复常见的路径问题。

### Q: 渲染出来的图片全白？

**原因**：可能有两个情况。

1. **DomeLight 颜色/强度过高**：光照太强导致整个画面过曝
2. **没有开启 backgroundZeroAlpha**：背景没有变透明，HDRI 环境图直接作为背景显示，而很多 HDRI 的背景区域非常亮

**解决方法**：

- 检查 `scene.py` 中 `backgroundZeroAlpha` 相关的 4 个设置是否都已正确配置
- 降低 `IntensityAttr` 的数值（如从 1500 降到 1000）
- 确认渲染代码中使用了 RGBA（4 通道）而非 RGB（3 通道）来获取图像

### Q: 渲染出来的图片全黑？

**原因**：场景中没有有效的光源。

1. **DomeLight intensity 太低**：亮度设为 0 或极小值
2. **HDRI 文件路径错误**：文件不存在，DomeLight 没有纹理，但 intensity 也不够
3. **环境文件缺失**：`background.usd` 不存在，且 fallback 的 DomeLight 也没创建成功

**解决方法**：

- 检查控制台日志，搜索 `[Scene]` 开头的信息，确认环境加载状态
- 确认 HDRI 文件路径存在（Isaac Sim 安装路径下的 `photo_studio_01_4k.hdr`）
- 增大 `IntensityAttr` 的值

### Q: 物体形状正确但表面没有质感，看起来像塑料？

**原因**：HDRI 未加载，使用了纯色 DomeLight。

纯色光源只能提供均匀的照明，缺少真实环境中复杂的光照变化（高光方向、环境反射等）。没有 HDRI 时，光滑表面没有环境可以「反射」，所以看起来像廉价塑料。

**解决方法**：确保 HDRI 文件路径正确，检查日志中是否有 `[Scene] HDRI environment loaded` 字样。

---

## 附：整体流程图

```
  HDRI 全景图                          Alpha 合成
  (光照信息)                          (换背景)
      |                                   |
      v                                   v
+-----------+     +-----------+     +-----------+
|  DomeLight | --> | RTX 渲染器 | --> |   RGBA    | --> 最终 RGB 图片
| (发光球体) |     | PathTracing|     | (物体+透明)|     (物体+深灰背景)
+-----------+     +-----------+     +-----------+
                        |
                        v
               backgroundZeroAlpha
               (背景标记为透明)
```

简单来说：**HDRI 负责「打光」，backgroundZeroAlpha 负责「抠图」，Alpha 合成负责「换背景」。**
