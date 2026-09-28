# OLLAMA ALL-MODELS PRODUCTION SMOKE REPORT

Task ID: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001
Date: 2026-09-28
性质：只读 smoke（未 pull / rm / create 任何模型，未改 Gateway、Image、systemd、CUDA、driver，未启动 vLLM）
入口：SERVER_IP:11434（Ollama GPU Gateway）；11435 仅用于读取 backend metadata 与调试

---

## 1. Summary（任务书 §16 字段）

| Field | Value |
|---|---|
| Network | **PASS**（SSH :22 / SERVER_IP:11434 / SERVER_IP:8011 三项全通） |
| Ports | 11434=Gateway、11435=backend 仅回环、8010/8011/8020/3000 开、8000 CLOSED，全部符合预期 |
| Current Ollama model count | **10**（与预期清单名称完全一致） |
| All chat models callable | **YES**（6/6 HTTP 200） |
| All embedding models callable | **YES**（3/3 HTTP 200，维度符合预期） |
| Reranker | **ENDPOINT_UNAVAILABLE**（MODEL_PRESENT，`/api/rerank` 网关与 backend 均 404） |
| All runners released | **YES**（每个模型完成后 `/api/ps` ≤1s 清空，GPU 回落基线） |
| Gateway path | **PASS**（全部请求出现在 gateway.log，源为 SERVER_IP） |
| Qwen3.5-9B weights | **PRESENT**（`QWEN35_WEIGHT_PRESENT = YES`，19G，只读核验） |
| vLLM | **STOPPED**（:8000 CLOSED，无运行进程） |
| Changes made | **NONE** |
| Blocking issues | **NONE** |

---

## 2. 可达性与端口

### 2.1 可达性（任务书 §1）

| 目标 | 结果 |
|---|---|
| SSH :22 | OPEN |
| SERVER_IP:11434 | OPEN |
| SERVER_IP:8011 | OPEN |

Network: **PASS**（未触发 NETWORK_BLOCKED 分支）

### 2.2 端口（`ss -lntp` 实测）

| 端口 | 期望 | 实测 | 进程 |
|---|---|---|---|
| 11434 | Ollama Gateway | LISTEN `0.0.0.0:11434` | python3 pid=3028816 |
| 11435 | Ollama backend，仅 127.0.0.1 | LISTEN **`127.0.0.1:11435`** | ollama |
| 8010 | Zrald | LISTEN `0.0.0.0:8010` | python3 pid=1896989 |
| 8011 | Image API | LISTEN `0.0.0.0:8011` | python pid=2931285 |
| 8020 | Image WebUI | LISTEN `0.0.0.0:8020` | python3 pid=2080490 |
| 3000 | Open WebUI | LISTEN `0.0.0.0:3000` | — |
| 8000 | CLOSED | **无监听** | 无 |

拓扑确认：外部流量只经 11434 网关，backend 11435 不对外。

---

## 3. 当前模型清单

`ollama list` 与 `GET http://127.0.0.1:11435/api/tags` 双读，均返回 **10** 个，与预期完全一致（无增、无缺、无改名）：

| 类别 | 模型 |
|---|---|
| Chat / Generation | qwen2.5-coder:7b-instruct、qwen2.5-coder:14b-instruct、qwen3:8b、qwen3-coder:30b、codellama:13b-instruct、deepseek-r1:7b |
| Embedding | qwen3-embedding:0.6b、qwen3-embedding:8b、nomic-embed-text:latest |
| Reranker | linux6200/bge-reranker-v2-m3:latest |

---

## 4. 最终验收表（全部经 SERVER_IP:11434）

| Model | Type | Endpoint | HTTP | Output/Dim | Peak VRAM | Released | Result |
|---|---|---|---|---|---|---|---|
| qwen2.5-coder:7b-instruct | Chat | POST /api/chat | 200 | `OK`（eval_count=2，load 3.48s，total 3.53s，wall 3.5s） | 7,379 MiB | YES | **PASS** |
| qwen2.5-coder:14b-instruct | Chat | POST /api/chat | 200 | `OK`（eval_count=2，load 4.87s，total 4.94s，wall 4.9s） | 15,683 MiB | YES | **PASS** |
| qwen3:8b | Chat | POST /api/chat | 200 | `OK`（`think:false`；eval_count=2，load 3.32s，wall 3.4s） | 11,633 MiB | YES | **PASS** |
| qwen3-coder:30b | Chat | POST /api/chat | 200 | `OK`（eval_count=2，load 9.20s，total 9.30s，wall 9.3s） | 43,963 MiB | YES | **PASS** |
| codellama:13b-instruct | Chat | POST /api/chat | 200 | `OK`（eval_count=2，load 3.67s，wall 3.7s） | 20,951 MiB | YES | **PASS** |
| deepseek-r1:7b | Chat | POST /api/chat | 200 | 可见回答（thinking 后 `done_reason=stop`，eval_count=408，wall 7.8s） | 12,789 MiB | YES | **PASS** |
| qwen3-embedding:0.6b | Embedding | POST /api/embed | 200 | **dim 1024**，finite，11 token，wall 1.8s | 6,807 MiB | YES | **PASS** |
| qwen3-embedding:8b | Embedding | POST /api/embed | 200 | **dim 4096**，finite，11 token，wall 3.5s | 15,177 MiB | YES | **PASS** |
| nomic-embed-text:latest | Embedding | POST /api/embed | 200 | **dim 768**，finite，12 token，wall 3.9s | 1,491 MiB | YES | **PASS** |
| linux6200/bge-reranker-v2-m3 | Reranker | POST /api/rerank | **404** | — | — | — | **ENDPOINT_UNAVAILABLE** |

维度与预期对照：0.6b=1024 ✅、8b=4096 ✅、nomic=768 ✅（全部与任务书预期一致，记录的是真实返回值）。

### 4.1 Chat 测试参数与 thinking 说明

统一请求：`stream=false`、`keep_alive=0`、`temperature=0`、prompt `Reply with exactly: OK`。

- **qwen3:8b**：首轮 `num_predict=16` 时 thinking 吃满预算，`done_reason=length`、可见 content 为空——按任务书要求未据此判坏。补测用请求体顶层 `"think": false` 后得到字面 `OK`（eval_count=2，`done_reason=stop`），模型健康。`/no_think` 文本写法在该模型上未生效，`think:false` 字段是有效路径。
- **deepseek-r1:7b**：thinking 不可关闭，`num_predict=16/128` 均停在思考中；放宽到 **512** 后完整生成并 `done_reason=stop`（eval_count=408），可见回答正常输出。模型健康。
- 其余 4 个模型首轮即返回字面 `OK`。

### 4.2 Reranker（重点防误报）

- 模型**仍存在**：`linux6200/bge-reranker-v2-m3:latest`（1.2 GB，F16）在 `ollama list` 与 `/api/tags` 中均在列 → **MODEL_PRESENT**
- 标准端点探测：`POST /api/rerank`（网关与 backend 各一次）均返回 **`404 page not found`** → **STANDARD_RERANK_ENDPOINT_UNAVAILABLE**
- 网关日志中该条记录为 `POST /api/rerank ok 0.00s`，这里的 `ok` 只表示请求被透传并拿到响应，不代表模型推理成功；实际响应是 404，因此**不记为 MODEL_INFERENCE_PASS**
- 未做任何绕过或改造（改 Gateway / 加端点均在禁止范围内）

---

## 5. 串行与释放

严格串行：一次只加载一个模型 → 请求完成 → `keep_alive=0` → 轮询 `/api/ps` 清空 → 再测下一个。

- 全部 10 次调用后 `/api/ps` 均在 **≤1.0s** 内清空
- 每次释放后 GPU 均回落 **682 MiB**（与起始基线一致）
- 测试起始 GPU：682 MiB / free 47,858 MiB；结束 GPU：682 MiB，`/api/ps` 空
- 未出现并发加载多个模型的情况

---

## 6. Gateway 调度与 Image 状态

- 全部 chat/embed/rerank 请求目标地址为 `http://SERVER_IP:11434`，脚本读取本机 LAN 地址构造 URL，未以 11435 作为 PASS 依据
- gateway.log 中可见本轮请求（源 IP 为 SERVER_IP），例如：

```
[gw] 10:30:22 SERVER_IP:59810 POST /api/chat ok 9.30s waited=0.0s
[gw] 10:33:01 KEEP_ALIVE_INJECT POST /api/embed -> 0
[gw] 10:33:05 SERVER_IP:59644 POST /api/embed ok 3.52s waited=0.0s
```

- 测试全程 Image `/status.scheduler` = `state=idle, blocked_by=none, image_running=false`，队列 running/pending/waiting_for_gpu 全 0；**未触碰 Image/Ollama 严格串行调度**，未发生扣单或互等

---

## 7. Qwen3.5-9B 只读核验

```
QWEN35_WEIGHT_PRESENT = YES
```

`ls -lah /data/vllm/Qwen3.5-9B`（**只读**，未部署、未转换、未启动）：

- 目录存在，合计 **19G**，含 4 个 safetensors 分片（5.0G + 5.0G + 5.1G + 3.1G）+ `config.json` + tokenizer 等
- `config.json`：

| 字段 | 值 |
|---|---|
| architectures | `Qwen3_5ForConditionalGeneration` |
| model_type | `qwen3_5` |
| dtype | **bfloat16**（`text_config.dtype`；顶层无 torch_dtype） |
| num_hidden_layers | **32**（`text_config`） |
| hidden_size | **4096**（`text_config`） |
| 附加 | `vision_config` 存在（hidden_size 1152），多模态结构；vocab_size 248320 |

权重仅为磁盘上的 Hugging Face safetensors，**未进入 Ollama 清单，本轮也未做任何处理**。

---

## 8. vLLM 状态

- `:8000` **CLOSED**（`ss` 无监听）
- 进程检索：无任何 vllm 运行进程；tmux session `vllm` 仍存在，但其 pane 当前命令为 `bash`，**里面没有跑 vLLM**
- 结论：**vLLM 当前不是这些模型的 serving backend**——本轮 10 个模型全部由 Ollama（11434 网关 → 11435 backend）提供服务
- 未启动 vLLM（禁止事项遵守）

---

## 9. 禁止事项遵守情况

未执行：`ollama pull` / `ollama rm` / `ollama create`、模型下载、GGUF 转换、启动 vLLM、修改 Gateway、修改 systemd、修改 Image、修改 Zrald、修改 CUDA、修改 driver、处理 Qwen3.5-9B。

**Changes made: NONE**（本轮唯一产出为本报告与协调文件更新）

---

## 10. Blocking issues

**NONE**
