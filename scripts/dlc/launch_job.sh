#!/bin/bash
set -euo pipefail
# DLC 通用启动脚本 (Generic launcher for DLC)
# 用法 (Usage): bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES] [COMMAND_ARGS]

if [ $# -lt 3 ]; then
    echo "Usage: bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES] [COMMAND_ARGS]"
    exit 1
fi

# 获取脚本参数
TASK_NAME=$1   # 参数1: 任务名称 (例如 render_grscenes100)
CHUNK_ID=$2    # 参数2: 当前分块 ID (例如 0)
CHUNK_TOTAL=$3 # 参数3: 总分块数 (例如 30)

# 整数验证
for var in CHUNK_ID CHUNK_TOTAL; do
    val="${!var}"
    case "$val" in
        ''|*[!0-9]*)
            echo "ERROR: $var must be a non-negative integer, got: '$val'" >&2
            exit 1
            ;;
    esac
done

# 参数4: 数据源 ID 列表 (可选)
# 更新为4个默认值，包含访问 /cpfs/user/zhuzihou 所需的数据源
DATA_SOURCES=${4:-"d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz,d-f1dsz5nbamclxgydo8"}

# 参数5: 自定义 run_task.sh 参数 (可选)
if [ $# -ge 5 ]; then
    COMMAND_ARGS="$5"
    # 精确处理 --overwrite（基于词的分割，避免部分匹配）
    if [[ " $COMMAND_ARGS " == *" --overwrite "* ]]; then
        COMMAND_ARGS=$(echo "$COMMAND_ARGS" | awk '{
            for(i=1;i<=NF;i++) if($i != "--overwrite") printf "%s%s", sep, $i; sep=" "
        } END{print ""}')
        COMMAND_ARGS="$COMMAND_ARGS true"
    fi
else
    COMMAND_ARGS="$CHUNK_ID $CHUNK_TOTAL"
fi

# 默认常量配置 (可以通过环境变量覆盖)
# 注意: WORKSPACE_ID, RESOURCE_ID 和 IMAGE 必须与您的 DLC 环境匹配

# DLC 工作空间 ID，默认为 270969 (SmartBot Workspace)
WORKSPACE_ID=${DLC_WORKSPACE_ID:-"270969"}

# Docker 镜像地址
# 默认为 Isaac Sim 4.1.0 (CUDA 11.8) 镜像
# 如果需要使用 4.5.0，请修改此处或设置 DLC_IMAGE 环境变量
IMAGE=${DLC_IMAGE:-"pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118"}

# 代码在容器内的挂载根目录
# 默认为 /cpfs/shared/simulation/zhuzihou/dev/render-usd
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

# 资源配置（保持当前 render-usd 配置）
WORKER_GPU=1
WORKER_CPU=16
WORKER_MEMORY=118Gi
WORKER_SHARED_MEMORY=118Gi
RESOURCE_ID=${DLC_RESOURCE_ID:-"quotalplclkpgjgv"}

# 作业超时设置（默认8小时=480分钟，0表示无限制）
JOB_TIMEOUT=${DLC_JOB_TIMEOUT:-480}

# 构造唯一的作业名称 (Job Name)
# 格式: 任务名_当前分块_总分块 (例如 render_grscenes100_0_30)
JOB_NAME="${TASK_NAME}_${CHUNK_ID}_${CHUNK_TOTAL}"

# 打印日志信息
echo "Submitting Job: $JOB_NAME"
echo "Code Root: $CODE_ROOT"

# DLC CLI 工具路径 (默认使用项目根目录下的 dlc 二进制)
DLC_BIN=${DLC_BIN:-"$CODE_ROOT/dlc"}
if [ ! -x "$DLC_BIN" ]; then
    echo "ERROR: DLC binary not found or not executable at $DLC_BIN"
    exit 1
fi

# 打印解析后的资源配置（方便排查）
echo "Resolved config -> GPU=$WORKER_GPU CPU=$WORKER_CPU Memory=$WORKER_MEMORY SharedMem=$WORKER_SHARED_MEMORY Resource=$RESOURCE_ID Timeout=${JOB_TIMEOUT}m"

# 调用 dlc submit 命令提交 pytorchjob 任务
# 这是阿里云 PAI-DLC 的命令行工具
"$DLC_BIN" submit pytorchjob --name=$JOB_NAME \
    --workers=1 \
    --job_max_running_time_minutes=$JOB_TIMEOUT \
    --worker_gpu=$WORKER_GPU \
    --worker_cpu=$WORKER_CPU \
    --worker_memory=$WORKER_MEMORY \
    --worker_shared_memory=$WORKER_SHARED_MEMORY \
    --worker_image=$IMAGE \
    --workspace_id=$WORKSPACE_ID \
    --resource_id=$RESOURCE_ID \
    --data_sources=$DATA_SOURCES \
    --oversold_type=ForbiddenQuotaOverSold \
    --priority 7 \
    --command="bash $CODE_ROOT/scripts/dlc/run_task.sh ${COMMAND_ARGS}"
# --command 参数指定了容器启动后要执行的具体命令
# 默认调用 run_task.sh 的 batch 模式，也可通过 COMMAND_ARGS 传入其他模式
