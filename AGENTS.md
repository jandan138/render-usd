# AGENTS.md

本文件是本仓库面向 Codex/通用代码 Agent 的项目级工作约束，内容尽量与 `CLAUDE.md` 和 `.claude/` 现有配置保持一致。

## 1. 项目概览

`render-usd` 是一个基于 NVIDIA Isaac Sim（PathTracing）的 USD 渲染流水线，用于从 USD 资产生成多视角缩略图。

- 入口：`src/render_usd/cli.py`
- 核心模块：`src/render_usd/core/renderer.py`、`scene.py`、`camera.py`
- 典型输出：每个物体 4 张 PNG（front/left/back/right 或 index 风格）

## 2. 环境准备（执行命令前必须完成）

```bash
# 1) 激活项目 conda 环境
source miniconda/bin/activate render-usd

# 2) 设置 PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# 3) 接受 Isaac Sim EULA（必需）
export OMNI_KIT_ACCEPT_EULA=YES

# 4) （可选）MDL 搜索路径
export MDL_SYSTEM_PATH="/path/to/Material/mdl:/path/to/Materials"
```

说明：DLC 任务建议通过 `scripts/dlc/run_task.sh` 启动，该脚本会处理上述环境步骤。

## 3. 常用命令

```bash
# 可编辑安装
pip install -e .

# 单资产渲染
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output

# 语义命名输出（front/left/back/right）
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output --naming_style view

# 自定义目录结构批量渲染
python -m render_usd.cli render_custom --assets_dir /path/to/assets --naming_style view

# GRScenes-100 分片渲染
python -m render_usd.cli grscenes100 --chunk_id 0 --chunk_total 10 --assets_dir /path/to/assets --save_dir ./output

# DLC 批量提交
python scripts/dlc/submit_batch.py --total 10 --name render_grscenes100
```

## 4. 架构与硬约束

1. `SimulationApp` 必须在任何 `omni`/`isaacsim`/`pxr` 导入前初始化。
2. 不要把 Isaac Sim 相关 lazy import 移到模块顶层。
3. 渲染主流程：CLI 解析参数 -> `RenderManager` 初始化 -> 加载 USD -> 计算 bbox -> 相机采样 -> 保存 PNG。
4. 关键默认配置在 `src/render_usd/config/settings.py`（环境贴图、MDL 路径、数据路径等）。

## 5. 文件归属与改动边界（对齐 `.claude/file-ownership.md`）

高冲突文件：

- `src/render_usd/cli.py`
- `src/render_usd/config/settings.py`
- `src/render_usd/core/renderer.py`

推荐规则：

1. 同一轮任务中，尽量避免并行修改同一高冲突文件。
2. 文档统一放在 `docs/`，保持可追溯的技术说明。
3. 未明确需要时，不修改 `.claude/agents/`、`.claude/file-ownership.md`、`.claude/settings.local.json`。

## 6. 任务执行规范

1. 先读上下文：`CLAUDE.md`、相关 `docs/`、目标代码文件。
2. 小步改动：优先最小正确修改，避免无关重构。
3. 变更说明要包含：问题、根因、改动点、验证方式、影响范围。
4. 与渲染/集群相关的任务需要记录执行命令与结果（成功/失败、关键日志）。

## 7. 文档落地要求（沿用 Claude 团队规则）

无论是探索、实现、测试还是运维任务，都应在 `docs/` 下留下可复盘记录（推荐放到 `docs/design/`、`docs/dlc/` 或 `docs/tmp/`）：

- Problem：要解决什么问题
- Investigation：如何定位/调研
- Solution：采用了什么方案及原因
- Results：验证结果与后续风险

## 8. 参考资料

- 总体说明：`CLAUDE.md`
- Agent 团队分工：`.claude/agents/*.md`
- 文件归属：`.claude/file-ownership.md`
- 团队搭建手册：`docs/agent-team-playbook.md`
