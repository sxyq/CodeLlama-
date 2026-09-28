# Last Agent Handoff

Updated At: 2026-09-28  
Last Task ID: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW

## Completed（本轮：全模型生产 smoke，只读验收）

- **网络恢复**：本机曾切换到 `10.225.129.x` 网段导致到服务器（`10.16.15.x`）无路由、全端口超时约 1 小时；
  恢复后 22/11434/8011 全通，任务按 §1 正常执行（未走 NETWORK_BLOCKED 分支）
- **端口全符合预期**：11434 网关（0.0.0.0，python3 pid=3028816）/ 11435 仅回环 / 8010 / 8011 /
  8020 / 3000 开 / **8000 CLOSED**
- **模型清单 10 个**（`ollama list` 与 `/api/tags` 双读），名称与预期完全一致，零增删
- **10/10 逐一实测，全部经 SERVER_IP:11434，严格串行**（每模型 `keep_alive=0` → `/api/ps` ≤1s 清空 → 下一个）：
  - chat 6/6 **PASS**：qwen2.5-coder:7b/14b、qwen3:8b、qwen3-coder:30b、codellama:13b、deepseek-r1:7b
    均 HTTP 200、可见输出、`done_reason=stop`；峰值 VRAM 7.4G/15.7G/11.6G/**44.0G**/21.0G/12.8G
  - embedding 3/3 **PASS**：0.6b=**1024**、8b=**4096**、nomic=**768**，全部 finite
  - reranker：**MODEL_PRESENT + STANDARD_RERANK_ENDPOINT_UNAVAILABLE**（`/api/rerank` 网关与 backend
    均 `404 page not found`；网关日志的 `ok 0.00s` 只是透传成功，不是推理 PASS——任务书要求防误报）
- **thinking 模型要点**：qwen3:8b 需请求体顶层 `"think": false` 才出字面 OK（`/no_think` 文本写法无效）；
  deepseek-r1:7b thinking 不可关，`num_predict=512` 才完整输出（16/128 会停在思考中）
- **调度零影响**：Image 全程 `state=idle` 队列全 0，网关无扣单，严格串行未破坏
- **Qwen3.5-9B 只读**：`QWEN35_WEIGHT_PRESENT=YES`（`/data/vllm/Qwen3.5-9B` 19G、4 个 safetensors 分片；
  config = `Qwen3_5ForConditionalGeneration`、`text_config` dtype **bfloat16**、num_hidden_layers **32**、
  hidden_size **4096**、含 vision_config 多模态）；未部署、未转换、未启动
- **vLLM**：8000 CLOSED，无 vllm 进程（tmux session `vllm` 存在但 pane=bash）；**不是当前 serving backend**
- **Changes made: NONE**；报告 `reports/OLLAMA_ALL_MODELS_PRODUCTION_SMOKE.md`

## Previous Task: OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001（要点保留）

- `qwen3-embedding:0.6b` 为 **REUSED_EXISTING_MODEL**（Q8_0 / ctx32768 / dim1024 / 595.78M），
  未 pull 未重复权重；语义表述 = Official Qwen3-Embedding-0.6B architecture/model family,
  served via Ollama packaging（不作 bit-for-bit 主张）
- keep_alive 缺省注入 `KEEP_ALIVE_INJECT POST /api/embed -> 0` 实证，runner ≤1s 释放
- 报告 `reports/OLLAMA_QWEN3_EMBEDDING_06B.md`，commit `ddb62ff`

## 更早任务要点（仍有效）

- **Ollama 入口收口**：unit `OLLAMA_HOST=127.0.0.1:11435`，公网口 `serving/services/ollama/gateway.py`
  占 `0.0.0.0:11434`；LAN 客户端零配置穿网关
- **严格互斥**：Image admission = `/api/ps` runner 空 ∧ gpu.lock ∧ VRAM 预算+3072MiB；
  网关 Image 占槽时扣完成类端点，image 仅资源等待时放行 `keep_alive=0`（BYPASS_RELEASE）
- 队列：queue timeout 1200 ≥ GPU wait 900；TTL 1800/300；idle 600
- 前端 Image 请求超时常量 `IMAGE_REQUEST_TIMEOUT_MS = 1_200_000`（600 用例全绿）

## Status Flags

| Flag | Value |
|---|---|
| NETWORK | PASS（曾断连约 1h，已恢复） |
| OLLAMA MODELS | 10（6 chat / 3 embed / 1 reranker），与预期一致 |
| CHAT / EMBED | 6/6 PASS、3/3 PASS（dim 1024·4096·768） |
| RERANKER | MODEL_PRESENT + ENDPOINT_UNAVAILABLE（404） |
| RUNNERS RELEASED | YES（全部 ≤1s，GPU 回落 682 MiB） |
| GATEWAY PATH | PASS（全部 11434，11435 仅读 metadata） |
| IMAGE | 全程 idle，严格串行未受影响 |
| QWEN35_WEIGHT_PRESENT | YES（只读，19G） |
| VLLM | STOPPED（8000 CLOSED） |
| CUDA OOM（本轮） | NO |
| CHANGES | NONE |
| GIT | 见最终回复 |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动） |
| 8011 Image | RUNNING（idle，unloaded） |
| 8020 WebUI | RUNNING |
| 11434 | 网关 → 127.0.0.1:11435 |
| 11435 | Ollama backend（回环，10 模型完整） |
| 3000 OWUI | RUNNING |
| 8000 vLLM | CLOSED |
| GPU | 682 MiB / free 47,858（全模型释放后），gpu.lock FREE |

## 环境要点（下轮必读）

- **外部一律打 11434（网关）**；11435 只读 metadata；网关日志 `~/ai-serving/logs/ollama/gateway.log`
  （`HELD` / `BYPASS_RELEASE` / `KEEP_ALIVE_INJECT`，含对端 IP；`ok` 只代表透传成功，不代表业务成功）
- **释放模型用 API** `keep_alive:0`；`ollama stop` CLI 本服务器 404 空转，勿用
- **reasoning 模型调用**：qwen3 用顶层 `think:false`（`/no_think` 文本无效）；deepseek-r1 给足
  `num_predict`（512 可完整输出）
- **本机网络**：Mac 曾在 `10.225.129.x` 网段时到服务器无路由 → 全端口超时；连不上先查
  `netstat -rn` 有无到 `10.16.x` 的路由，别急着判服务挂了
- **sudo 模式**：密码仅经当次 ssh heredoc **首行** stdin，永不落盘；`sudo -n` 无免密
- **pkill/pgrep 自匹配**：同命令行含模式明文时括号技巧失效——取 PID 直杀，分三次 SSH
- 服务器测试：Node 于 `env/node-v22.23.3-linux-x64/bin`；本机 rollup 坏，生成/测试在服务器跑；
  本机 curl 加 `--noproxy '*'`；zsh 变量不自动分词
- 真实 IP 永不入 Git（报告用 `SERVER_IP` / `CLIENT_IP_REDACTED`）

## Exact Next Action

WAIT FOR COMMANDER REVIEW

## Do Not

- 未授权不动 Gateway/拓扑/Image/Zrald/gpu.lock/queue/CUDA/driver/Open WebUI/systemd
- 不 `ollama pull` / `rm` / `create`，不转换 GGUF，不启动 vLLM，不处理 Qwen3.5-9B（需新授权）
- 不为测试反复制造 CUDA OOM
- 模型权重/blobs/logs/tmp/真实IP/secret 不入 Git；禁 git add -A
