# DLC Job Failure Analysis: Chunk 16

## Executive Summary

**Job ID:** `dlcymzh8p8f6818o`
**Task Name:** `render_grscenes_test1_fixed_16_100`
**Status:** Failed
**Failure Type:** **Platform/Infrastructure Issue (NOT Code Issue)**
**Root Cause:** Kubernetes container creation timeout - `context deadline exceeded`

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 2026-03-05T04:05:18Z | Job created |
| 2026-03-05T04:05:22Z | Job submitted, pod assigned to node `i-2zej0xgv68c8vfnjdy6f` |
| 2026-03-05T04:06:18Z | Pod sandbox created (51s elapsed) |
| 2026-03-05T04:07:27Z | Pod status: Initializing |
| 2026-03-05T04:09:22Z | Created container `pytorch` (first attempt) |
| 2026-03-05T04:11:22Z | **ERROR: context deadline exceeded** |
| 2026-03-05T04:11:24Z | Retry: Pulling image |
| 2026-03-05T04:11:52Z | Created container `pytorch` (second attempt) |
| 2026-03-05T04:13:52Z | **ERROR: context deadline exceeded** |
| 2026-03-05T04:14:03Z | Job marked as Failed |
| 2026-03-05T04:14:34Z | Pod finished |

---

## Error Analysis

### Primary Error

```
2026-03-05 12:11:22 Error: context deadline exceeded
2026-03-05 12:13:52 Error: context deadline exceeded
```

This error occurs at the **Kubernetes/DLC platform level**, not at the application level. It indicates that the container runtime (containerd/docker) failed to start the `pytorch` container within the expected time limit.

### Secondary Errors

During pod termination, multiple `KillPodSandbox` errors occurred:
```
error killing pod: failed to "KillPodSandbox" ... context deadline exceeded
```

These are **consequences** of the primary failure, not causes. The sandbox container was in `SANDBOX_READY` state but couldn't be stopped cleanly.

---

## Comparison with Successful Jobs

### Successful Job (Chunk 13 - `dlctx6dqh4kvx1vp`)

| Metric | Chunk 13 (Success) | Chunk 16 (Failed) |
|--------|-------------------|-------------------|
| Node | `i-2zebgxatz9pc6ckbmz5a` | `i-2zej0xgv68c8vfnjdy6f` |
| Sandbox Creation | 217ms | 51,171ms (236x slower) |
| Pod Init → ImagePull | ~1s | ~3 minutes |
| Container Creation | Immediate | Timeout (2+ minutes) |
| Total Startup | ~8 seconds | ~9 minutes (then failed) |

### Key Differences

1. **Node Performance:** Chunk 16's node (`i-2zej0xgv68c8vfnjdy6f`) showed severely degraded performance:
   - Pod sandbox creation took **51 seconds** vs **217ms** (236x slower)
   - Container creation consistently timed out

2. **Image Pull:** Both jobs used the same image (`pj4090/yangsizhe:isaacsim41-cuda118`), already present on the node

3. **Configuration:** Identical job specs (CPU: 16, GPU: 1, Memory: 118Gi, SharedMemory: 118Gi)

---

## Failure Classification

| Category | Assessment |
|----------|------------|
| **Code Error** | NO - Application code never started |
| **Resource Issue (OOM/GPU)** | NO - Container never reached resource allocation phase |
| **USD File Issue** | NO - No USD files were processed |
| **Environment Issue** | **YES** - Kubernetes node/container runtime problem |

### Specific Classification

**Infrastructure/Platform Issue:**
- Node `i-2zej0xgv68c8vfnjdy6f` experienced container runtime degradation
- Possible causes:
  - Containerd/docker daemon issues
  - Disk I/O bottleneck (image layers)
  - Network issues (though image was already pulled)
  - Node resource contention
  - CNI (Container Network Interface) delays

---

## Exit Code Analysis

The job's `ReasonMessage` shows:
```json
{"overview":"PyTorchJob dlcymzh8p8f6818o failed because 1 Master replica(s) failed.","content":[{"time":"1772684043","pods":{"Master":[0]},"reason":"128"}]}
```

**Exit Code 128:** This is the base value for container exit codes. The actual exit code would be `128 + N` where N is the signal number. In this case, it indicates the container was terminated by the platform (Kubernetes) rather than exiting on its own.

This is consistent with a **platform-initiated termination** due to health check failures or timeouts.

---

## Recommendation

### Immediate Action

**Retry the job.** This is a transient infrastructure failure, not a code issue. The chunk can be safely re-submitted.

```bash
# Re-submit chunk 16
python scripts/dlc/submit_batch.py \
  --total 100 \
  --name render_grscenes_test1_retry \
  --chunk_start 16 \
  --chunk_end 17
```

### Long-term Actions

1. **Monitor Node Health:** Track which nodes exhibit slow sandbox creation
2. **Add Retry Logic:** Consider implementing automatic retry for infrastructure failures
3. **Node Affinity:** If certain nodes are problematic, use anti-affinity rules

---

## Conclusion

**This failure is NOT related to the render-usd code or the recent fixes.** It is a transient Kubernetes/DLC platform issue where the assigned node (`i-2zej0xgv68c8vfnjdy6f`) failed to start containers within the required timeout.

The application code never executed - the failure occurred during container initialization, before any Python code or Isaac Sim initialization could run.

**Recommended Action:** Retry chunk 16.

---

## Appendix: Raw Pod Events

```
2026-03-05 12:05:22 Successfully assigned t1844268484432251/dlcymzh8p8f6818o-master-0 to i-2zej0xgv68c8vfnjdy6f
2026-03-05 12:05:22 UpdateService error: getting endpoints error: Endpoints "dlcymzh8p8f6818o-master-0" not found
2026-03-05 12:05:22 HandleServiceUpdateSucceed
2026-03-05 12:05:22 pod sub status changed from Scheduling to NetworkInitializing
2026-03-05 12:06:18 Successfully create pod sandbox, elapsedTime 51.171879476s
2026-03-05 12:06:18 Container image "dsw-registry-vpc.cn-beijing.cr.aliyuncs.com/pai-common/alpine:3.10" already present on machine
2026-03-05 12:06:23 Created container pod-init-indicator
2026-03-05 12:07:26 Started container pod-init-indicator
2026-03-05 12:07:27 HandleServiceUpdateSucceed
2026-03-05 12:07:27 pod sub status changed from NetworkInitializing to Initializing
2026-03-05 12:07:41 Container image "pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118" already present on machine
2026-03-05 12:07:41 pod sub status changed from Initializing to ImagePulling
2026-03-05 12:07:45 Created container warmup
2026-03-05 12:08:40 Started container warmup
2026-03-05 12:09:00 Pulling image "pj4090acr-registry-vpc.cn-beijing.cr.aliyuncs.com/pj4090/yangsizhe:isaacsim41-cuda118"
2026-03-05 12:09:00 pod sub status changed from ImagePulling to WaitingForRun
2026-03-05 12:09:00 Successfully pulled image "..." in 262ms
2026-03-05 12:09:22 Created container pytorch
2026-03-05 12:11:22 Error: context deadline exceeded
2026-03-05 12:11:24 Pulling image "..."
2026-03-05 12:11:24 Successfully pulled image "..." in 272ms
2026-03-05 12:11:52 Created container pytorch
2026-03-05 12:13:52 Error: context deadline exceeded
```

---

*Analysis completed: 2026-03-05*
*Analyzed by: dlc-operator agent*
