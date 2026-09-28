# NEXT_ACTION

Updated At: 2026-09-28  
Task: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001

Current Phase:

NETWORK_BLOCKED — 冒烟测试未执行（服务器不可达，任务书 §1 STOP）

Next Action:

1. 恢复执行机网络（回到可路由到 SERVER_IP 的内网/VPN）→ 从任务书 §1 重跑可达性探测
2. 可达后执行 OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001 全流程（端口/清单/6 chat/3 embedding/reranker/
   串行释放/显存/gateway log/Qwen3.5-9B 只读/vLLM 只读），结果写入同一份报告
3. （可选）运维手册固化：0.6B embedding 默认即释放，业务无需显式 keep_alive；如需驻留须显式传值
4. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- OLLAMA_TOPOLOGY = gateway 0.0.0.0:11434（pid=3028816）→ backend 127.0.0.1:11435（本轮未动）
- EMBED_06B = REUSED_EXISTING_MODEL（Q8_0 / ctx32768 / dim1024），未 pull、未重复权重
- EMBED_8B = PRESERVED（4.7GB 仍在列表）
- KEEP_ALIVE_DEFAULT = 0（网关注入），runner ≤1s 释放
- STRICT_EXCLUSION（Image↔Ollama 互斥）= 未改，回归 PASS
- CUDA_OOM（本轮）= NO
- 本轮（冒烟）禁止：pull/rm/create/下载/转换、启动 vLLM、改 Gateway/systemd/Image/Zrald/CUDA/driver、真实 IP 入 Git
- 禁止：未授权改 Gateway/拓扑/Image/Zrald/gpu.lock/queue/CUDA/driver/Open WebUI、删改已有模型
