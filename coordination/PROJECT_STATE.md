# PROJECT_STATE

更新时间：2026-09-28  
Task: LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | llama-manager 排队与并发修复完成（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED，本轮未动） |
| LLAMA MANAGER :8010 | RUNNING（新代码）：**GPU 等待 900s/3s 轮询** 替代 503 快速失败；单一 Condition + **原子 inflight 预留**；状态机 QUEUED→WAITING_FOR_GPU→LOADING→RUNNING→IDLE→UNLOADED |
| /status 新字段 | state / waiting_for_gpu / blocked_by（ollama·image·gpu_lock·gpu_memory·none，无 PID/IP）；原 zrald 字段全保留 |
| 等待条件 | gpu.lock 被占 / Ollama runner >1GB / nvidia 其他 >1GB；排队期不持锁，切换期租约跨切换保持 |
| Race 修复 | selection + 切换判定 + inflight++ 同一临界区；transition 标志保证同时仅一个准备者 |
| 测试 | 代码测试 **7/7 PASS**（含 deterministic race：order=[A_reserved,A_done,B_reserved,B_done]） |
| E2E | **34/34 PASS**：A=Image→llama 等待 662.7s 自动 200；B=Ollama→llama blocked=ollama→14.6s 自动 200；C=A/B 各自 model 字段正确 |
| §20 六方向 | 全 PASS（含补测 llama→Image 74.7s、Image→Ollama 61.7s、llama→Ollama 15.8s） |
| Gateway fail-safe | status 不可达 → 回退 gpu.lock 探测 + nvidia llama-server 进程，任一命中即 BUSY（消除 fail-open） |
| Orphan 保护 | 实测：人为造 orphan → 识别归属 → graceful terminate → VRAM 释放 → orphan=resolved；不可判定则拒载 |
| Zrald 兼容 | PASS（无 model/未知 model → default zrald 200；/health /manager/status 原字段未删） |
| 回归 | qwen3-14b/mistral/zrald、qwen3:8b、embed0.6b、Image 1024×1024 多轮 200；Ollama 14 模型完好 |
| 超时核对 | llama GPU wait 900（新）/ 切换队列 900 / Gateway 1800 / Image 900·1200 —— 后三者未改 |
| 终态 | 8010/8011/8020/11434/11435/3000 OPEN、8000 CLOSED、**无孤儿**、gpu.lock **FREE**、ps empty、GPU **682 MiB** |
| OOM | 本轮 0 次 |
| 本轮改动 | 仅 llama-manager（2 文件）+ gateway + reports + coordination |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
