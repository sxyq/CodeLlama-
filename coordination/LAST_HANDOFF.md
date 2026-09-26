# Last Agent Handoff

Updated At: 2026-09-27  
Last Task ID: GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW（Git 结果见最终回复 / git log）

## Completed

- **Ollama 入口收口（无感迁移）**：unit 改 `OLLAMA_HOST=127.0.0.1:11435`（sudo 密码仅当次 stdin，未落盘）
  → daemon-reload/restart → 网关 `serving/services/ollama/gateway.py` 占 `0.0.0.0:11434`；
  LAN/本机客户端零配置切换。7天端点清单（journal sudo）：GPU 类 embed798/generate81/v1chat20/chat15/
  v1embed7/v1comp3/rerank1/embeddings1；透传 ps1164/tags68/show46 等。真实 LAN 客户端实测穿网关
  （被扣56/618/720s 后自动完成，注入 keep_alive=0 生效）。
- **严格互斥**：Image admission 第一层 `/api/ps` runner 空判定（512MiB 阈，不返回 GPU_BUSY）+
  VRAM 预算+3072MiB 双确认 + flock；网关在 Image 占槽时扣住完成类 Ollama 请求。
- **BYPASS_RELEASE 修复**：image 仅资源等待时放行 `keep_alive=0` 释放请求（0.16-0.19s），防互等；
  推理中仍全扣。本地 harness **7/7 PASS**。
- **timeout 修复**：`IMAGE_QUEUE_TIMEOUT_SECONDS 480→1200`（≥ GPU wait900）。
- **E2E**：A=Image等ollama（blocked_by=ollama→4.6s自动→200）、C=chat模型（chat200→90.1s→200，
  兼 chat 回归）、**B=核心**（5ref+2048²+120 运行中 embed 扣720.1s、ps全空、图200、
  OOM零新增、完成→embed自动200；真实LAN客户端同窗口被扣56/618/720s）。
- **keep_alive=0 兼容实测**（先于注入启用）：向量4096、即卸、二次调用正常；显式 keep_alive 保留。
- **/status.scheduler**：`state/blocked_by(none|ollama|zrald|gpu_memory)/image_running/ollama_running/zrald_running`。
- **UI**：徽标实时 `等待 Ollama`/`正在生成`（实拍）、`超高质量（实验性）·120`、Ultra 完整说明
  （本机5参考图实验档/非官方推荐/不保证优于40）；自定义1-200 与提示不变；dist 重建；
  npm test **35文件/596用例**全绿 + build 通过。
- **回归全 PASS**：t2i、5ref、2K、Ultra120（E2E B）、custom200→200 / steps201→400、embed、chat、
  Zrald /manager/status、queue 串行（0/65.4s）、unload 活体409→200、TTL1800/300、IDLE600、端口全绿。
- 报告：`reports/GPU_SCHEDULER_STRICT_OLLAMA_IMAGE.md`

## Status Flags

| Flag | Value |
|---|---|
| OLLAMA/IMAGE POLICY | STRICT SERIAL（runner空 ∧ lock ∧ VRAM双确认；网关扣完成类） |
| OLLAMA TOPOLOGY | backend 127.0.0.1:11435 ← gateway 0.0.0.0:11434（PID2931799） |
| QUEUE/GPU WAIT TIMEOUT | 1200 / 900（≥ 关系成立） |
| CUDA OOM（本轮） | NO（计数212不变；00:15=旧策略孤儿） |
| HOL POLICY | 保留占槽等待（报告§7 论证） |
| CLIENT TIMEOUT GAP | WebUI600 < wait900（限制项，见报告§13.1） |
| 运维 | `ollama stop` CLI 无效（404空转）→ API `keep_alive:0` |
| GIT | 见最终回复（`feat: serialize ollama and image gpu workloads` → push） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动，manager 正常，lease 空闲） |
| 8011 Image | RUNNING（严格准入，unloaded/FREE，idle600，queue1/8/480→timeout1200） |
| 8020 WebUI | RUNNING（dist=等待状态+Ultra实验档版） |
| 11434 | **网关**（→127.0.0.1:11435）；Ollama 仅回环 |
| 11435 | Ollama backend（回环，10模型完整） |
| 3000 OWUI | RUNNING（经 localhost:11434 → 网关，健康200） |
| 8000 vLLM | CLOSED |
| GPU | ~15.2GB（embed 水位），gpu.lock FREE |
| env | IDLE600 / TTL1800/300 / QUEUE_TIMEOUT**1200** / GPU_WAIT900·3s·margin3072 |

## 环境要点（下轮必读）

- **Ollama 拓扑变了**：外部一律打11434（网关），backend 只在回环11435；查后端直连11435、查入口看
  `~/ai-serving/logs/ollama/gateway.log`（含对端 IP）。journal 的源IP 现为网关回环。
- **卸载 Ollama 模型用 API**：`POST /api/embed|chat {"keep_alive":0}`；`ollama stop` CLI 在本服务器
  会空转到超时（/api/stop 404），不要用它做测试释放。
- **网关日志关键词**：`HELD`=扣住、`BYPASS_RELEASE`=等待态放行释放、`HOLD_TIMEOUT`、`KEEP_ALIVE_INJECT`。
- **sudo 模式**：密码仅经当次 ssh heredoc 首行 stdin（`IFS= read -r PW; … sudo -S -v`），永不落盘；
  heredoc 第一行必须是密码（本轮曾三次漏写首行导致空转，教训固化）。
- **前端 fetch 超时600s**：浏览器等待类请求超600s 会前端失败而服务端孤儿完成——测长等待要么服务端
  内定时释放，要么接受孤儿语义。
- 其余沿用：pkill 括号技巧、IAB filechooser 不可用、本机 rollup 坏、curl --noproxy、Node 于
  `env/node-v22.23.3-linux-x64/bin`、真实IP永不入Git。

## Exact Next Action

WAIT FOR COMMANDER REVIEW

## Do Not

- 未授权不升级/重装 Ollama、不动模型、不删模型；systemd unit 已按本轮授权改绑，勿回改0.0.0.0
- 不动 vLLM/Zrald/llama.cpp/Open WebUI/CUDA/Clash/网络
- 网关与 strict admission 是互斥闭环，勿单独关闭一侧
- 测试图/tmp/logs/模型/node_modules/dist本地配置/真实IP不入Git；禁 git add -A
