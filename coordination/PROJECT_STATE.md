# PROJECT_STATE

更新时间：2026-09-27  
Task: OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | OLLAMA QWEN3-EMBEDDING-0.6B VERIFY COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED） |
| ZRALD :8010 | RUNNING（flock 互斥未动） |
| OLLAMA | backend **127.0.0.1:11435**（回环，unit 未动）；公网口网关 **0.0.0.0:11434**（pid=3028816，逻辑未动）；**10 模型完整，本轮零增删** |
| OLLAMA 模型（Embedding） | `qwen3-embedding:0.6b`（**REUSED_EXISTING_MODEL**：qwen3 / 595.78M / **Q8_0** / ctx **32768** / dim **1024** / capabilities=embedding）、`qwen3-embedding:8b`（PRESERVED）、`nomic-embed-text` |
| OLLAMA 模型（Chat/Gen） | qwen2.5-coder:7b-instruct、qwen2.5-coder:14b-instruct、qwen3:8b、qwen3-coder:30b、codellama:13b-instruct、deepseek-r1:7b |
| OLLAMA 模型（Reranker） | linux6200/bge-reranker-v2-m3 |
| 0.6B API 验证 | 英/中 embedding 200·dim1024·有限数值 PASS；长文本 8000字符/1779token PASS；相似度 A-B **0.845444** > A-C **0.354812** PASS |
| 0.6B keep_alive | 缺省注入 `KEEP_ALIVE_INJECT POST /api/embed -> 0` 实证；runner **≤1s** 释放，`/api/ps` 清空 |
| 0.6B 显存 | 基线 682 → 加载峰值 **6807 MiB**（模型进程 6120）→ 释放回落 **682** |
| 调度回归 | embed → runner 自动释放 → Image 1024×1024 **200/59.3s**（steps24，峰值 17602 MiB），无手工清理 |
| IMAGE :8011 | RUNNING，严格准入未动，unloaded/idle，queue1200 / GPU wait900 |
| WEBUI :8020 | RUNNING（超时对齐版 1200s，dist 含 `12e5`；600 用例全绿） |
| OOM（本轮） | NO（未做极限测试，仅真实读数） |
| 本轮改动 | 仅新增 `reports/OLLAMA_QWEN3_EMBEDDING_06B.md` + 协调文件；**业务代码/配置零改动** |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
