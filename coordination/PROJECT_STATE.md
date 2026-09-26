# PROJECT_STATE

更新时间：2026-09-27  
Task: IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | GPU WAIT QUEUE + MAX STEPS COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED） |
| ZRALD :8010 | RUNNING（未改动；本轮仅作为 wait 测试对象被正常触发 spawn/idle 释放） |
| OLLAMA :11434 | RUNNING（未改；外部客户端周期 embed 载入仍在） |
| IMAGE :8011 | RUNNING（VRAM 预算 admission + WAITING_FOR_GPU 队列 + timeout900；单实例；unloaded/FREE） |
| WEBUI :8020 | RUNNING（slider1-200、Ultra120、动态提示、预计耗时、等待GPU徽标；dist 已重建） |
| GPU_WAIT_QUEUE | admission=free≥budget(实测标定)+3072MiB 余量；不持锁等待；3s 轮询；超时 503 GPU_WAIT_TIMEOUT |
| STATUS_QUEUE | {running, pending, waiting_for_gpu, max_pending} |
| E2E_A_ZRALD | PASS（租约原因等待600.9s → 同请求自动200，image 侧锁全程 null） |
| E2E_B_OLLAMA | PASS（embed 驻留 t2i 直接200，零 gpu-wait 日志，冷加载6.47s） |
| E2E_C_OLLAMA | PASS（5ref2K 等待→资源变化→同请求自动200；等待期 image VRAM 恒564MiB） |
| E2E_TIMEOUT | PASS（30s→503 GPU_WAIT_TIMEOUT「等待 GPU 超时（30s）」，已恢复900） |
| STEPS_MATRIX | 24-200 八档全200；img 峰值31,386-31,528（差0.45%）→ STEPS_VRAM_SCALING=MINIMAL |
| QUALITY_PLATEAU_STEP | 120（160倒退、200未超越） |
| RECOMMENDED_HIGH_STEP | 120（Ultra 档=超高质量·120步） |
| MAX_TESTED_STEP | 200；官方推荐保持40 |
| ULTRA_2K_CONFIRM | 5ref+2048²+120：首次 OOM（embed 中途载入=外部竞态实证）→防御重跑200（715.7s，img45,988） |
| OLLAMA_EXTERNAL_RACE | STILL_PRESENT（admission 挡不住起跑后载入；生产路径不碰 Ollama） |
| CANCEL_WAITING | 未实现（需 job id 架构，按任务书§7 记录不阻塞） |
| BROWSER_E2E | Ultra120 档/slider/自定义80→`steps=80 refs=5`→200/提示/徽标「等待GPU中」实时 ✓ |
| 前端测试 | 35 文件 / 596 用例全绿，build 通过 |
| 回归 | 映射5/5、单图/5图编辑、queue、unload 409→200、idle600、TTL1800/300、端口全绿 |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
