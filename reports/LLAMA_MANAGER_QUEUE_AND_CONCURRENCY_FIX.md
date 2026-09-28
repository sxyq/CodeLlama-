# LLAMA MANAGER QUEUE AND CONCURRENCY FIX REPORT

Task ID: LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001
Date: 2026-09-28
Base: HEAD `54c3d4b`（本轮之前）
范围：仅 `serving/services/llama-manager/`、`serving/services/ollama/gateway.py`、`reports/`、`coordination/`
未动：模型 / GGUF / models.yaml 模型路径与 context / Ollama tag / Image / vLLM / CUDA / driver

---

## 1. Old 503 behavior

旧 `ensure_model()` → `lease_acquire()`：Image 或任何持有者占用 `gpu.lock` 时立刻
`BlockingIOError → GpuBusy → HTTP 503 GPU_BUSY`，同一请求不重试，客户端必须人工重发。
Ollama runner 驻留、nvidia 大进程占用时同样快速失败。这与统一排队目标相反。

本轮实测复现（测试套件中以伪造 Image 持锁构造）：旧路径等价于"锁不可用即失败"，
新路径下同一场景进入等待而非失败（见 §2/§6）。

## 2. GPU waiting state machine

新增配置（环境变量，默认即任务书要求值）：

| 参数 | 默认 | 含义 |
|---|---|---|
| `LLAMA_MANAGER_GPU_WAIT_TIMEOUT` | **900** | GPU 等待总时长，超时 → 503 `GPU_WAIT_TIMEOUT` |
| `LLAMA_MANAGER_GPU_WAIT_POLL` | **3** | 等待轮询间隔（秒） |

状态机（`/manager/status` 新增 `state` / `waiting_for_gpu` / `blocked_by`，不暴露 PID/IP）：

```
QUEUED → WAITING_FOR_GPU → LOADING → RUNNING → IDLE → UNLOADED
```

`blocked_by` 取值域（强校验，越界回落 `none`）：`ollama | image | gpu_lock | gpu_memory | none`

等待条件（任一成立即等待，全部安静才继续）：

| 条件 | blocked_by |
|---|---|
| A. `gpu.lock` 被 Image / 其他持有者占用 | `image`（holder 含 image）/ `gpu_lock` |
| B. Ollama `/api/ps` 存在 >1GB GPU runner | `ollama` |
| C. nvidia-smi 有其他 >1GB 计算进程 | `gpu_memory` |

锁策略（§2 "等待期间不持锁" 与 §13 "切换中租约保持" 的统一）：

- **未持锁的排队**：每轮只做非阻塞探测；`锁空闲 ∧ ollama 空 ∧ nvidia 空` 三者同时成立才
  瞬时取锁进入 LOADING——纯粹排队期间**不持有** `gpu.lock`；超时释放所取的锁。
- **持锁换模（lease across switch）**：先 SIGTERM 旧 backend（释放其 VRAM）→ **保持租约**
  等 Ollama/其他进程排空 → spawn 新模型——全程不出现"放锁再抢锁"（§13 顺序保持）。

网关侧超时保持 1800s 不变，Image 900/1200 不变，模型切换队列超时 900s。

## 3. Atomic inflight design

旧结构：`ensure_model(model)`（临界区 1）与 `state["inflight"] += 1`（临界区 2）之间存在
窗口——另一个请求可在窗口内看到 `inflight==0` 并切换模型，第一个请求随后被发到错误的 backend。

新结构（单一 `threading.Condition = state["cond"]`，`model / proc / inflight / transition /
waiting_for_gpu / blocked_by / phase / last_activity / lock_fd` 全部在该条件变量下访问，
不再混用 `mu` + `cond`）：

```
acquire_model_for_request(key):
  with cond:
    while True:
      if transition:            # 别人正在等待/加载/切换 → 只能等
          wait(); continue
      if model==key && proc alive:
          _call_hook(selection→reserve)   # 测试注入点
          inflight += 1                   # ← 选择与预留在同一临界区
          return Reservation
      if inflight > 0:          # 需要换模型但当前推理未排空 → QUEUE
          phase=QUEUED; wait(); continue
      transition = True          # 取得唯一的"准备权"
      break
  # ---- 临界区外（transition=True 挡住其他加载请求）----
  [stop old if switch] → _wait_gpu_until(900s) → spawn → 
  with cond:
      model/proc 更新 + inflight += 1 + transition=False + notify   # 同一临界区原子完成
```

`release_request_reservation()`：`with cond: inflight -= 1; last_activity = now; notify_all()`。

**不变量**：其它线程只能在两个临界区**之间**观察状态，永远看不到"已选模型但未预留 inflight"
的中间态；同刻只允许一个线程处于 transition（等待/加载/切换互斥）。

`/status` 推导：`transition → WAITING_FOR_GPU/LOADING`；`inflight>0 → RUNNING`；
驻留无请求 → `IDLE`；无 backend → `UNLOADED`。

## 4. Deterministic race reproduction

`test_atomic_inflight_reservation`（不靠 sleep 碰运气）：

1. 预热 mistral → A 请求命中同模型，**在 selection 与 reserve 之间**被
   `TEST_HOOKS["after_selection_before_reserve"]` 用 `Event` 卡在临界区内部；
2. B（请求 qwen3-14b）随后发起——旧实现会在该窗口看到 `inflight==0` 并切换；
   新实现中 B 连临界区都拿不到（cond 被 A 持有），**2×poll 周期内 B 必须仍阻塞**；
3. 期间断言 `status.model` 仍是 mistral（没有被切换）；
4. 放行 hook → A 完成预留与推理（`A_reserved → A_done`）→ B 才获得 cond →
   等 A 排空 → 切换 → 预留。

实测输出（deterministic）：

```
B blocked inside A's critical section (window closed)
order=['A_reserved', 'A_done', 'B_reserved', 'B_done']
[PASS] test_atomic_inflight_reservation
```

旧实现在步骤 2 会直接复现"B 在 A 预留前切换"的错误窗口。

## 5. Race fix

同上：选择 + 切换判定 + `inflight` 预留合并进**一个** `with cond` 临界区；模型状态交换
（`model/proc` 更新与 `inflight += 1`）也在同一个临界区完成；`transition` 标志保证全局
至多一个准备者。HTTP 层现在是 `reservation = acquire_model_for_request(desired)` →
proxy → `finally: release_request_reservation(reservation)`，两步不再分离。

## 6. Image → llama wait E2E（E2E A）

真实流程：Image 发 1024×1024 → RUNNING → 立即 POST `:8010/v1/chat/completions`
（mistral）：

| 时点 | 观测 |
|---|---|
| Image running +8s | llama `state=WAITING_FOR_GPU`、`blocked_by=image`、`waiting_for_gpu=true`，请求**未返回 503**（线程仍在等待）|
| Image 完成 | `image 200 / 58.5s`；Image 按既有语义驻留至 idle 600s 才卸载释放 `gpu.lock`（本轮未改 Image，锁语义 = 跟随卸载）|
| 锁释放后 | **同一 HTTP 请求自动继续**：`LOADING → RUNNING → 200`，`content=" OK…"` |
| 全程 | `llama wall = 662.7s`（覆盖 Image 运行 58.5s + idle-unload 600s + spawn），未重新提交 |

**Image busy → llama waits: PASS　Automatic resume: PASS**

> 说明：等待 662.7s < GPU_WAIT_TIMEOUT 900s；Image 的 600s 驻留窗口被 900s 等待完整覆盖
>（这是把 900s 设为默认值的实际意义）。

## 7. Ollama → llama wait E2E（E2E B）

1. `qwen3:8b` 以 `keep_alive:-1` 驻留（`/api/ps` 确认 runner 在）；
2. llama mistral 请求 → `state=WAITING_FOR_GPU`、**`blocked_by=ollama`**（锁此时空闲，
   判定信号来自 `/api/ps`）；
3. 释放 Ollama（`keep_alive:0`）→ **同一请求 14.6s 后 200**。

**Ollama busy → llama waits: PASS　Automatic resume: PASS**

### 7.1 反向：llama busy → Ollama waits

llama 驻留（`lease_held=true`）时经网关发 `/api/embed` → 网关扣住（8s 后仍未返回）→
终止 llama backend（watchdog 释放租约）→ **同一 embed 请求 15.8s 后 200**。

### 7.2 反向：llama busy → Image waits

llama 驻留持锁时发 Image 1024×1024 → Image `state=waiting_for_gpu`（queue waiting=1）→
释放 llama → **Image 自动 200 / 74.7s**。

### 7.3 Image busy → Ollama waits

Image running 期间网关 embed 8s 未返回（被扣）→ Image 200/63.3s → **embed 自动 200/61.7s**。

**§20 六个方向全部实测通过，无一依赖人工重试。**

## 8. model-switch concurrency E2E（E2E C）

- A：`qwen3-14b-local` 长推理（700 token 预算），`inflight=1`、`state=RUNNING`；
- B：1.5s 后请求 `mistral-7b-instruct-v0.2-local` → **QUEUED**（A 的 model 不被切换/kill）；
- A 完成 → B 自动切换 → 200。

响应来源核验（响应 `model` 字段 = backend alias）：

```
A: http 200, model=qwen3-14b-local
B: http 200, model=mistral-7b-instruct-v0.2-local
final model = mistral-7b-instruct-v0.2-local
```

**Different-model concurrency: PASS　A 的请求绝不会发给 B backend: PASS（model 字段断言）**

## 9. Same-model concurrency

两个 mistral 请求并发：

- 都 **200**；`spawn_count` 全程不变（`8 → 8`，无重复 spawn、无重复 switch）；
- 单元测试侧同场景断言 `inflight == 2`（同一 backend 双预留）。

**Same-model concurrency: PASS**

**Lease across switch**：切换全程 `lease_held=true`（stop 旧 → 等排空 → spawn 新均持锁，
无"放锁再抢"）；E2E C 与测试 `test_different_model_switch_waits` 期间持续采样确认。
**PASS**

**idle 行为**：`idle_timeout=600` 不变；unload 仅在 `inflight==0 ∧ transition==false ∧
waiting_for_gpu==false ∧ now-last_activity>600` 成立时执行（`test_idle_does_not_unload_inflight`
分别对 `inflight=1` 与 `transition=True` 两个 case 断言跳过）。等待 GPU 的请求不会被
watchdog 打扰。**PASS**

## 10. orphan / fail-safe behavior

### 10.1 orphan llama-server（manager 启动时只读检测）

- 探测 :8012 端口、`llama-server` 进程 cmdline、`gpu.lock` holder；
- **归属可判定**（model 路径 ∈ registry 或 `--port 8012`）→ graceful SIGTERM → 确认端口关闭
  与 VRAM 释放，`orphan="resolved"`；
- **归属不可判定**（真实 `llama-server` 可执行文件但不匹配 registry）→ **不杀、不启动第二个
  backend**，`orphan="unresolved"`，所有加载请求 503 `ORPHAN_UNRESOLVED`（拒绝服务而非蛮干）。

实测（人为制造）：

```
手动启动 llama-server（mistral GGUF, --port 8012）→ GPU 5709 MiB
重启 manager → 日志：
  [llama-mgr] orphan llama-server pid=… belongs to this registry -> graceful terminate
  [llama-mgr] orphan terminated, VRAM released
进程 TERMINATED，8012 关闭，GPU 回 682，status orphan=resolved
```

**Orphan llama-server protection: PASS**

### 10.2 Gateway fail-safe（消除 fail-open）

旧 `LlamaGate`：manager status 不可达 → `busy=false`（**fail-open**，会在 manager 挂掉时
给 Ollama 开并发窗口）。

新行为：status 请求失败 → 立即回退两级本地探测：

1. `gpu.lock` 非阻塞 flock 探测（拿不到 = 有人持有 = busy）；
2. nvidia-smi 计算进程里查找 `llama-server` 可执行进程（>1GB = busy）。

任一命中即 **BUSY**（扣住 Ollama 完成类请求）；status 恢复后打日志回到直接读取。
日志样例：`[gw] llama status unreachable -> fail-safe busy=…`。

`test_gateway_llama_status_fail_safe` 三段断言全过：

```
锁空闲 + 无 llama-server GPU 进程 → busy=False
锁被持有 → busy=True
LLAMA_STATUS 指向死端口（127.0.0.1:1）+ 锁被持有 → 轮询后 LlamaGate 报 busy=True
fallback: lock-held=>busy, free=>not busy, dead-endpoint honored
```

**Gateway manager-down fail-safe: PASS**

## 11. Zrald compatibility

| 项 | 结果 |
|---|---|
| 端口 :8010 | 不变 |
| 无 `model` 字段的旧请求 → 回退 default | 200（`model=zrald-qwen3.8-27b-accuracy`，9.4s 含切换） |
| 未知 `model` 名 → 回退 default | 200（单元回归沿用） |
| `/health` | 200，原字段（status/service/backend_alive/ctx/port/default_model）保留 |
| `/manager/status` | 原字段全保留（backend_alive/backend_pid/lease_held/inflight/idle_timeout/spawn_count/ctx），新增字段仅追加 |

**Zrald compatibility: PASS**

## 12. regression

### 12.1 代码测试（任务书 §22 全部 7 项，服务器真实 GPU 真实 spawn）

```
[PASS] test_gpu_wait_not_503                 (13.6s)  state=WAITING_FOR_GPU blocked_by=image
[PASS] test_gpu_wait_auto_resume             (16.6s)  单次 acquire 自动恢复 14.4s
[PASS] test_atomic_inflight_reservation      (40.6s)  order=[A_reserved, A_done, B_reserved, B_done]
[PASS] test_different_model_switch_waits     (16.3s)  B 排队，A 不被切换
[PASS] test_same_model_concurrent_requests   (4.6s)   inflight=2，无重复 spawn
[PASS] test_idle_does_not_unload_inflight    (4.7s)   inflight=1 与 transition=True 均跳过
[PASS] test_gateway_llama_status_fail_safe   (3.9s)
TOTAL 7 | PASS 7 | FAIL 0
```

### 12.2 E2E 套件

`e2e_queue.py`：**TOTAL 34 | PASS 34 | FAIL 0**（含 §6-§9 全部断言），外加两次反向方向
补测（llama→Image、Image→Ollama）均 PASS。

### 12.3 代表模型回归（§18 范围，未重测全部旧模型）

| 目标 | 结果 |
|---|---|
| llama `qwen3-14b-local` | PASS（E2E C，200 + 正确 model 字段） |
| llama `mistral-7b-instruct-v0.2-local` | PASS（E2E A/B/C 反复 200） |
| llama `zrald-qwen3.8-27b`（default） | PASS（无 model 字段 → 200） |
| Ollama `qwen3:8b` 经 :11434 | PASS（200，`OK`，`think:false`） |
| Ollama `qwen3-embedding:0.6b` 经 :11434 | PASS（200，dim 1024） |
| Image 1024×1024 standard | PASS（60.0s / 58.5s / 63.3s / 74.7s 多轮 200） |
| Ollama 模型数 | 14 完好（未动 tag） |

### 12.4 服务终态（§23）

| 端口 | 状态 |
|---|---|
| 8010 llama-manager | RUNNING（新代码，gpu_wait=900/3.0） |
| 8011 Image | RUNNING（idle，`/unload` 后模型已卸） |
| 8020 WebUI | RUNNING |
| 11434 Gateway | RUNNING（含 fail-safe LlamaGate） |
| 11435 Ollama | loopback（14 模型） |
| 3000 Open WebUI | RUNNING |
| 8000 vLLM | CLOSED |
| 孤儿 llama-server | **无** |
| gpu.lock | **FREE** |
| /api/ps | **empty** |
| GPU | **682 MiB**（回基线） |

**CUDA OOM：NO**（本轮 0 次；最高显存出现在 Image 推理 ~17.6GB，未新增压力）。

### 12.5 超时参数核对（§21）

| 参数 | 值 | 未改 |
|---|---|---|
| llama GPU wait | 900s / 3s | 本轮新设（任务书要求值） |
| llama 模型切换队列 | 900s | 沿用 |
| Gateway hold | 1800s | 未改 |
| Image GPU wait / queue | 900 / 1200 | 未改 |
| idle timeout | 600s | 未改 |

## 13. Git

| 项 | 内容 |
|---|---|
| 修改文件 | `serving/services/llama-manager/llama_manager.py`、`serving/services/llama-manager/test_llama_manager.py`（新增）、`serving/services/ollama/gateway.py`、`reports/`、`coordination/` |
| 未触碰 | models.yaml 模型条目/路径/context、GGUF、Ollama tag、Image、vLLM、CUDA、driver、`/home/yuyong/vllm` |
| commit | `fix: queue llama gpu waits and close model switch race` |
| 禁止项 | 模型/GGUF/logs/tmp/真实IP/PID/secret/local env 均未入 Git；secret scan PASS |
