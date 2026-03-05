#!/bin/bash
# DLC 通用启动脚本 (Generic launcher for DLC)
# 用法 (Usage): bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES] [COMMAND_ARGS]

# 获取脚本参数
TASK_NAME=$1   # 参数1: 任务名称 (例如 render_grscenes100)
CHUNK_ID=$2    # 参数2: 当前分块 ID (例如 0)
CHUNK_TOTAL=$3 # 参数3: 总分块数 (例如 30)
# 参数4: 数据源 ID 列表 (可选)
# 如果没有提供第4个参数，则使用默认的 ID 列表
DATA_SOURCES=${4:-"d-mzps5b7joy2axmqpa8,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz"}
# 参数5: 自定义 run_task.sh 参数 (可选)
# 默认为 grscenes100 batch 模式 (chunk_id chunk_total)，也可传入其他模式参数
# 例如: "render_custom /path/to/assets" 或 "single /path/to/file.usd /output"
# 检查是否需要添加 --overwrite 标志
if [[ "$5" == *"--overwrite"* ]]; then
    # 如果 command_args 包含 --overwrite，提取实际的命令参数
    COMMAND_ARGS="${5//--overwrite/} true"
else
    # 默认使用 grscenes100 模式（通过传递 chunk_id 和 chunk_total 触发 run_task.sh 的 batch 分支）
    COMMAND_ARGS=${5:-"$CHUNK_ID $CHUNK_TOTAL"}
fi

# 默认常量配置 (可以通过环境变量覆盖)
# 注意: WORKSPACE_ID, RESOURCE_ID 和 IMAGE 必须与您的 DLC 环境匹配

# DLC 工作空间 ID，默认为 270969 (SmartBot Workspace)
WORKSPACE_ID=${DLC_WORKSPACE_ID:-"270969"}

# DLC 资源配额 ID，默认为 quotalplclkpgjgv
RESOURCE_ID=${DLC_RESOURCE_ID:-"quotalplclkpgjgv"}

# Docker 镜像地址
# 默认为 Isaac Sim 4.1.0 (CUDA 11.8) 镜像
# 如果需要使用 4.5.0，请修改此处或设置 DLC_IMAGE 环境变量
IMAGE=${DLC_IMAGE:-"pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118"}

# 代码在容器内的挂载根目录
# 默认为 /cpfs/shared/simulation/zhuzihou/dev/render-usd
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

# 构造唯一的作业名称 (Job Name)
# 格式: 任务名_当前分块_总分块 (例如 render_grscenes100_0_30)
JOB_NAME="${TASK_NAME}_${CHUNK_ID}_${CHUNK_TOTAL}"

# 打印日志信息
echo "Submitting Job: $JOB_NAME" # 打印作业名称
echo "Code Root: $CODE_ROOT"     # 打印代码根目录

# DLC CLI 工具路径 (默认使用项目根目录下的 dlc 二进制)
DLC_BIN=${DLC_BIN:-"$CODE_ROOT/dlc"}

# 调用 dlc submit 命令提交 pytorchjob 任务
# 这是阿里云 PAI-DLC 的命令行工具
"$DLC_BIN" submit pytorchjob --name=$JOB_NAME \
    --workers=1 \
    --job_max_running_time_minutes=0 \
    --worker_gpu=1 \
    --worker_cpu=16 \
    --worker_memory=118Gi \
    --worker_shared_memory=118Gi \
    --worker_image=$IMAGE \
    --workspace_id=$WORKSPACE_ID \
    --resource_id=$RESOURCE_ID \
    --data_sources=$DATA_SOURCES \
    --oversold_type ForbiddenQuotaOverSold \
    --priority 7 \
    --command="bash $CODE_ROOT/scripts/dlc/run_task.sh $COMMAND_ARGS"
# --command 参数指定了容器启动后要执行的具体命令
# 默认调用 run_task.sh 的 batch 模式，也可通过 COMMAND_ARGS 传入其他模式
