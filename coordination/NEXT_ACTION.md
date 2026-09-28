# NEXT_ACTION

Updated At: 2026-09-28  
Task: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001

Current Phase:

OLLAMA ALL-MODELS PRODUCTION SMOKE COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：禁用词/真实IP 扫描 → 白名单 add（reports/coordination）→ commit → push main
2. （可选）reranker 业务接入：当前无 `/api/rerank` 端点，若业务需要重排，需 Commander 决策
   （改 Gateway 或换调用方式均属新授权范围）
3. （可选）Qwen3.5-9B 权重已在盘（19G HF safetensors），是否纳入 Ollama/vLLM 需 Commander 授权
   （`ollama pull qwen3.5:9b` 或 GGUF 转换，均本轮禁止）
4. （可选）恢复 vLLM（需授权）
5. （可选）运维固化：chat reasoning 模型调用建议 `think:false`（qwen3）或足够 num_predict（deepseek-r1）

Flags:

- VLLM_RUNNING = NO（8000 CLOSED，非当前 serving backend）
- OLLAMA_TOPOLOGY = gateway 0.0.0.0:11434 → backend 127.0.0.1:11435（未动）
- OLLAMA_MODELS = 10（6 chat + 3 embed + 1 reranker，名称与预期一致）
- RERANK_ENDPOINT = UNAVAILABLE（404，模型在库）
- STRICT_EXCLUSION = 未受影响，Image 全程 idle
- QWEN35_WEIGHT_PRESENT = YES（只读）
- 禁止：未授权 pull/rm/create、改 Gateway/systemd/Image/Zrald/CUDA/driver、启动 vLLM、真实 IP 入 Git
