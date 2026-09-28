# PROJECT_STATE

更新时间：2026-09-28  
Task: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | OLLAMA 全模型生产 smoke COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED，无 vllm 进程；tmux session `vllm` 内 pane=bash） |
| ZRALD :8010 | RUNNING（未动） |
| OLLAMA | backend 127.0.0.1:11435（回环）；网关 0.0.0.0:11434（pid=3028816）；**10 模型，零增删** |
| 全模型 smoke | **10/10 逐一实测**：chat 6/6 PASS（200+可见输出）、embed 3/3 PASS（dim 1024/4096/768 有限数值）、reranker 模型在但 `/api/rerank` 网关+backend 均 **404 → ENDPOINT_UNAVAILABLE** |
| 串行与释放 | 每模型 `keep_alive=0` → `/api/ps` ≤1s 清空 → GPU 回落 682 MiB 基线；无并发加载 |
| Gateway path | 全部业务请求经 SERVER_IP:11434，gateway.log 可见；11435 只读 metadata |
| Image :8011 | 全程 `state=idle`，队列全 0，严格串行调度未受影响 |
| Qwen3.5-9B | `QWEN35_WEIGHT_PRESENT=YES`（`/data/vllm/Qwen3.5-9B` 19G/4 分片；config: Qwen3_5ForConditionalGeneration、bf16、32 层、hidden 4096、带 vision_config）——只读，未部署未转换 |
| Chat thinking | qwen3:8b 用请求体 `think:false` 得字面 OK；deepseek-r1:7b 需 `num_predict=512` 才出可见回答（thinking 不可关） |
| 端口 | 11434 网关 / 11435 仅回环 / 8010 / 8011 / 8020 / 3000 开 / 8000 CLOSED |
| 网络 | 恢复（22/11434/8011 全通；本机曾因切换到 10.225.129.x 网段断连约 1 小时） |
| 本轮改动 | 仅 `reports/OLLAMA_ALL_MODELS_PRODUCTION_SMOKE.md` + 协调文件；**服务端零改动** |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
