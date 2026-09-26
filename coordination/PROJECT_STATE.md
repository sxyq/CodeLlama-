# PROJECT_STATE

更新时间：2026-09-26  
Task: QWEN-IMAGE-MAX-CAPABILITY-AND-UI-PROFILE-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | MAX CAPABILITY + UI PROFILE COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED） |
| ZRALD :8010 | RUNNING（未动） |
| OLLAMA :11434 | RUNNING（qwen3-embedding:8b 周期驻留仍在，未改） |
| IMAGE :8011 | RUNNING（capability.py 单一配置源 + 多参考图1-5 + 512-2752/4.3MP/1.8 包络 + 409 guard + 计时拆分） |
| WEBUI :8020 | RUNNING（Model Profile：官方8档预设/5图上限/质量4步标注/自定义尺寸逐条校验；dist 已重建） |
| STEPS_VRAM_SCALING | MINIMAL（4/24/40 → img 峰值 17316/17282/17282 MiB） |
| T2I_2K_MATRIX | 7/7 PASS（峰值 30.4-33.7GB，embed 同场总峰值最高 48,455） |
| REF_MATRIX_1024 | 1-5 全 PASS（img 20.6→31.4GB） |
| REF_5_X_2K | 2048² idle PASS(41,372) / embed同场 OOM；2752×1536 idle PASS(45,396)；1536×27524×窗口被抢 NOT ESTABLISHED |
| ABSOLUTE_TESTED_MAX | 5ref + 2752×1536 + 40 steps（idle）img 45,396 / total 45,700 |
| PRODUCTION_SAFE_MAX | t2i 7档官方全开；edit ≤5ref 输出≤1024² 全条件；5ref×2K 仅空闲 GPU；最重工况余量3.4GB |
| OOM 处置 | 首次 OOM 后停压，看门狗8次中止零复犯，日志 OOM 计数保持75 |
| BROWSER_E2E | 5/5 标签+预设+质量40+尺寸校验+refs=5→200+旧错误0次；filechooser 路由不可用（等价路径完成） |
| 前端测试 | 35 文件 / 594 用例全绿，build 通过 |
| TTL/IDLE/QUEUE | 1800/300、600、1/8/480 未改（env+environ 确认） |
| 服务终态 | 8011 unloaded/FREE；8020 200；GPU 仅 embed 水位 |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
