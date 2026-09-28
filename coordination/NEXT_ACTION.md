# NEXT_ACTION

Updated At: 2026-09-28  
Task: LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001

Current Phase:

llama-manager 排队与并发修复完成 — AWAITING COMMANDER REVIEW

Next Action:

1. Git：secret/禁用词扫描 → 白名单 add → commit（`fix: queue llama gpu waits and close model switch race`）→ push main
2. （可选）运维手册固化：Image 完成后锁随 idle 600s 卸载才释放，llama 侧 900s 等待覆盖该窗口
3. （可选）观察期：fail-safe 日志关键词 `llama status unreachable -> fail-safe`（manager 重启窗口会短暂出现）
4. （可选）恢复 vLLM（需授权）

Flags:

- VLLM_RUNNING = NO
- LLAMA_GPU_WAIT = 900s / 3s poll；切换队列 900s；Gateway 1800s；Image 900/1200（未改）
- ATOMIC_RESERVATION = 单 Condition，选择+切换判定+inflight 预留同临界区
- FAIL_SAFE = 网关对 manager 不可达回退锁+GPU进程探测
- ORPHAN = 启动检测，可判定→清理，不可判定→拒载
- 六方向 STRICT SERIAL = 全实测 PASS
- CUDA_OOM（本轮）= NO
- 禁止：未授权改模型/GGUF/Image/vLLM/CUDA、真实 IP 入 Git
