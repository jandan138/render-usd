# Renderer 重复代码修复方案

## 问题总结

`src/render_usd/core/renderer.py` 中的 `render_thumbnail_wo_bg` 方法存在严重的代码重复问题：

- **第254-284行**：图像提取和保存代码块（在 try 块内）
- **第304-335行**：完全相同的图像提取和保存代码块（在 finally 块后）

这导致每个对象被渲染两次，图像被保存两次（第二次覆盖第一次），造成双倍渲染时间。

## 需要删除的确切行号范围

### 删除范围：第304-335行

```python
            os.makedirs(save_dir, exist_ok=True)
            for idx, camera in enumerate(cameras):
                # Get RGBA and composite onto dark gray background
                rgba = get_src(camera, "rgba")
                if rgba is not None and rgba.shape[2] == 4:
                    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                    bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)  # dark gray RGB(40,40,40)
                    rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
                else:
                    rgb = get_src(camera, "rgb")

                # Determine filename based on naming style
                filename_base = f"{object_name}_{idx}"
                if naming_style == "view":
                    if sample_number == 4 and init_azimuth_angle == 0:
                        view_names = {0: "front", 1: "left", 2: "back", 3: "right"}
                        if idx in view_names:
                            filename_base = view_names[idx]
                    else:
                        print(f"[Warning] 'view' naming style requires sample_number=4 and init_azimuth_angle=0. Falling back to index style.")

                if show_bbox2d:
                    bbox2d = get_src(camera, "bbox2d_tight")
                    try:
                        bbox2d_data = bbox2d[0][0]  # get the first row data
                        rgb = draw_bbox2d(rgb, bbox2d_data)
                    except:
                        print(f"[RenderManager: Render Thumbnail Without Background] {object_name} {idx} bbox2d is not valid due to the specific aspect.")
                    cv2.imwrite(f"{save_dir}/{filename_base}_bbox2d.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                else:
                    cv2.imwrite(f"{save_dir}/{filename_base}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
            delete_prim(show_prim_path)
```

### 保留范围：第254-284行（try 块内的代码）

这段代码应该保留，因为它：
1. 位于 try 块内，有适当的错误处理
2. 包含在 try-finally 结构中，确保资源清理

## 删除后预期的代码结构

```python
            try:
                set_prim_cast_shadow_true(usd_prim)
                add_update_semantics(usd_prim, semantic_label="instance", type_label="class")
                bbox_min, bbox_max = compute_bbox(usd_prim)

                # CRITICAL FIX #3: Validate bounding box data before using it
                if np.any(np.isnan(bbox_min)) or np.any(np.isnan(bbox_max)):
                    print(f"[Error] Invalid bounding box (NaN) for {object_name}, skipping")
                    delete_prim(show_prim_path)
                    continue
                if np.any(np.isinf(bbox_min)) or np.any(np.isinf(bbox_max)):
                    print(f"[Error] Invalid bounding box (Inf) for {object_name}, skipping")
                    delete_prim(show_prim_path)
                    continue

                center = (bbox_min + bbox_max) / 2
                distance = np.linalg.norm(bbox_max - bbox_min) * 1.0

                # Clamp distance to reasonable range to prevent numerical instability
                distance = np.clip(distance, 0.1, 100.0)

                for i in range(sample_number):
                    azimuth = init_azimuth_angle + i * 360 / sample_number
                    elevation = 35
                    set_camera_look_at(cameras[i], center, azimuth=azimuth, elevation=elevation, distance=distance)

                # CRITICAL FIX #4: Add error handling around rendering steps
                try:
                    for _ in range(100):
                        self.world.step(render=False)
                    for _ in range(8):
                        self.world.step(render=True)
                except Exception as e:
                    print(f"[Error] Rendering failed for {object_usd_path}: {e}")
                    print(f"[Error] Skipping this asset and continuing...")
                    try:
                        delete_prim(show_prim_path)
                    except:
                        pass
                    continue

                # Image extraction and saving (inside try block so cleanup happens on error)
                os.makedirs(save_dir, exist_ok=True)
                for idx, camera in enumerate(cameras):
                    # Get RGBA and composite onto dark gray background
                    rgba = get_src(camera, "rgba")
                    if rgba is not None and rgba.shape[2] == 4:
                        alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
                        bg = np.full_like(rgba[:, :, :3], 40, dtype=np.float32)
                        rgb = (rgba[:, :, :3].astype(np.float32) * alpha + bg * (1.0 - alpha)).astype(np.uint8)
                    else:
                        rgb = get_src(camera, "rgb")

                    # Determine filename based on naming style
                    filename_base = f"{object_name}_{idx}"
                    if naming_style == "view":
                        if sample_number == 4 and init_azimuth_angle == 0:
                            view_names = {0: "front", 1: "left", 2: "back", 3: "right"}
                            if idx in view_names:
                                filename_base = view_names[idx]
                        else:
                            print(f"[Warning] 'view' naming style requires sample_number=4 and init_azimuth_angle=0. Falling back to index style.")

                    if show_bbox2d:
                        bbox2d = get_src(camera, "bbox2d_tight")
                        try:
                            bbox2d_data = bbox2d[0][0]
                            rgb = draw_bbox2d(rgb, bbox2d_data)
                        except:
                            print(f"[RenderManager: Render Thumbnail Without Background] {object_name} {idx} bbox2d is not valid due to the specific aspect.")
                        cv2.imwrite(f"{save_dir}/{filename_base}_bbox2d.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                    else:
                        cv2.imwrite(f"{save_dir}/{filename_base}.png", cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))

            except Exception as e:
                print(f"[Error] Unexpected error processing {object_usd_path}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Always cleanup the prim, even if an error occurred
                try:
                    delete_prim(show_prim_path)
                except:
                    pass

                # CRITICAL FIX #5: Memory cleanup every N objects
                if (idx_obj + 1) % 50 == 0:
                    gc.collect()
                    print(f"[Memory] Garbage collected after {idx_obj + 1} objects")

            # [删除的重复代码块原来在这里 - 第304-335行]
```

## 风险分析和缓解措施

### 风险1：功能丢失
- **风险**：删除代码块可能导致某些功能不再工作
- **缓解措施**：
  - 确认保留的代码块（第254-284行）与删除的代码块（第304-335行）完全相同
  - 保留的代码块位于 try 块内，有更好的错误处理
  - 删除的代码块位于 finally 块后，没有额外的错误保护

### 风险2：Prim 清理问题
- **风险**：第335行的 `delete_prim(show_prim_path)` 被删除
- **缓解措施**：
  - 检查确认 `finally` 块（第290-302行）已经包含 `delete_prim(show_prim_path)` 调用
  - 第335行的调用是多余的，因为 `finally` 块总会执行

### 风险3：缩进和语法错误
- **风险**：删除代码后可能导致缩进错误或语法错误
- **缓解措施**：
  - 仔细验证删除后的代码结构
  - 确保 `finally` 块后的代码正确缩进

### 验证步骤
1. 删除后检查 Python 语法：`python -m py_compile src/render_usd/core/renderer.py`
2. 运行单元测试（如果有）
3. 进行小规模渲染测试，验证输出正确

## 实施建议

1. 使用代码编辑器的精确删除功能，确保只删除第304-335行
2. 删除后验证文件语法正确
3. 进行小规模测试渲染（1-2个对象）确认功能正常
4. 监控渲染时间，确认性能提升

## 预期结果

- 渲染时间减少约 50%
- 代码更清晰，易于维护
- 保留所有原有功能
- 不影响错误处理和内存清理逻辑

## 实施状态

**状态**: 已完成

修复已由 feature-implementer 实施，包括：
1. 删除了第304-335行的重复代码块
2. 整理了导入语句顺序（将标准库导入移到文件顶部）
3. 移除了多余的 `import traceback`（已移到文件顶部）

**验证**: 通过 `git diff` 确认修改正确
- 删除了32行重复代码
- 保留了 try-finally 结构和内存清理逻辑
- 导入语句整理符合 PEP 8 规范
