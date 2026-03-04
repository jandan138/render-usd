# 改动记录

**日期**: 2026-03-04
**对应 Commit**: `3a1708a` Feat: Update DLC scripts with render_custom/grscenes modes and add dlc-operator agent

---

## DLC 脚本修复

- **`launch_job.sh`**:
  - 新增 `DLC_BIN` 变量，默认指向 `$CODE_ROOT/dlc`，解决 `dlc` 二进制不在系统 PATH 中导致提交失败的问题，同时支持通过环境变量覆盖
  - 更新 `DATA_SOURCES` 默认值为 3 个数据源 ID（`d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz`）
  - 新增第 5 个参数 `COMMAND_ARGS`，支持自定义 `run_task.sh` 运行模式，默认为 batch 模式（`$CHUNK_ID $CHUNK_TOTAL`）

- **`run_task.sh`**:
  - 新增 `render_custom` 模式：`run_task.sh render_custom <assets_dir> [naming_style]`，用于渲染 `Category/UID/usd/UID.usd` 结构的自定义资产目录
  - 新增 `grscenes` 模式：`run_task.sh grscenes <part> <usd> [scene]`，用于 GRScenes 场景级渲染

- **`submit_batch.py`**:
  - 新增 `--command_args` 参数，可将自定义运行模式参数传递给 `launch_job.sh`（例如 `--command_args "render_custom /path/to/assets"`）

## HDRI 环境光照

- **`scene.py`**:
  - 当 `background.usd` 缺失时，自动查找 Isaac Sim 自带的 `photo_studio_01_4k.hdr` HDRI 贴图创建 DomeLight（强度 1500）
  - 启用 RTX `backgroundZeroAlpha` 系列设置，实现"HDRI 照亮物体但背景透明"的效果

- **`camera.py`**:
  - 新增 `get_rgba()` 函数，返回完整的 4 通道 RGBA 数据（含 Alpha 通道）
  - `get_src()` 新增 `"rgba"` 类型支持

- **`renderer.py`**:
  - `render_thumbnail_wo_bg` 方法改为获取 RGBA 数据，利用 Alpha 通道将物体合成到深灰背景 RGB(40,40,40) 上，解决此前纯白/纯灰背景对比度不足的问题

## 新增 Agent

- **`dlc-operator`**: DLC 任务配置和提交专用 Agent，负责 DLC Job 的参数配置、脚本调试和任务提交操作

## 环境修复

- **Material 符号链接**: 创建 `/cpfs/shared/simulation/zhuzihou/dev/Material` → `usd-scene-physics-prep/GRScenes-test1/Material` 的符号链接，解决 USD 文件中材质引用路径断裂导致物体渲染为纯红色的问题

## 测试记录

本次所有 DLC 测试 Job 及结果：

| Job 名称 | 结果 | 说明 |
|-----------|------|------|
| test_dlc_validate | 成功 | DLC CLI 可用性、认证状态、脚本语法验证通过 |
| test_single_render | 成功 | 单文件渲染正常，但物体为红色（材质引用缺失） |
| test_single_material | 成功 | 修复 Material 符号链接后，材质正常加载，白色背景 |
| test_gray_bg | 成功 | 切换为浅灰背景，但物体与背景对比度不够 |
| test_dark_bg | 成功 | 深灰背景，物体也随之变暗 |
| test_hdri_v2_plate | 成功 | HDRI + Alpha 合成方案，光照充足且背景纯净，效果良好 |
| test_hdri_v2_bed | 成功 | HDRI + Alpha 合成方案，光照充足且背景纯净，效果良好 |
