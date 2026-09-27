# OLLAMA QWEN3-EMBEDDING-0.6B VERIFY & DEPLOY REPORT

Task ID: OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001
Date: 2026-09-27
Services: SERVER_IP:11434（Ollama GPU Gateway） → 127.0.0.1:11435（Ollama backend） → RTX A6000

---

## 1. Summary（任务书 §19 字段）

| Field | Value |
|---|---|
| Official model | Qwen/Qwen3-Embedding-0.6B |
| Ollama model | qwen3-embedding:0.6b |
| Existing model found | **YES** |
| Deployment action | **REUSED_EXISTING_MODEL** |
| Architecture | qwen3（`general.architecture=qwen3`，capabilities=`["embedding"]`，pooling_type=3） |
| Quantization | **Q8_0**（`general.file_type=7`，format=gguf） |
| Disk size | 639,150,858 B（639 MB），blob `sha256-06507c7b…c3e439`，model id `ac6da0dfba84` |
| Context | **32768** |
| Embedding dimension | **1024** |
| English embedding | **PASS** |
| Chinese embedding | **PASS** |
| Semantic similarity smoke | **PASS**（sim(A,B)=0.845444 > sim(A,C)=0.354812） |
| Gateway path | **PASS**（SERVER_IP:11434） |
| keep_alive=0 | **PASS**（网关 `KEEP_ALIVE_INJECT … -> 0`） |
| Runner release | **PASS**（请求完成后 ≤1s `/api/ps` 清空） |
| Peak VRAM | 6,807 MiB（GPU 总用量峰值；其中模型进程 6,120 MiB） |
| Image after embedding | **PASS**（1024×1024 → 200，59.3s） |
| 8B model preserved | **YES** |
| Blocking issues | **NONE** |

语义表述（按任务书 §6）：本模型为 **Official Qwen3-Embedding-0.6B architecture/model family, served via Ollama packaging**，非与 Hugging Face 权重 bit-for-bit identical（未做权重逐位比对）；Ollama 侧实际量化为 Q8_0，如实记录。

---

## 2. 官方模型基线

| 项 | 值 |
|---|---|
| Hugging Face | Qwen/Qwen3-Embedding-0.6B |
| 类型 | Text Embedding（非 chat model） |
| 参数规模 | 约 0.6B / 实测 metadata 595,776,512（595.78M） |
| 最高维度 | 1024 |
| Context | 32K（实测 32768） |
| 能力 | 多语言 embedding、语义检索、RAG、代码检索、聚类/相似度 |

---

## 3. 第一阶段：现有模型核验（VERIFY FIRST）

先查 `ollama list` 与 backend `GET /api/tags`，确认模型**已存在**，因此未执行任何 `ollama pull`。

```
NAME                   ID              SIZE      MODIFIED
qwen3-embedding:0.6b   ac6da0dfba84    639 MB    5 months ago
qwen3-embedding:8b     64b933495768    4.7 GB    5 months ago
```

`POST /api/show {"name":"qwen3-embedding:0.6b"}`（backend 11435 读取元数据）：

| 元数据键 | 值 | 任务书核对项 |
|---|---|---|
| `general.architecture` | `qwen3` | architecture = qwen3 ✅ |
| `qwen3.pooling_type` | `3` | pooling 为 embedding 池化（capabilities 含 `embedding`）✅ |
| `qwen3.context_length` | `32768` | context ≈ 32768 ✅ |
| `qwen3.embedding_length` | `1024` | embedding length = 1024 ✅ |
| `general.parameter_count` | `595776512` | ≈ 0.6B / 595.8M ✅ |
| `general.file_type` | `7` → Q8_0 | quantization 记录 ✅ |
| `capabilities` | `["embedding"]` | embedding 专用 ✅ |
| 张量样例 | `token_embd.weight [1024, 151669]`、`output_norm.weight [1024]` | 输出维度 1024 ✅ |
| Modelfile FROM | `…/blobs/sha256-06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` | 本地权重，无重复拷贝 ✅ |

**结论：Existing model found = YES → Deployment action = REUSED_EXISTING_MODEL（DO NOT PULL AGAIN / DO NOT DUPLICATE MODEL）。** 未产生新的下载、未新增权重副本，模型仍由 Ollama 自管于 `/usr/share/ollama/.ollama`，未复制到 `~/ai-serving/` 或 `/data/vllm/`。

---

## 4. API 验证（经 SERVER_IP:11434 Gateway）

所有业务调用均以 `http://SERVER_IP:11434` 发起（不以 11435 作为验收地址），无新增端口、无新增独立 embedding 服务、未改 Gateway 调度逻辑。

### 4.1 English embedding

```
POST /api/embed  {"model":"qwen3-embedding:0.6b",
                  "input":"The quick brown fox jumps over the lazy dog."}
→ HTTP 200，dim=1024，全部值为有限数值（math.isfinite 逐元素通过），11 token，4.58s（含首载）
```

**English embedding: PASS**

### 4.2 Chinese embedding

```
POST /api/embed  {"input":"人工智能正在改变软件开发方式。"}
→ HTTP 200，dim=1024，1.81s
```

**Chinese embedding: PASS**

### 4.3 语义相似度 smoke test（三组，非大型 benchmark）

| 组 | 文本 | HTTP | dim |
|---|---|---|---|
| A | 机器学习模型训练 | 200 | 1024 |
| B | 训练人工智能模型 | 200 | 1024 |
| C | 今天天气很好 | 200 | 1024 |

Cosine similarity（真实实测）：

```
sim(A,B) = 0.845444
sim(A,C) = 0.354812
sim(B,C) = 0.372505
```

`sim(A,B) > sim(A,C)`（0.8454 > 0.3548）成立。

**Semantic similarity smoke: PASS**

### 4.4 长文本能力 smoke

- metadata context = **32768**（未塞满 32K，按任务书不做压力测试）
- 实测输入 8,000 字符（`prompt_eval_count = 1779` token）→ HTTP 200，dim=1024，有限数值，2.06s
- 接口稳定，无截断/超时/报错

**Long-text smoke: PASS**

---

## 5. Gateway keep_alive 行为（关键验收项）

网关对 embedding 缺省注入 `keep_alive=0`（客户端未显式指定时）。

| 验收点 | 结果 | 证据 |
|---|---|---|
| 调用 → 200 | PASS | §4 全部 200 |
| 请求完成 → runner 自动释放 | PASS | 完成后轮询 `/api/ps`：**1.0s 内清空**，`PS_FINAL=[]` |
| 默认注入生效 | PASS | `logs/ollama/gateway.log` 出现 `KEEP_ALIVE_INJECT POST /api/embed -> 0`（该日志累计 612 条注入记录） |
| 不长期占 GPU 阻塞 Image | PASS | 释放后 GPU 回到 682 MiB，Image 随后立即生成成功（§7） |

日志样本（本轮测试窗口）：

```
[gw] 19:39:51 SERVER_IP:32886 POST /api/embed ok 1.80s waited=0.0s
[gw] 19:40:06 KEEP_ALIVE_INJECT POST /api/embed -> 0
[gw] 19:40:10 CLIENT_IP_REDACTED:51342 POST /api/embed ok 3.94s waited=0.0s   ← 真实 LAN 客户端同期正常
```

**keep_alive=0: PASS　Runner release: PASS**

---

## 6. 显存记录

测量方式：默认路径（无显式 keep_alive）与受控持住（显式 `keep_alive=60` 读数后再 `keep_alive=0` 释放）各测一轮；只记录真实值，不做极限测试。

| 阶段 | GPU used (MiB) | 说明 |
|---|---|---|
| 请求前基线 | **682**（free 47,858） | Image idle、`/api/ps` 空 |
| 加载期间（持住读数） | **6,807** | 模型进程 PID 3798979 占 **6,120 MiB**（权重 + 32K 上下文 KV 预分配 + CUDA context）；另有常驻 266 + 378 MiB 进程 |
| 默认请求路径峰值 | **6,811** | 轮询采样峰值 |
| Release 后 | **682**（free 47,858） | 与基线一致，1s 内回落 |

**Peak VRAM: 6,807 MiB（GPU 总用量）／模型进程 6,120 MiB**

---

## 7. 调度回归（Image → embed → Image）

严格互斥链路未被本轮改动，实测顺序回归：

1. Image `/status`：`state=idle`、`blocked_by=none`、queue 全 0，GPU 682 MiB，`/api/ps` 空
2. 经网关调用 `qwen3-embedding:0.6b` → **200**（dim 1024，1.80s），期间 GPU 到 6,807、`/api/ps` 短暂出现该模型
3. **无需人工清理 Ollama**：轮询 `/api/ps` 立即为空（runner 自动释放），GPU 回落 682 MiB
4. 紧接发 `POST /v1/images/generations`（1024×1024，标准 24 步）→ **HTTP 200**，59.3s，`effective_steps=24`，`queue_wait=0.0s`，b64 输出 1,660,288 字符
5. 生成期间 GPU 峰值 17,602 MiB；完成后 Image 回到 `state=idle`，GPU 698 MiB，`/api/ps` 仍为空

**Image after embedding: PASS**

---

## 8. 现有 8B 模型与模型列表

`qwen3-embedding:8b`（4.7 GB，id `64b933495768`）未删除、未覆盖、未改名；`ollama list` 复查仍在。

**8B model preserved: YES**

Ollama 模型体系（报告/项目状态归入 OLLAMA）：

```
OLLAMA
├── Chat / Generation
│   ├── qwen2.5-coder:7b-instruct
│   ├── qwen2.5-coder:14b-instruct
│   ├── qwen3:8b
│   ├── qwen3-coder:30b
│   ├── codellama:13b-instruct
│   └── deepseek-r1:7b
│
├── Embedding
│   ├── qwen3-embedding:0.6b     ← 本轮核验复用（Q8_0 / 32K / 1024）
│   ├── qwen3-embedding:8b
│   └── nomic-embed-text
│
└── Reranker
    └── linux6200/bge-reranker-v2-m3
```

业务按需选择 0.6b（轻量、释放快）或 8b（更强表征），两者并存互不影响。

---

## 9. 拓扑与未改动项

| 项 | 状态 |
|---|---|
| 对外入口 | `SERVER_IP:11434` 网关（`ss`：`0.0.0.0:11434` python3 pid=3028816） |
| Backend | `127.0.0.1:11435` 仅回环（`ss` 实证），LAN 客户端不直连 11435 |
| 端口 | 无新增（8010/8011/8020/11434/11435/3000 开，8000 vLLM 仍 CLOSED） |
| Gateway 调度逻辑 | **未修改**（纯调用方） |
| Image / Zrald / gpu.lock / queue / CUDA / driver / Open WebUI | **未修改** |
| Ollama systemd / 模型增删 | **未修改**（本轮无 pull、无 rm、无 rename） |
| 权重位置 | 仍由 Ollama 自管于 `/usr/share/ollama/.ollama`，无重复副本 |
| 业务代码改动 | **无**（仅新增本报告与协调文件更新） |

---

## 10. Blocking issues

**NONE**

未尽事项（非阻塞）：未做 Hugging Face 权重与 Ollama blob 的逐位比对（任务书未要求，且不作 bit-for-bit 主张）；未做 32K 满上下文压测（任务书明确不需要）。

---

## 11. Git

本轮未改任何业务代码/配置，仅新增 `reports/OLLAMA_QWEN3_EMBEDDING_06B.md` 与协调文件更新。模型权重、Ollama blobs、logs、tmp、真实 IP、secret 一律不入 Git。
