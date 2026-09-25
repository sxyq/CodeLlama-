# PROJECT_STATE

更新时间：2026-09-26  
Task: QWEN-IMAGE-EDIT-API-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | EDIT API COMPLETE（待 Commander 审阅 + Git 结果） |
| VLLM_RUNNING | NO（8000 CLOSED） |
| ZRALD :8010 | RUNNING（llama.cpp，idle600，lease 空闲，未改动） |
| OLLAMA :11434 | RUNNING（10 模型，未改动） |
| IMAGE :8011 | RUNNING（PID 1944262 附近，idle600） |
| IMAGE_ENDPOINTS | health / status / **generations** / **edits（新，multipart）** / unload |
| EDIT_PIPELINE | QwenImage21Pipeline（image= 官方入口；**无 mask、无 strength**） |
| EDIT_E2E | 架构图 PASS（24步 std5.43→13.81）· 苹果红→绿 PASS（G−R −77.9→−3.8）· 错误用例6/6 PASS |
| EDIT_LOCK_MUTEX | 双向 PASS（Zrald⇄edits 均 503 lease-held） |
| TEXT_TO_IMAGE_REGRESSION | PASS |
| MASK_EDIT | UNSUPPORTED_BY_CURRENT_PIPELINE |
| IDLE_UNLOAD | PASS（edits 同样触发；600 已恢复） |
| OPENWEBUI_REQUIRED | NO |
| BLOCKING_ISSUE | NONE（观察项：2 次瞬时 status 读数异常，受控复现 4/4 正常） |
| Git | 见 LAST_HANDOFF（commit/push 结果以其为准） |
| Next Action | WAIT FOR COMMANDER REVIEW |
