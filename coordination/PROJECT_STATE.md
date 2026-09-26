# PROJECT_STATE

更新时间：2026-09-26  
Task: IMAGE-WEBUI-QUALITY-SAFETY-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | QUALITY + INFERENCE SAFETY COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED，未恢复） |
| ZRALD :8010 | RUNNING（llama.cpp，未改动） |
| OLLAMA :11434 | RUNNING（10 模型，未改动；embedding 周期驻留仍在） |
| IMAGE :8011 | RUNNING（idle600，queue+CORS+TTL+quality 映射+inference guard） |
| WEBUI :8020 | RUNNING（serve_static.py，dist 已重建：中文质量三档+生效步数显示） |
| QUALITY_MAP | fast/low=4，standard/medium/auto=24，high/xhigh/max=40；优先级 显式 steps>quality>24；单一 helper 双端点共用 |
| DEFAULT_QUALITY | medium（标准=24），不再默认 4 |
| INFERENCE_GUARD | _inference_lock 全程持有（load+推理+编码）；推理中 /unload → 409 INFERENCE_BUSY；watcher 跳过本轮 |
| TIMING | queue_wait / load / inference / total 四字段；generation_seconds 兼容 = inference |
| UNLOAD_DURING_INFERENCE | SAFE（409 + 锁 held + 生成 200 无 CUDA 错误） |
| ZRALD_LEASE_SAFETY | PASS（推理中两 probe 均 503 GPU_BUSY，holder=image-service） |
| A/B/C | 4/24/40 步真实生成 PASS（seed=42，1024²，计时/峰值 VRAM/文件已记录） |
| QUEUE_E2E | 串行 PASS：首请求 queue_wait=0.000，次请求=59.698 |
| IDLE_UNLOAD | IDLE=20 临时实测 PASS（推理中不卸载，结束后 36.2s 卸载），已恢复 600 |
| TEMP_OUTPUT | TTL 1800s/300s 未改动（env+进程 environ 双确认） |
| BROWSER_E2E | 高质量→生效步数40→日志 steps=40→出图；快速→4；PASS |
| 前端测试 | 34 文件 576 用例全绿；build OK |
| BLOCKING_ISSUE | NONE（Ollama embed 驻留窗口依赖为既有观察项，见报告 §13） |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
