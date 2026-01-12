#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: chunk_id chunk_total"
    exit 1
fi

chunk_id=$1
chunk_total=$2
task_name="render_grscenes100_${chunk_id}/${chunk_total}"


script_name=render_grscenes100.sh
worker_gpu=1
worker_cpu=16
worker_memory=118Gi
worker_shared_memory=118Gi
max_running_min=0

echo "Using script: $script_name"
echo "Task name: $task_name"



echo "Using smartbot workspace"
workspace_id=270969
resource_id=quotalplclkpgjgv
data_sources="d-phhmdh73h3zzv7pqh0,d-r70bzlwqnstu3rg55l,d-d49o5g0h2818sw8j1g,d-8wz4emfs21s5ajs9oz"


    # --worker_image=pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:1.0 \
dlc submit pytorchjob --name=$task_name \
    --workers=1 \
    --job_max_running_time_minutes=$max_running_min \
    --worker_gpu $worker_gpu \
    --worker_cpu $worker_cpu \
    --worker_memory $worker_memory \
    --worker_shared_memory $worker_shared_memory \
    --worker_image=pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118 \
    --workspace_id=$workspace_id \
    --resource_id $resource_id \
    --data_sources=$data_sources \
    --oversold_type ForbiddenQuotaOverSold \
    --priority 7 \
    --command="cd /cpfs/user/caopeizhou/projects/GRGenerator/object_extraction_and_caption/_submit_scripts; bash $script_name $chunk_id $chunk_total"