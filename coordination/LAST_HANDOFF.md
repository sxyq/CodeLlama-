# Last Agent Handoff

Updated At: 2026-09-28  
Last Task ID: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001  
Status: **NETWORK_BLOCKED** — 冒烟未执行（服务器不可达，任务书 §1 STOP）

## 本轮：全模型生产冒烟（NETWORK_BLOCKED）

- **可达性探测**：执行机 → SERVER_IP 的 22 / 11434 / 8011 全部 timeout；4 轮含 20s 间隔重试 +
  此前十余分钟 5 次以上，均失败 → 判定 **NETWORK_BLOCKED**，按 §1 STOP，**未猜任何服务状态**
- **原因（本机侧）**：执行机已切到 `10.225.129.0/24`（en0，网关/ARP 正常），路由表**无到
  `10.16.15.x` 的路由**，流量走默认网关后丢弃；最后一次成功 SSH 是 2026-09-27 上一任务
- **未执行**：端口核验、模型清单、6 chat / 3 embedding / reranker 调用、串行释放、显存记录、
  gateway log、Qwen3.5-9B 只读、vLLM 只读——全部未做，报告无任何 PASS 行
- **零操作**：服务器未连接，未执行任何服务端命令；本地仅新增
  `reports/OLLAMA_ALL_MODELS_PRODUCTION_SMOKE.md`（内容=NETWORK_BLOCKED）+ 协调文件
- **下一步**：恢复网络后从 §1 重跑，结果写入同一份报告

## Previous Task: OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001（要点保留）

- **VERIFY FIRST 结论**：`ollama list` / `GET 127.0.0.1:11435/api/tags` 已存在 `qwen3-embedding:0.6b`
  （id `ac6da0dfba84`，639 MB，modified 2026-04-17）→ **REUSED_EXISTING_MODEL**，未 pull、未重复下载、
  未新增权重副本（仍在 `/usr/share/ollama/.ollama`，未复制到 `~/ai-serving/` 或 `/data/vllm/`）
- **元数据核对**（`/api/show`）：architecture=**qwen3**、capabilities=`[embedding]`、pooling_type=3、
  context=**32768**、embedding_length=**1024**、parameter_count=**595,776,512**、file_type=7→**Q8_0**、
  blob `sha256-06507c7b…c3e439`；语义表述=Official Qwen3-Embedding-0.6B architecture/model family,
  served via Ollama packaging（**未做**权重逐位比对，不作 bit-for-bit 主张）
- **API 验证（全部经 SERVER_IP:11434 网关，不以 11435 验收）**：
  - 英 `The quick brown fox…` → 200 / dim **1024** / 有限数值 / 11 token
  - 中 `人工智能正在改变软件开发方式。` → 200 / dim 1024
  - 相似度：A `机器学习模型训练`、B `训练人工智能模型`、C `今天天气很好`
    → cos(A,B)=**0.845444** > cos(A,C)=**0.354812**（B-C=0.372505）PASS
  - 长文本 8000 字符（1779 token）→ 200 / dim 1024 / 2.06s（ctx 仅核对 metadata，未塞满 32K）
- **keep_alive 关键验收**：网关日志实证 `KEEP_ALIVE_INJECT POST /api/embed -> 0`（累计 612 条）；
  请求完成后 `/api/ps` **≤1s** 清空，GPU 回落基线 → 不会长期占 GPU 阻塞 Image
- **显存**：基线 **682** MiB → 持住读数 **6807** MiB（模型进程 **6120** MiB）→ 释放 **682** MiB
- **调度回归**：Image idle → embed 200 → runner 自动释放 → Image 1024×1024 **200 / 59.3s**
  （effective_steps=24，峰值 17602 MiB，完成后 idle、ps 空）；**无需人工清理 Ollama**
- **8B 保留**：`qwen3-embedding:8b`（4.7 GB）未删/未覆盖/未改名，与 0.6b 并存
- **零改动**：Gateway、11434/11435 拓扑、Image、Zrald、gpu.lock、queue、CUDA、driver、Open WebUI、
  Ollama systemd 与模型列表均未修改；业务代码零改动，仅新增报告与协调文件
- 报告：`reports/OLLAMA_QWEN3_EMBEDDING_06B.md`

## Earlier Task: IMAGE-WEBUI-TIMEOUT-ALIGN-001（要点保留）

- 唯一常量 `IMAGE_REQUEST_TIMEOUT_MS = 1_200_000`（`webui/image-platform/upstream/src/lib/imageApiShared.ts`）
  经 `imageRequestTimeoutMs()` 接入 `openaiCompatibleImageApi.ts` 三处 abort 与 `store.ts` 看门狗；
  `gen-preset-config.py` timeout 600→1200；新增 `imageTimeout.test.ts`
- npm test **36 文件 / 600 用例全绿**；build 通过，dist 含 `12e5`；preset-config timeout=1200
- commit `abab48a fix: align image webui request timeout`、`8fd916e docs: update handoff after timeout align`
- 生成/测试均在服务器跑（本机 node_modules rollup 签名损坏）；Node 于 `env/node-v22.23.3-linux-x64/bin`

## Earliest Task: GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001（要点保留）

- **Ollama 入口收口**：unit `OLLAMA_HOST=127.0.0.1:11435`，公网口由 `serving/services/ollama/gateway.py`
  占 `0.0.0.0:11434`（本轮实测 pid=3028816）；LAN 客户端零配置穿网关
- **严格互斥**：Image admission = `/api/ps` runner 空（512MiB 阈）∧ gpu.lock ∧ VRAM 预算 +3072MiB；
  网关在 Image 占槽时扣完成类端点，image 仅资源等待时放行 `keep_alive=0`（BYPASS_RELEASE）
- 队列：queue timeout **1200** ≥ GPU wait **900**（3s 轮询）；TTL 1800/300、idle 600
- 前端 Image 请求超时 **1200s**（常量唯一真源，profile timeout 与之对齐）

## Status Flags

| Flag | Value |
|---|---|
| EMBED_06B | REUSED_EXISTING_MODEL（Q8_0 / 32768 / 1024） |
| EMBED_8B | PRESERVED |
| OLLAMA TOPOLOGY | gateway 0.0.0.0:11434 → backend 127.0.0.1:11435（未动） |
| KEEP_ALIVE DEFAULT | 0（网关注入），runner ≤1s 释放 |
| IMAGE↔OLLAMA STRICT | 未改，回归 PASS（embed→释放→图 200） |
| QUEUE/GPU WAIT TIMEOUT | 1200 / 900 |
| CUDA OOM（本轮） | NO |
| WEBUI_8020 | RUNNING（超时对齐版） |
| VLLM | 8000 CLOSED |
| GIT | 见最终回复（仅 reports + coordination） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动） |
| 8011 Image | RUNNING（idle，unloaded，queue1200 / wait900） |
| 8020 WebUI | RUNNING（超时对齐版） |
| 11434 | 网关 → 127.0.0.1:11435 |
| 11435 | Ollama backend（回环，10 模型完整） |
| 3000 OWUI | RUNNING |
| 8000 vLLM | CLOSED |
| GPU | ~682 MiB（embed 全释放后），gpu.lock FREE |

## 环境要点（下轮必读）

- **外部一律打 11434（网关）**；查后端直连 11435；网关日志 `~/ai-serving/logs/ollama/gateway.log`
  （`HELD` / `BYPASS_RELEASE` / `KEEP_ALIVE_INJECT` 关键词，含对端 IP）；journal 源IP 为网关回环
- **释放 Ollama 模型用 API** `POST /api/embed|chat {"keep_alive":0}`；`ollama stop` CLI 在本服务器
  `/api/stop` 404 空转，勿用；embed 缺省注入 keep_alive=0（显式值保留，-1=永久驻留）
- **sudo 模式**：密码仅经当次 ssh heredoc **首行** stdin（`IFS= read -r PW; … sudo -S -v`），永不落盘；
  `sudo -n` 无免密；heredoc 首行漏写密码会空转
- **pkill/pgrep 自匹配**：同命令行含模式明文时括号技巧也失效——杀进程/建脚本/pgrep 分三次 SSH，优先 PID 直杀
- 服务器测试流程：scp → cp 进 `~/ai-serving/webui/image-platform/upstream/…` →
  `export PATH=$HOME/ai-serving/env/node-v22.23.3-linux-x64/bin:$PATH; cd upstream && npm test`；
  对外 dist 用 `bash scripts/build_webui.sh`
- 本机 Mac 代理拦内网：curl 加 `--noproxy '*'`；zsh 变量不自动分词、`====` 触发 = 展开
- IAB filechooser 报 `ambiguous routed session` → 画廊「编辑输出」等价路径；受控 number input
  用三击+Backspace 清值
- 历史教训：`urllib HTTPError` 用 `e.read()` 而非 `e.body`；nvidia-smi CSV 需去逗号再 `int()`
- 真实 IP 永不入 Git（报告用 `SERVER_IP` / `CLIENT_IP_REDACTED`）

## Exact Next Action

恢复执行机到 SERVER_IP 网段的网络 → 从任务书 §1 重跑 OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001
（端口 → 清单 → 6 chat → 3 embedding → reranker → 串行释放 → 显存 → gateway log →
Qwen3.5-9B 只读 → vLLM 只读），结果写入 `reports/OLLAMA_ALL_MODELS_PRODUCTION_SMOKE.md`

## Do Not

- 未授权不动 Gateway/11434·11435 拓扑/Image/Zrald/gpu.lock/queue/CUDA/driver/Open WebUI/systemd
- 不删、不覆盖、不改名任何已有模型（含 0.6b 与 8b）
- 不为测试反复制造 CUDA OOM；不恢复 vLLM（需授权）
- 模型权重/blobs/logs/tmp/真实IP/secret 不入 Git；禁 git add -A
- 冒烟任务禁止：ollama pull/rm/create、下载模型、转换 GGUF、启动 vLLM、改 Gateway/systemd/Image/Zrald/CUDA/driver
- 网络不可达时**不得编造服务状态或 PASS**，只能写 NETWORK_BLOCKED
