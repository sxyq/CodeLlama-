# GPU SCHEDULER — STRICT OLLAMA / IMAGE EXCLUSION REPORT

Task ID: GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001
Date: 2026-09-27
Services: SERVER_IP:8011 (Image), SERVER_IP:8020 (WebUI), SERVER_IP:11434 (Ollama Gateway → backend 127.0.0.1:11435), SERVER_IP:8010 (Zrald), RTX A6000 49,140 MiB

---

## 1. Current race（改造前）

- Image admission 只有两层：VRAM 预算 + gpu.lock；**Ollama 驻留不再拦截**（上一轮为共存策略）。
- 外部 LAN 客户端在 Image 已开始推理后仍可触发 `POST /api/embed` → Ollama 中途加载 runner →
  5ref×2K decode 阶段显存不足 → **CUDA OOM**（IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS-001 已实际发生：
  2K@120 首次复核 OOM）。
- 同时存在 timeout 不一致：`IMAGE_QUEUE_TIMEOUT=480 < GPU_WAIT_TIMEOUT=900`——前序请求等 GPU 600s 时，
  后续 pending 请求会先于它超时（head-of-line 反向超时）。

## 2. Scheduler design（本轮实现）

```
ALLOW_IMAGE = ollama_gpu_runner_empty AND gpu_lock_available AND vram_admission_pass
```

- **Image 侧**（`model_manager.py`）：`_gpu_admission` 第一层查询
  `GET /api/ps`（1s 缓存，`size_vram ≥ OLLAMA_GPU_MIN_MIB=512` 即
  `ollama gpu runner active` → GpuBusy → WAITING_FOR_GPU，**不返回 GPU_BUSY**）；
  第二层沿用 VRAM 预算 + `IMAGE_GPU_SAFETY_MARGIN_MIB=3072` 双重确认（起跑前后各一次）；
  gpu.lock 仍由调用方在两次 admission 之间获取。`ollama_gpu_runner_mib()` 在 /api/ps
  不可达时按 0 处理（无 runner 存在的证据，VRAM 层兜底），避免服务停机导致 Image 永久等待。
- **Ollama 入口侧**（`gateway.py`，见 §4）：Image 占槽期间，GPU 完成类端点排队等待。
- 等待循环不变：3s 轮询、`IMAGE_GPU_WAIT_TIMEOUT_SECONDS=900` → 503 `GPU_WAIT_TIMEOUT`。
- Zrald：flock 互斥完全保留（等待原因为 lease 时 `blocked_by=zrald`）。

## 3. Ollama endpoint inventory（7 天 journal，sudo 读取）

GPU 完成类（网关需调度）：

| Method+Path | 7d 次数 |
|---|---|
| POST /api/embed | 798 |
| POST /api/generate | 81 |
| POST /v1/chat/completions | 20 |
| POST /api/chat | 15 |
| POST /v1/embeddings | 7 |
| POST /v1/completions | 3 |
| POST /api/rerank | 1 |
| POST /api/embeddings | 1 |

透传类（不调度）：GET /api/ps 1164、GET /api/tags 68、POST /api/show 46、GET /v1/models 3、
GET /api/version 2、POST /api/create 1、POST /api/blobs/… 1、GET /api/status 1。

客户端：**CLIENT_IP_REDACTED（LAN，816 POST，主为 /api/embed）**、127.0.0.1（OWUI/本机服务/测试）。
（迁移后 journal 源地址变为网关127.0.0.1；网关日志记录真实对端地址。）

## 4. Gateway decision（§6–§8，无感迁移）

- **方案：Ollama backend 改绑 `127.0.0.1:11435`，网关占用 `0.0.0.0:11434`** —— 所有 LAN/本机客户端
  继续使用原 `SERVER_IP:11434`，无需任何客户端配置变更（§8 最小迁移方案）。
- 前置兼容性确认后才执行：端点清单（§3）+ `keep_alive=0` embed 功能实测（返回4096维向量、runner
  即卸、二次调用正常 → **COMPATIBLE**）+ 用户授权（sudo 密码仅经当次 stdin，未落盘）。
- 执行：改 `/etc/systemd/system/ollama.service` 的 `OLLAMA_HOST` → `daemon-reload` → `restart ollama`
  （进程换绑，PID2931799，模型列表10个完整保留）→ 立即启动网关 → 全链路联通核验
  （`/api/version`、`/api/ps`、`/api/tags` 直通正常）。
- 网关实现（`serving/services/ollama/gateway.py`，nohup 启动脚本 `scripts/ollama/start_ollama_gateway.sh`）：
  - 每请求独立 HTTP 事务（`Connection: close` 双侧），按 §3 清单分类
  - GPU 完成类：等 Image 槽空闲（读 `/status`，2s 轮询）→ 转发；超时1800s → 503
  - embed 类端点缺省注入 `keep_alive=0`（**客户端显式值原样保留**，实测 keep_alive:60/-1 均未被改写）
  - 透传类即时转发；流式/分块响应按字节中继
- 本地测试harness（fake Image status + fake Ollama backend）：**7/7 PASS**，覆盖直通、扣住-放行、
  注入、显式保留、**释放请求旁路**、等待中普通请求仍扣、超时503。
- 运维发现（记录）：本服务器 `ollama stop` CLI 实际发送 `/api/stop`，但该路由在后端返回 **404**——
  CLI 只能轮询 ps 空转到超时；历轮"stop 成功"实为 keep_alive 自然到期。运行规约改用
  **API `keep_alive:0` 卸载**（本轮全部脚本均如此）。

### 释放请求旁路（运行中发现并修复的真实缺陷）

Image 处于 `waiting_for_gpu`（等 runner 清空）时，**释放型请求（body `keep_alive=0`）若也被网关扣住，
将互相等待**（长 keep_alive 的 runner 靠自然到期才能解，极端下饥饿）。修复：
网关在 image `scheduler.state == waiting_for_gpu` 时放行 `keep_alive=0` 的 GPU 类请求
（`BYPASS_RELEASE` 日志）；image 真在 `running`（推理中）时一律扣住（严格互斥不破）。
本地 harness 新增2用例后 **7/7 PASS**；生产实测：等待中释放 **0.16–0.19s** 返回，`BYPASS_RELEASE`
入日志，Image 在 **~3–6s 内自动 admission 并66.3s 完成**。

## 5. Strict mutual exclusion

- Image→Ollama：admission 第一层 runner 空判定（§2），runner 在场一律 WAITING（E2E A/C 实证）。
- Ollama→Image：网关扣住完成类请求直到 Image 槽空（E2E B 实证：720.1s 扣住，期间 `/api/ps` 全程为空，
  图像200、OOM 计数不变）。
- Zrald：flock 不变；Image 等待 lease 的场景在上轮 E2E A 已验证（本轮回归 /manager/status 正常）。
- 双层合起来：**任一时刻至多一方在用 GPU**（embed 的瞬时 in-flight 请求除外——网关放行的
  keep_alive=0 释放调用本身会短暂加载 runner，但它发生在 Image 仅资源等待、未占 GPU 的窗口，
  随即卸载，Image 随后 admission）。

## 6. Queue timeout fix

- `IMAGE_QUEUE_TIMEOUT_SECONDS`：480 → **1200**（≥ GPU wait 900），消除"前序等 GPU、后续 pending 先超时"。
- `service.env.example` 注明约束：queue timeout 必须 ≥ `IMAGE_GPU_WAIT_TIMEOUT_SECONDS`。
- 实测 env：`QUEUE_TIMEOUT=1200 / GPU_WAIT_TIMEOUT=900 / poll=3s / margin=3072MiB`。

## 7. HOL handling（设计选择，报告 §13 要求）

- **保留"等待占用 execution slot"模型**（QUEUED → WAITING_FOR_GPU → RUNNING，未引入 PENDING_RESOURCE 重排队）。
- 理由：严格互斥下 Ollama active 时**所有** Image 请求都必须等，HOL 拆分不能让任何请求提前执行，
  只会引入重排队/乱序复杂度；timeout 对齐（§6）已消除最实际的 HOL 危害（先到者被后来者超时）。
- 代价（如实记录）：一个高预算请求等待期间，低预算请求同在等待——行为上等价于全局串行，与政策目标一致。
- 若未来出现"部分请求可跑"的混合准入，再考虑 PENDING_RESOURCE。

## 8. Image waiting for Ollama test（E2E A + C）

**E2E A（embedding）**：embed keep_alive=60 驻留 → 提交 t2i 1024×1024/24：

| 时点 | 结果 |
|---|---|
| t=1.5s | `queue.waiting_for_gpu=1`，`scheduler.blocked_by="ollama"`，`ollama_running=true` |
| 日志 | `[gpu-wait] WAITING_FOR_GPU budget=17565MiB blocked_by=ollama reason: ollama gpu runner active (15378904864MiB resident)` |
| 释放（embed keep_alive=0） | 同一请求 `admitted after 4.6s` → **200**（inference 58.155s，effective24） |

**E2E C（chat 模型 qwen2.5-coder:7b-instruct，经网关）**：

- chat 请求200，回复 "OK"（**Ollama chat 回归 PASS**），runner 驻留
- Image → `blocked_by=ollama` 等待 → chat 释放（keep_alive=0 调用）→ 同一请求
  `admitted after 90.1s` → **200**（inference 70.633s）

**Image waits for Ollama = PASS；Automatic Image start = PASS**

## 9. Ollama waiting for Image test（E2E B，核心验收）

5 refs + 2048×2048 + **120 steps（Ultra）** 启动 RUNNING 后，模拟 LAN 客户端
`POST /api/embed`（不带 keep_alive，走注入路径）：

| 断言 | 结果 |
|---|---|
| embed 不得立即加载 runner | **PASS**：扣住期间 `/api/ps` 逐采样**全为空**（60s 窗口0次载入） |
| Image 全程无中断 | **PASS**：`queue.running=1` 全程保持 |
| Image 结果 | **200**，effective_steps=120，inference 720.813s，输出 2048×2048 |
| OOM | **计数 212→212 零新增** |
| Image 完成后 Ollama 自动执行 | **PASS**：被扣 embed 在图像完成后自动转发，**等待720.1s → 200（4096维）** |
| 真实 LAN 客户端（CLIENT_IP_REDACTED） | 同窗口被扣 **56s / 618s / 720s** 后完成，`keep_alive` 注入生效；其中1条客户端提前断开（Broken pipe，属客户端超时行为，网关与后端无损） |

**Ollama waits for Image = PASS；Automatic Ollama start = PASS；5ref 2K Ultra 而 Ollama 请求到达 = PASS**

## 10. OOM regression

- **严格策略部署后（本轮起）零新增 CUDA OOM**；总计数全程稳定在212。
- 历史 OOM 事件回顾（日志时间簇）：18:50（约70行）、23:31（约70行，上轮已报告的2K@120 embed 中途载入）、
  00:15（约68行，**迁移窗口期旧 admission 策略的孤儿进程**所发——该进程持有旧代码，部署完成前已自然消亡）。
  18:04–18:19 的5条单行 allocator 警告为自动重试成功、请求未失败。
- 结论：**CUDA OOM = NO（本轮0次；严格互斥生效后）**。

## 11. UI states（§21）

`GET /status` 新增：

```json
"scheduler": {"state": "idle|queued|running|waiting_for_gpu",
              "blocked_by": "none|ollama|zrald|gpu_memory",
              "image_running": false, "ollama_running": true, "zrald_running": false}
```

（无客户端 IP / PID；`blocked_by` 枚举严格四值。）

WebUI 徽标（`QueueStatusBadge`）实时状态：

- **`队列 1/0 · 等待 Ollama · 模型未载入`** —— 浏览器实拍（blocked_by=ollama，两次）
- **`队列 1/0 · 正在生成 · 模型已载入`** —— 浏览器实拍
- 空闲：`队列 0/0 · 模型…`（无多余状态词）
- 代码路径覆盖 `等待 Zrald / 等待 GPU / 队列中`（同函数映射；等待Zrald由上轮 E2E 的服务端
  blocked_by=zrald 证据支撑，本轮未再开 Zrald 实拍）

## 12. Steps UI wording

- 质量档：快速4 / 标准24 / 高质量40（官方推荐） / **超高质量（实验性）·120 步**（仅
  `recommendedHighSteps>40` 出现，通用模型 Profile 恒不出现）
- Ultra tooltip（实拍 DOM）：`官方高质量 / 40 steps（快速 4 · 标准 24）· 超高质量（实验性）120：
  本机 5 参考图测试中表现较好的实验档，不是官方推荐值，也不保证所有 prompt/seed 都优于 40；官方推荐 40 steps`
- 自定义 steps 保持 **1–200**（number+slider），`>40 高计算成本`、`>100 实验性` 提示不变，
  未把200命名为最高质量；接口实测：`steps=200 → 200`（inference 85.53s），`steps=201 → 400`
- 前端测试 **35 文件 / 596 用例全绿**，`npm run build` 通过，对外 dist 已重建

## 13. Remaining limitations

1. **客户端超时 vs 等待时长**：WebUI profile timeout=600s < GPU wait900s——若等待超过600s，
   浏览器 fetch 中断（卡片失败）而服务端请求继续跑完（孤儿完成，实测两次）。建议后续把 profile
   timeout 调到 ≥900 或在 UI 提示预计等待；本轮已记录未改。
2. 客户端提前断开（Broken pipe / 轮询空转）：网关按连接中止处理，无泄漏；属客户端行为。
3. `ollama stop` CLI 在本服务器无效（/api/stop 404 + 空转）——运维统一用 API `keep_alive:0`；
   若未来升级 Ollama 修复该路由，行为自动恢复。
4. 严格互斥下 embed 的"释放型调用"仍会瞬时加载 runner（秒级），发生在 Image 仅等待时；概率窗口极小，
   若与 Image 冷启动同刻竞争，由 VRAM 双重 admission +3GB 余量兜底。
5. keep_alive 注入只覆盖 embed 类端点；chat/generate 显式 keep_alive 完全尊重客户端（长驻由客户端决定，
   Image 等待时长相应拉长，受900s 超时约束）。
6. journal 迁移后源 IP 变为网关回环地址——客户端维度审计改看网关日志（含对端地址）。

## 14. Git

- 提交范围：`serving/`（services/ollama/gateway.py 新增、services/image/*、configs/image/env.example、
  scripts/ollama/start_ollama_gateway.sh、configs/ollama/gateway.env.example）、
  `webui/image-platform/upstream/src/`（3文件）、`reports/`、`coordination/`
- 禁止项：模型/日志/测试图/真实 IP/secret/node_modules/dist 本地配置 —— 不入 Git
- secret scan PASS 后 commit：`feat: serialize ollama and image gpu workloads` → push main
- 结果见最终回复
