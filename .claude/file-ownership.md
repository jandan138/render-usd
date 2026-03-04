# 文件归属表（File Ownership Map）

> 同一文件在一次 Agent Teams 会话中只能由一个 agent 修改。
> 若多个 agent 需触及同一文件，应串行而非并行。

## 代码模块归属

| 路径 | 负责 Agent | 说明 |
|---|---|---|
| `src/render_usd/core/renderer.py` | feature-implementer, bug-fixer | 核心渲染逻辑；高冲突风险 |
| `src/render_usd/core/scene.py` | feature-implementer | 场景/灯光管理 |
| `src/render_usd/core/camera.py` | feature-implementer, bug-fixer | 摄像机控制和数据提取 |
| `src/render_usd/cli.py` | feature-implementer | **高冲突风险**：所有子命令在此注册 |
| `src/render_usd/config/settings.py` | feature-implementer | **高冲突风险**：全局配置 |
| `src/render_usd/utils/usd_utils/` | feature-implementer, code-refactorer | USD 工具函数 |
| `src/render_usd/utils/common_utils/` | feature-implementer, code-refactorer, bug-fixer | 通用工具函数 |
| `src/render_usd/utils/caption_utils/` | feature-implementer | GPT/Qwen 描述生成 |
| `scripts/dlc/` | feature-implementer | DLC 集群脚本 |

## 文档归属

| 路径 | 负责 Agent | 说明 |
|---|---|---|
| `docs/` | docs-writer | 所有文档；其他 agent 只读 |
| `README.md` | docs-writer | 项目根 README |

## 验证归属（只读）

| 路径 | 负责 Agent | 说明 |
|---|---|---|
| `test_outputs/` | render-validator | 只读验证渲染输出，不修改任何文件 |

## 基础设施（仅 team lead 或手动操作）

| 路径 | 负责 Agent | 说明 |
|---|---|---|
| `CLAUDE.md` | team lead / 手动 | 需人工审核，不由 agent 自动修改 |
| `.claude/agents/` | team lead / 手动 | Agent 定义文件 |
| `.claude/file-ownership.md` | team lead / 手动 | 本文件 |
| `.claude/settings.local.json` | team lead / 手动 | 项目配置 |

## 高冲突风险文件

| 文件 | 风险原因 | 推荐处理方式 |
|---|---|---|
| `src/render_usd/cli.py` | 所有新子命令均在此注册 | 多功能时串行，或 team lead 统一处理 |
| `src/render_usd/config/settings.py` | 全局配置，各模块都引用 | 同一 team 只允许一个 agent 修改 |
| `src/render_usd/core/renderer.py` | 核心渲染逻辑，feature 和 bugfix 都可能触及 | 同一 team 中串行处理 |

## 规则摘要

1. 各 agent 改动不重叠的路径 → 可并行
2. 两个 agent 都需要改同一文件 → 必须串行
3. version-commit-agent 先合并改动范围最小、最独立的分支
4. Agent 改动超出本表所列范围 → version-commit-agent 须在合并前报告 team lead
