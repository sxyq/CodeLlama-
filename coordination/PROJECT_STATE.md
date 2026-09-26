# PROJECT_STATE

更新时间：2026-09-26  
Task: IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | IMAGE WEBUI PLATFORM COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED，未恢复） |
| ZRALD :8010 | RUNNING（llama.cpp，idle600，本轮未改动） |
| OLLAMA :11434 | RUNNING（10 模型，未改动） |
| IMAGE :8011 | RUNNING（uvicorn，idle600，含 queue + CORS + TTL cleaner） |
| WEBUI :8020 | RUNNING（serve_static.py，dist @ aa2556df+P1-P5 补丁） |
| IMAGE_ENDPOINTS | health / status(+queue) / generations(+b64_json) / edits(+b64_json, image\|image[]) / unload |
| QUEUE | 单槽共享：max_concurrent=1, max_pending=8, timeout=480s；超限 429 QUEUE_FULL |
| QUEUE_E2E | 两并发采样 running=1/pending=1、双200、无 OOM → PASS |
| TEMP_OUTPUT | /home/syy/ai-serving/tmp/image-output/，TTL 1800s，300s 周期，60s 实测 PASS（已恢复1800/300） |
| CORS | IMAGE_ALLOWED_ORIGINS 白名单（代码无真实 IP），浏览器→:8011 全链路 PASS |
| WEBUI_E2E | t2i 1024²/1536×1024、edit keep-original/custom、预设4/4、mask toast、徽标 全 PASS |
| IDLE_UNLOAD | PASS（临时 IDLE=60 实测，已恢复 600） |
| BROWSER_LOCAL_HISTORY | ENABLED（IndexedDB，浏览器本地） |
| SERVER_HISTORY | DISABLED |
| OPENWEBUI_REQUIRED | NO |
| BLOCKING_ISSUE | NONE（观察项见报告 §25：Ollama embed 周期驻留需抓窗口；IAB filechooser/download 路由不可用） |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
