# DLC 提交功能测试报告

**测试日期**: 2026-03-04
**测试环境**: DLC cluster node, CPFS mounted at `/cpfs/`
**DLC CLI 版本**: `2598c3119-202512111654`

## 测试结果总览

| 测试项 | 结果 | 说明 |
|--------|------|------|
| DLC CLI 可用性 | PASS | 二进制在 repo 根目录, 版本正常 |
| DLC 认证状态 | PASS | `dlc get job` 正常返回 |
| Shell 脚本语法 | PASS | `bash -n` 全部通过 |
| Python 脚本语法 | PASS | `ast.parse` 通过 |
| Conda 环境 | PASS | `render-usd` 环境完整, import 正常 |
| GRScenes-100 资产 | PASS | 116+ 分类目录存在 |
| 单任务提交 (batch 模式) | PASS | JobId: `dlcqsvr498ibb83z`, 状态 `EnvPreparing` |
| `background.usd` 环境文件 | FAIL | `assets/environments/` 为空 |
| 输出目录预创建 | SKIP | 渲染器会自动创建 |

## 发现并修复的问题

### 1. [CRITICAL] `dlc` 不在 PATH — 已修复

**问题**: `launch_job.sh` 直接调用 `dlc`，但二进制在 repo 根目录，不在系统 PATH 中。
**文件**: `scripts/dlc/launch_job.sh:41`
**修复**: 添加 `DLC_BIN` 变量，默认指向 `$CODE_ROOT/dlc`，支持环境变量覆盖。

### 2. [HIGH] data_sources 重复 ID 导致提交失败 — 已修复

**问题**: 用户提供的 3 个数据源 ID 中 `d-mzps5b7joy2axmqpa8` 出现两次，DLC 报错 "different datasource can't have the same mount path"。
**错误码**: HTTP 400
**修复**: 去重后保留 2 个唯一 ID: `d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g`

### 3. [HIGH] `run_task.sh` 仅支持 2/4 种 CLI 模式 — 已修复

**问题**: 只支持 `single` 和默认 batch (`grscenes100`)，缺少 `render_custom` 和 `grscenes` 模式。
**文件**: `scripts/dlc/run_task.sh:49-83`
**修复**: 添加 `render_custom` 和 `grscenes` 的 `elif` 分支。

### 4. [HIGH] `launch_job.sh` command 硬编码 — 已修复

**问题**: `--command` 参数只能运行 batch 模式，无法指定其他模式。
**文件**: `scripts/dlc/launch_job.sh:54`
**修复**: 添加第 5 个参数 `COMMAND_ARGS`，默认为 `$CHUNK_ID $CHUNK_TOTAL`。

### 5. [HIGH] `submit_batch.py` 无法传递自定义模式 — 已修复

**问题**: 没有参数可以指定运行模式。
**文件**: `scripts/dlc/submit_batch.py`
**修复**: 添加 `--command_args` 参数。

## 未修复的已知问题

### 6. [MEDIUM] `background.usd` 缺失

**路径**: `assets/environments/background.usd`
**影响**: 渲染器启动时找不到环境贴图，会 fallback 到 DomeLight（可用但渲染质量可能不同）
**建议**: 获取 `background.usd` 文件并放置到 `assets/environments/` 目录

### 7. [MEDIUM] `settings.py` 默认路径无效

**文件**: `src/render_usd/config/settings.py:14-17`
**路径**: `/cpfs/user/caopeizhou/...` 系列路径不存在
**影响**: 不影响 DLC 提交（CLI 参数会覆盖），但直接调用 CLI 且不传参数时会报错

### 8. [LOW] `run_task.sh` fallback bashrc 不存在

**文件**: `scripts/dlc/run_task.sh:21`
**路径**: `/cpfs/user/caopeizhou/.bashrc`
**影响**: 无 — 本地 conda 存在时不会走到这个分支

## 修改的文件清单

| 文件 | 修改内容 |
|------|----------|
| `scripts/dlc/launch_job.sh` | 添加 `DLC_BIN` 变量; 更新 `DATA_SOURCES` 默认值; 添加 `COMMAND_ARGS` 参数 |
| `scripts/dlc/run_task.sh` | 添加 `render_custom` 和 `grscenes` 模式分支 |
| `scripts/dlc/submit_batch.py` | 添加 `--command_args` 参数 |

## 用法参考（修改后）

```bash
# 批量渲染 GRScenes-100 (默认模式, 不变)
python scripts/dlc/submit_batch.py --total 30 --name render_grscenes100

# 自定义数据源
python scripts/dlc/submit_batch.py --total 10 --name my_task --data_sources "d-xxx,d-yyy"

# 使用 render_custom 模式提交
python scripts/dlc/submit_batch.py --total 1 --name render_custom_job \
    --command_args "render_custom /cpfs/path/to/assets"

# 直接调用 launch_job.sh (单任务)
bash scripts/dlc/launch_job.sh my_task 0 1

# 查看任务状态
./dlc get job <job_id>

# run_task.sh 支持的所有模式
bash scripts/dlc/run_task.sh <chunk_id> <chunk_total>                    # batch (默认)
bash scripts/dlc/run_task.sh single <usd_path> [output_dir]             # 单文件
bash scripts/dlc/run_task.sh render_custom <assets_dir> [naming_style]   # 自定义目录
bash scripts/dlc/run_task.sh grscenes <part> <usd> [scene]              # GRScenes
```

## 环境依赖清单

| 依赖项 | 路径 | 必须 |
|--------|------|------|
| DLC CLI 二进制 | `$CODE_ROOT/dlc` | 是 |
| Conda 环境 | `$CODE_ROOT/miniconda/` | 是 |
| render-usd 包 | `$CODE_ROOT/pyproject.toml` | 是 (自动安装) |
| GRScenes-100 资产 | `/cpfs/shared/simulation/zhuzihou/assets/GRScenes100-for-render/GRScenes_assets` | 是 (batch 模式) |
| background.usd | `$CODE_ROOT/assets/environments/background.usd` | 否 (fallback DomeLight) |
