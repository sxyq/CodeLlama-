# Last Agent Handoff

Updated At: 2026-09-28  
Last Task ID: LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW

## Completed（本轮：llama-manager 排队 + 并发 race 修复）

- **问题 A → GPU 等待**：`503 GPU_BUSY` 快速失败改为 `WAITING_FOR_GPU` 同请求自动继续。
  参数 `LLAMA_MANAGER_GPU_WAIT_TIMEOUT=900` / `LLAMA_MANAGER_GPU_WAIT_POLL=3`。
  等待条件：`gpu.lock` 被占（holder 含 image → blocked_by=image）/ Ollama runner>1GB →
  `ollama` / nvidia 其他>1GB → `gpu_memory`；超时才 503 `GPU_WAIT_TIMEOUT`。
  **排队期不持锁**；**切换期租约跨切换保持**（先停旧 backend 释放 VRAM，再持锁等排空）。
  `/status` 新增 `state / waiting_for_gpu / blocked_by`（无 PID/IP），状态机
  QUEUED→WAITING_FOR_GPU→LOADING→RUNNING→IDLE→UNLOADED。
- **问题 B → 原子 reservation**：selection + 切换判定 + `inflight++` 合并进**同一 `with cond`
  临界区**；全局单一 `threading.Condition`（不再混用 mu+cond）；`transition` 标志保证同时
  仅一个线程等待/加载/切换。HTTP：`acquire_model_for_request() → proxy → finally release`。
- **deterministic race 测试**：`TEST_HOOKS["after_selection_before_reserve"]` 把 A 卡在
  选择与预留之间，B 必须阻塞（旧实现该窗口可复现错误切换）；实测
  `order=[A_reserved, A_done, B_reserved, B_done]`。
- **测试 7/7 PASS**（服务器真 GPU 真 spawn）：not_503 / auto_resume / atomic_inflight /
  different_model_switch_waits / same_model_concurrent / idle_does_not_unload /
  gateway_llama_status_fail_safe。
- **E2E 34/34 PASS**：
  - A：Image running → llama `WAITING_FOR_GPU/blocked_by=image`（非 503）→ Image 200 →
    （600s idle-unload 释放锁）→ **同一请求 662.7s 自动 200**
  - B：qwen3:8b `keep_alive:-1` 驻留 → `blocked_by=ollama` → 释放 → **14.6s 自动 200**
  - C：qwen3-14b 长推理中 mistral 排队 → A 响应 `model=qwen3-14b-local`、
    B `model=mistral-…`（各自 backend，绝不串）
  - 同模型并发：200×2、`spawn_count` 不变、`inflight=2`
  - 反向补测：llama 持锁 → Image `waiting_for_gpu` → 74.7s 自动 200；
    llama 持锁 → 网关扣 embed → 释放 → 15.8s 自动 200；Image running → embed 扣 61.7s 后自动
  - **§20 六方向互斥全 PASS，无一需人工重试**
- **Gateway fail-safe**：`LlamaGate` 在 status 不可达时回退
  （1）`gpu.lock` 非阻塞 flock 探测 （2）nvidia-smi 查 `llama-server` 计算进程，
  任一命中即 BUSY——消除原 fail-open；日志 `llama status unreachable -> fail-safe busy=…`。
- **Orphan 保护（§16）**：启动时探测 :8012 + `llama-server` 进程 + 锁 holder；
  归属可判定（model ∈ registry）→ graceful terminate + VRAM 确认，`orphan=resolved`
  （人为制造实测通过）；不可判定 → **不杀不载**，请求 503 `ORPHAN_UNRESOLVED`。
- **idle 规约**：仅 `inflight==0 ∧ transition==false ∧ waiting==false ∧ >600s` 才卸载
  （两个 case 单测断言跳过）。
- **Zrald 兼容**：:8010、无/未知 model → default、`/health` `/manager/status` 原字段全保留。
- **回归**：qwen3-14b / mistral / zrald default、`qwen3:8b` 200 `OK`、`embed0.6b` 200 dim1024、
  Image 1024×1024 多轮 200、Ollama 14 模型完好、Image `POST /unload` 后锁 FREE。
- **终态**：8010/8011/8020/11434/11435/3000 OPEN、8000 CLOSED、无孤儿、
  gpu.lock FREE、`/api/ps` empty、GPU **682 MiB**；本轮 CUDA OOM **0**。
- 报告：`reports/LLAMA_MANAGER_QUEUE_AND_CONCURRENCY_FIX.md`（13 节）
- 修改面：`serving/services/llama-manager/llama_manager.py`（重写同步核心）、
  `test_llama_manager.py`（新增）、`serving/services/ollama/gateway.py`（fail-safe）；
  **模型/GGUF/models.yaml 路径与 context/Image/vLLM/CUDA 零改动**

## Previous Task: LOCAL-MODEL-UNIFIED-DYNAMIC-SERVING-001（要点保留）

- 三级 Serving：Ollama 14 模型（原10 + `qwen3.5:9b-local`/`gemma3:12b-it-local`/
  `deepseek-coder:6.7b-instruct-local`/`codellama:7b-instruct-local`）；llama.cpp registry
  6 模型（qwen3-14b / mistral / gemma2-it / gemma2 / starcoder2 / zrald default）；
  VLLM_DYNAMIC=NOT_NEEDED
- `ollama create` 必须 `OLLAMA_HOST=127.0.0.1:11435`（网关不支持 blob 上传）
- 服务器 PyPI 不通 → 依赖从执行机下载 wheel scp + `pip --no-index`
- GGUF 在 `/data/vllm/ConvertedGGUF/`（5×Q4_K_M 共 28G，F16 已清）

## Status Flags

| Flag | Value |
|---|---|
| GPU WAIT | 900s / 3s；超时 503 GPU_WAIT_TIMEOUT（此前为 503 GPU_BUSY 快速失败） |
| RESERVATION | 原子（单 Condition；transition 互斥） |
| FAIL-SAFE | 网关 status 失效 → 锁 + nvidia llama-server 探测，busy 优先 |
| ORPHAN | 启动检测：可判定清理 / 不可判定拒载 |
| 六方向互斥 | 全实测 PASS |
| 测试 / E2E | 7/7 与 34/34 |
| CUDA OOM | NO |
| ZRALD :8010 | 兼容 PASS（default 回退） |
| GIT | 见最终回复 |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 | llama-manager（新代码，gpu_wait 900/3） |
| 8011 | Image RUNNING（idle，模型已 /unload） |
| 8020 | WebUI RUNNING |
| 11434 | 网关（fail-safe LlamaGate）→ 11435 |
| 11435 | Ollama backend 回环，14 模型 |
| 3000 | OWUI RUNNING |
| 8000 | CLOSED |
| GPU / 锁 | 682 MiB；gpu.lock FREE；ps empty；无孤儿 |

## 环境要点（下轮必读）

- **Image 的 gpu.lock 随 idle 600s 卸载才释放**（完成任务≠放锁）——llama 900s 等待覆盖该窗口；
  想立即释放可 `POST :8011/unload`（推理中 409）
- llama-manager 排队期间**不持锁**，`blocked_by` 每 3s 刷新；等锁时 status 保持可读
  （状态更新走短临界区，spawn/等待在临界区外）
- `TEST_HOOKS` 与 `LLAMA_MANAGER_GPU_WAIT_*` 仅测试/配置用；测试跑法：**停生产 manager →
  `python3 test_llama_manager.py` → 重启**（测试会真 spawn 与真抢锁）
- 网关 fail-safe 日志关键词：`llama status unreachable -> fail-safe busy=…`
- `ollama create` 必须 `OLLAMA_HOST=127.0.0.1:11435`；释放模型用 API `keep_alive:0`
  （`ollama stop` CLI 404 勿用）；qwen3 系推理用 `think:false`
- 服务器 PyPI 不通：依赖从执行机下 wheel scp + `pip --no-index`；转换用 `env/image` venv
- 历史沿用：sudo 密码仅当次 heredoc 首行；pkill 自匹配用 PID 直杀；curl `--noproxy '*'`；
  Node 于 `env/node-v22.23.3-linux-x64/bin`；真实 IP 永不入 Git
- **修 python 类结构**：把方法抽成模块函数时注意别让类在中途被顶格 def 截断
  （本轮 `manager_status` 抽取曾致 `do_GET` 变嵌套函数 → 501，已修）
- E2E 脚本在服务器 `~/ai-serving/tmp/`（临时，跑完即删），本地副本 `/tmp/e2e/`

## Exact Next Action

WAIT FOR COMMANDER REVIEW（Git 提交见最终回复）

## Do Not

- 未授权不动：模型/GGUF/models.yaml 条目/Image/vLLM/systemd/CUDA/driver/网络/Open WebUI
- 网关 fail-safe 与 manager 等待是同一闭环两侧，勿单独关掉
- 测试图/tmp/logs/GGUF/blob/真实IP/secret 不入 Git；禁 git add -A
