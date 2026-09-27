# NEXT_ACTION

Updated At: 2026-09-27  
Task: OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001

Current Phase:

OLLAMA QWEN3-EMBEDDING-0.6B VERIFY COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：secret/禁用词/真实IP 扫描 → 白名单 add（reports/coordination）→ commit → push main
2. （可选）运维手册固化：0.6B embedding 默认即释放，业务无需显式 keep_alive；如需驻留须显式传值
3. （可选）WebUI/Open WebUI 侧按业务选择 embedding 模型（0.6b 轻量 / 8b 强表征），互不覆盖
4. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- OLLAMA_TOPOLOGY = gateway 0.0.0.0:11434（pid=3028816）→ backend 127.0.0.1:11435（本轮未动）
- EMBED_06B = REUSED_EXISTING_MODEL（Q8_0 / ctx32768 / dim1024），未 pull、未重复权重
- EMBED_8B = PRESERVED（4.7GB 仍在列表）
- KEEP_ALIVE_DEFAULT = 0（网关注入），runner ≤1s 释放
- STRICT_EXCLUSION（Image↔Ollama 互斥）= 未改，回归 PASS
- CUDA_OOM（本轮）= NO
- 禁止：未授权改 Gateway/拓扑/Image/Zrald/gpu.lock/queue/CUDA/driver/Open WebUI、删改已有模型、真实 IP 入 Git
