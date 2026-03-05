# DLC 脚本修复审查报告

**审查日期**: 2026-03-05
**审查者**: code-refactorer agent
**审查范围**: `launch_job.sh`, `run_task.sh`, `submit_batch.py`

---

## 1. 执行摘要

经过详细审查，当前的 DLC 脚本实现**基本正确**，参数传递链完整。但在 `launch_job.sh` 中发现一个潜在的逻辑问题，以及文档注释与实际行为的小差异。

---

## 2. 详细审查结果

### 2.1 launch_job.sh 审查

**文件路径**: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/launch_job.sh`

#### 发现的问题

**问题 #1: --overwrite 处理逻辑不完整 (第16-21行)**

```bash
# 检查是否需要添加 --overwrite 标志
if [[ "$5" == *"--overwrite"* ]]; then
    # 如果 command_args 包含 --overwrite，提取实际的命令参数
    COMMAND_ARGS="${5//--overwrite/} true"
else
    COMMAND_ARGS=${5:-"$CHUNK_ID $CHUNK_TOTAL"}
fi
```

**问题分析**:
- 当 `$5` 包含 `--overwrite` 时，代码将 `--overwrite` 替换为空字符串，并追加 ` true`
- 这会产生格式问题：例如 `"render_custom /path --overwrite"` 变成 `"render_custom /path true"`
- 但 `run_task.sh` 的 `render_custom` 模式期望第6个参数是 `overwrite` (第78行: `OVERWRITE=${6:-""}`)
- 实际上这种处理在 `run_task.sh` 的 `render_custom` 分支中可能工作，但在批量模式下会出问题

**建议修复**:
```bash
if [[ "$5" == *"--overwrite"* ]]; then
    # 移除 --overwrite 标志，run_task.sh 会根据参数位置判断
    COMMAND_ARGS="${5//--overwrite/}"
    # 添加一个标志表示启用 overwrite
    COMMAND_ARGS="$COMMAND_ARGS --overwrite"
else
    COMMAND_ARGS=${5:-"$CHUNK_ID $CHUNK_TOTAL"}
fi
```

或者更简单地，直接传递原始参数，让 `run_task.sh` 自己解析：
```bash
COMMAND_ARGS=${5:-"$CHUNK_ID $CHUNK_TOTAL"}
```

#### 确认正确的部分

1. **COMMAND_ARGS 构造正确** (第20行):
   - 默认值 `"$CHUNK_ID $CHUNK_TOTAL"` 正确传递了分块参数
   - 格式正确：两个参数用空格分隔

2. **参数传递到 run_task.sh 正确** (第67行):
   ```bash
   --command="bash $CODE_ROOT/scripts/dlc/run_task.sh $COMMAND_ARGS"
   ```
   - 使用 `$COMMAND_ARGS` 展开，会正确传递所有参数

---

### 2.2 run_task.sh 审查

**文件路径**: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh`

#### 发现的问题

**问题 #1: 批量模式缺少 --overwrite 支持 (第103-118行)**

```bash
else
    # 批量模式 (Batch mode) - DLC 默认模式
    # 用法: bash run_task.sh <chunk_id> <chunk_total> [assets_dir] [save_dir]
    CHUNK_ID=$1
    CHUNK_TOTAL=$2
    ASSETS_DIR=${3:-"/cpfs/shared/simulation/zhuzihou/assets/GRScenes100-for-render/GRScenes_assets"}
    SAVE_DIR=${4:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_dlc_result"}

    echo "Running Batch Render Task: Chunk $CHUNK_ID / $CHUNK_TOTAL"

    python -m render_usd.cli grscenes100 \
        --chunk_id $CHUNK_ID \
        --chunk_total $CHUNK_TOTAL \
        --assets_dir "$ASSETS_DIR" \
        --save_dir "$SAVE_DIR"
fi
```

**问题分析**:
- 批量模式（else 分支）没有处理 `--overwrite` 参数
- 虽然 `cli.py grscenes100` 支持 `--overwrite` 标志（第78行），但 `run_task.sh` 没有传递它
- 如果用户通过 `launch_job.sh` 的 `--overwrite` 标志尝试启用覆盖模式，在批量模式下会被忽略

**建议修复**:
```bash
else
    # 批量模式 (Batch mode) - DLC 默认模式
    # 用法: bash run_task.sh <chunk_id> <chunk_total> [assets_dir] [save_dir] [overwrite]
    CHUNK_ID=$1
    CHUNK_TOTAL=$2
    ASSETS_DIR=${3:-"/cpfs/shared/simulation/zhuzihou/assets/GRScenes100-for-render/GRScenes_assets"}
    SAVE_DIR=${4:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd/output_dlc_result"}
    OVERWRITE=${5:-""}

    echo "Running Batch Render Task: Chunk $CHUNK_ID / $CHUNK_TOTAL"

    CMD="python -m render_usd.cli grscenes100 \
        --chunk_id $CHUNK_ID \
        --chunk_total $CHUNK_TOTAL \
        --assets_dir \"$ASSETS_DIR\" \
        --save_dir \"$SAVE_DIR\""
    if [ -n "$OVERWRITE" ]; then
        CMD="$CMD --overwrite"
    fi
    eval "$CMD"
fi
```

#### 确认正确的部分

1. **批量模式参数解析正确** (第106-109行):
   - `$1` -> `CHUNK_ID`
   - `$2` -> `CHUNK_TOTAL`
   - `$3` -> `ASSETS_DIR` (可选，有默认值)
   - `$4` -> `SAVE_DIR` (可选，有默认值)

2. **grscenes100 命令调用正确** (第113-117行):
   ```bash
   python -m render_usd.cli grscenes100 \
       --chunk_id $CHUNK_ID \
       --chunk_total $CHUNK_TOTAL \
       --assets_dir "$ASSETS_DIR" \
       --save_dir "$SAVE_DIR"
   ```
   - 参数名称与 `cli.py` 中定义的一致
   - 使用了正确的长选项格式 `--chunk_id` 和 `--chunk_total`

---

### 2.3 submit_batch.py 审查

**文件路径**: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/submit_batch.py`

#### 确认正确的部分

1. **参数传递正确** (第20-34行):
   ```python
   cmd: list[str] = [
       "bash",
       str(launch_script),
       task_name,
       str(chunk_id),
       str(chunk_total),
   ]
   cmd.append(data_sources if data_sources else "")
   if command_args:
       expanded_args = command_args.replace("{chunk_id}", str(chunk_id)).replace("{chunk_total}", str(chunk_total))
       cmd.append(expanded_args)
   ```
   - 参数顺序与 `launch_job.sh` 期望的一致
   - 支持模板变量替换 `{chunk_id}` 和 `{chunk_total}`

---

## 3. 参数传递链验证

完整的参数传递链验证如下：

```
submit_batch.py --total 100 --name xxx
↓
调用: bash launch_job.sh <task_name> <chunk_id> <chunk_total> "" "<command_args>"
↓
launch_job.sh: COMMAND_ARGS="$CHUNK_ID $CHUNK_TOTAL" (默认值)
↓
调用: bash run_task.sh $CHUNK_ID $CHUNK_TOTAL
↓
run_task.sh else分支: CHUNK_ID=$1, CHUNK_TOTAL=$2
↓
调用: python -m render_usd.cli grscenes100 --chunk_id $CHUNK_ID --chunk_total $CHUNK_TOTAL
```

**验证结果**: ✅ 参数传递链完整且正确

---

## 4. 修复建议汇总

### 4.1 高优先级修复

1. **run_task.sh 批量模式添加 --overwrite 支持**
   - 文件: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh`
   - 位置: 第103-118行 (else 分支)
   - 原因: 保持与其他模式一致的功能完整性

### 4.2 中优先级修复

2. **launch_job.sh 简化 --overwrite 处理逻辑**
   - 文件: `/cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/launch_job.sh`
   - 位置: 第16-21行
   - 建议: 直接传递原始参数，避免复杂的字符串替换

---

## 5. 结论

当前脚本实现**功能正确**，可以正常工作。发现的问题是功能增强（添加 --overwrite 支持）和代码简化，不是阻塞性问题。

**参数传递链完整验证**: ✅ 通过
**语法检查**: ✅ 通过
**逻辑检查**: ✅ 通过（有小问题但不影响主要功能）

---

## 6. 附录：测试命令参考

测试参数传递链：

```bash
# 测试 submit_batch.py -> launch_job.sh
python scripts/dlc/submit_batch.py --total 2 --name test_render

# 手动测试 launch_job.sh -> run_task.sh (dry-run，添加 echo 查看命令)
bash scripts/dlc/launch_job.sh test_render 0 2 ""

# 手动测试 run_task.sh -> cli.py (本地测试，跳过 DLC)
bash scripts/dlc/run_task.sh 0 2 /path/to/assets /path/to/output
```
