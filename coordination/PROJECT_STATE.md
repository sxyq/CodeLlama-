# PROJECT_STATE

更新时间：2026-09-27  
Task: GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | STRICT OLLAMA/IMAGE SCHEDULER COMPLETE（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED） |
| ZRALD :8010 | RUNNING（flock 互斥未动，spawn_count=3） |
| OLLAMA | backend 改绑 **127.0.0.1:11435**（systemd unit 已改，PID2931799，10 模型完整）；**公网口由网关接管** |
| OLLAMA GATEWAY | `0.0.0.0:11434 → 127.0.0.1:11435`（serving/services/ollama/gateway.py，nohup）：完成类端点等 Image 槽、embed 缺省 keep_alive=0 注入、等待态放行释放请求（BYPASS_RELEASE） |
| IMAGE :8011 | 严格准入 = runner空 ∧ gpu.lock ∧ VRAM预算+3072MiB；WAITING_FOR_GPU 3s轮询/900s超时；queue timeout **1200**；/status 增 scheduler 块 |
| WEBUI :8020 | 徽标实时状态（等待 Ollama/正在生成等）、超高质量（实验性）·120、§19 Ultra 说明；dist 已重建；596 用例全绿 |
| E2E_A（image等ollama） | PASS（blocked_by=ollama → 释放后同请求4.6s admission →200） |
| E2E_C（chat模型） | PASS（chat200"OK"→等待90.1s→自动200；兼作 chat 回归） |
| E2E_B（核心） | PASS（5ref+2048²+120 运行中：模拟embed扣720.1s、ps全程空、图200、OOM零新增、完成后embed自动200；真实LAN客户端被扣56/618/720s） |
| KEEP_ALIVE=0 兼容 | PASS（4096维向量、即卸、二调正常；显式值保留实测） |
| Bypass修复 | 等待态释放请求0.16-0.19s放行；本地 harness 7/7 |
| TIMEOUT修复 | queue 480→1200 ≥ gpu wait 900 |
| OOM | 本轮0次（计数稳定212；00:15 事件=旧策略孤儿进程） |
| 回归 | t2i/5ref/2K/Ultra120/custom200(200→201→400)/embed/chat/Zrald/queue/unload409→200/TTL/端口 全 PASS |
| 运维规约 | `ollama stop` CLI 无效（/api/stop 404 空转）→ 一律 API `keep_alive:0` |
| 已知限制 | WebUI profile timeout600 < gpu wait900（长等待前端先断、服务端孤儿完成）；见报告§13 |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
