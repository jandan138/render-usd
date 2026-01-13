#!/bin/bash
# Generic launcher for DLC
# Usage: bash launch_job.sh <TASK_NAME> <CHUNK_ID> <CHUNK_TOTAL> [DATA_SOURCES]

TASK_NAME=$1
CHUNK_ID=$2
CHUNK_TOTAL=$3
DATA_SOURCES=${4:-"d-phhmdh73h3zzv7pqh0,d-r70bzlwqnstu3rg55l,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz"}

# Default constants (can be overridden by env vars)
# NOTE: WORKSPACE_ID, RESOURCE_ID, and IMAGE should be verified against your DLC environment
WORKSPACE_ID=${DLC_WORKSPACE_ID:-"270969"}
RESOURCE_ID=${DLC_RESOURCE_ID:-"quotalplclkpgjgv"}
IMAGE=${DLC_IMAGE:-"pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118"}
CODE_ROOT=${DLC_CODE_ROOT:-"/cpfs/shared/simulation/zhuzihou/dev/render-usd"}

JOB_NAME="${TASK_NAME}_${CHUNK_ID}_${CHUNK_TOTAL}"

echo "Submitting Job: $JOB_NAME"
echo "Code Root: $CODE_ROOT"

dlc submit pytorchjob --name=$JOB_NAME \
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
    --command="bash $CODE_ROOT/scripts/dlc/run_task.sh $CHUNK_ID $CHUNK_TOTAL"
