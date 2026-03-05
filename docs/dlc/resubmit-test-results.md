# DLC 任务重新提交操作记录

**操作时间**: 2026-03-05
**操作人**: dlc-operator agent
**任务**: 重新提交修复后的 DLC 渲染任务

---

## 1. 停止旧任务

### 1.1 识别需要停止的任务

从 DLC 集群查询到以下旧任务仍在运行（使用错误的 `render_custom` 模式）：

| Chunk | Job ID | 状态 |
|-------|--------|------|
| 13 | dlctx6dqh4kvx1vp | Running |
| 14 | dlcxt0p3dqh57d0l | Running |
| 15 | dlcyczvuxzzzuwql | Running |
| 17 | dlcz6yo095r6946j | Running |

Chunk 16 (dlcymzh8p8f6818o) 已经失败（平台问题）。

### 1.2 执行停止操作

```bash
./dlc stop job dlctx6dqh4kvx1vp -e pai-dlc.cn-beijing.aliyuncs.com -f
./dlc stop job dlcxt0p3dqh57d0l -e pai-dlc.cn-beijing.aliyuncs.com -f
./dlc stop job dlcyczvuxzzzuwql -e pai-dlc.cn-beijing.aliyuncs.com -f
./dlc stop job dlcz6yo095r6946j -e pai-dlc.cn-beijing.aliyuncs.com -f
```

**结果**: 所有4个任务已成功停止

```
[OK] Job [dlctx6dqh4kvx1vp] was stopped successfully
[OK] Job [dlcxt0p3dqh57d0l] was stopped successfully
[OK] Job [dlcyczvuxzzzuwql] was stopped successfully
[OK] Job [dlcz6yo095r6946j] was stopped successfully
```

---

## 2. 提交新任务

### 2.1 提交命令

```bash
python scripts/dlc/submit_batch.py --total 100 --name render_grscenes_fixed_v2
```

### 2.2 提交结果

成功提交了 100 个 chunk 任务：
- 任务名称格式: `render_grscenes_fixed_v2_{chunk_id}_100`
- Chunk 范围: 0-99
- 每个 chunk 对应的 Job ID 已记录在 DLC 系统中

**关键配置确认**:
```json
{
  "UserCommand": "bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh {chunk_id} 100",
  "DataSources": [
    "d-mzps5b7joy2axmqpa8",
    "d-d49o5g0h2818sw8j1g",
    "d-8wz4emfs21s5ajs9oz"
  ],
  "Image": "pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118",
  "ResourceConfig": {
    "CPU": "16",
    "GPU": "1",
    "Memory": "118Gi",
    "SharedMemory": "118Gi"
  }
}
```

---

## 3. 任务状态监控

### 3.1 初始状态检查

提交后立即检查任务状态：

```bash
./dlc get job -e pai-dlc.cn-beijing.aliyuncs.com --workspace_id 270969 \
  --display_name_regex "render_grscenes_fixed_v2" --page_size 20
```

**观察到的状态分布**:
- Succeeded: 1 个 (chunk 0)
- Running: 多个
- EnvPreparing: 多个
- Queuing: 多个
- Creating: 1 个

### 3.2 第一个任务验证

**Chunk 0** (dlccq6sjtd7ru01p) 已成功完成：

```
[CLI] GRScenes-100 Chunk 0/100: 857 assets (0-857).
Rendering objects: 100%|██████████| 857/857 [00:02<00:00, 407.65it/s]
[CLI] Rendering complete, starting shutdown cleanup...
[RenderManager] Cleanup completed
[CLI] Garbage collection completed
```

**验证要点**:
1. ✅ 使用了正确的 `grscenes100` 模式
2. ✅ 正确识别了 857 个待渲染资源
3. ✅ 成功完成所有资源渲染
4. ✅ 正常执行了 shutdown cleanup

### 3.3 运行中任务验证

**Chunk 90** (dlc16ezci19kq047) 正在运行：

```
Status: Running
UserCommand: bash /cpfs/shared/simulation/zhuzihou/dev/render-usd/scripts/dlc/run_task.sh 90 100
```

日志显示 Isaac Sim 正常启动中。

---

## 4. 修复内容确认

### 4.1 代码版本

使用的代码版本包含以下关键提交：
- `a31f3ee` Fix DLC crash with shutdown cleanup and chunking support

### 4.2 关键修复

1. **run_task.sh**: 默认 batch 模式现在调用 `grscenes100` CLI 命令，支持分片渲染
2. **renderer.py**: 添加了 `shutdown_cleanup()` 方法，在渲染完成后正确关闭 Isaac Sim
3. **cli.py**: 添加了 `grscenes100` 命令，支持 `--chunk_id` 和 `--chunk_total` 参数

---

## 5. 后续监控建议

1. **定期检查任务状态**:
   ```bash
   ./dlc get job -e pai-dlc.cn-beijing.aliyuncs.com --workspace_id 270969 \
     --display_name_regex "render_grscenes_fixed_v2" --page_size 100
   ```

2. **查看失败任务日志**:
   ```bash
   ./dlc logs <job_id> <pod_id> -e pai-dlc.cn-beijing.aliyuncs.com -n 500
   ```

3. **统计完成进度**:
   - 总任务数: 100
   - 监控 Succeeded/Failed/Running 状态分布

---

## 6. 总结

| 项目 | 结果 |
|------|------|
| 旧任务停止 | ✅ 4 个任务已停止 |
| 新任务提交 | ✅ 100 个 chunk 已提交 |
| 模式验证 | ✅ grscenes100 模式确认 |
| 首个任务 | ✅ Chunk 0 成功完成 |
| 运行状态 | ✅ 多个任务正在运行 |

**结论**: DLC 任务重新提交成功，修复后的脚本工作正常。
