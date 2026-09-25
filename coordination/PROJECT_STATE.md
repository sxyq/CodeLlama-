# PROJECT_STATE

更新时间：2026-09-26  
Task: MODEL-DYNAMIC-LOAD-E2E-VALIDATION-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | E2E VALIDATION COMPLETE（待 Commander 审阅 + Git 执行结果） |
| VLLM_RUNNING | NO（8000 CLOSED，未恢复） |
| ZRALD_BACKEND | LLAMA_CPP（:8010 管理器 →8012，ctx 32768，idle 600） |
| ZRALD_DYNAMIC_LOAD / UNLOAD | PASS / PASS（cold 8.9s、warm 1.09s、decode ≈35 t/s、idle60 释放→600 已恢复） |
| OLLAMA_E2E | PASS（10/10 现存模型：6 chat +3 embed 全 PASS，reranker=API_NOT_AVAILABLE，串行 load/test/unload 全部 GPU 回650） |
| OLLAMA_DUPLICATE_REMOVED | YES（qwen3.8-27b-zrald-accuracy 已删；RECOVERED≈16.46GB；/data 源文件 SHA 复验 MATCH；余10模型全在） |
| IMAGE_E2E | PASS（lazy 1.34s / gen 59.95s / 峰34,726MiB / 示意图 e2e-validation PNG 2048² 有效 / unload+锁释放） |
| GPU_LOCK | 双向 PASS（Zrald→Image、Image→Zrald 均503 lease-held） |
| OLLAMA_RACE_OBSERVED | YES（LAN CLIENT_IP_REDACTED embed 阻塞冷测1次；成功推理窗口无干扰无 OOM；未阻止外部客户端） |
| OPENWEBUI_REQUIRED | NO（:3000 未动） |
| BLOCKING_ISSUE | NONE |
| Git | 见 LAST_HANDOFF（本轮执行 commit/push，结果以其为准） |
| Next Action | WAIT FOR COMMANDER REVIEW |
