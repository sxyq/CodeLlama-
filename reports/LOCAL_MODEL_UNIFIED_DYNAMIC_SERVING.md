# LOCAL MODEL UNIFIED DYNAMIC SERVING REPORT

Task ID: LOCAL-MODEL-UNIFIED-DYNAMIC-SERVING-001
Date: 2026-09-28
原则：LOCAL WEIGHTS FIRST（全部使用 /data/vllm 既有权重，零重新下载；原始 Safetensors 未删除/移动/覆盖）
执行机 → SERVER_IP（SSH）；Serving 目录 `/home/syy/ai-serving/`；权重目录 `/data/vllm/`

---

## 1. Local model inventory（实时审计）

`/data/vllm` 目录级清点（11 个文本模型 + Zrald + Image，本轮全部逐一读取 config.json / generation_config.json / tokenizer_config.json / safetensors index）：

| # | 目录 | 架构 | dtype | hidden/layers | 分片 | 目录大小 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | CodeLlama-13b-Instruct-hf | LlamaForCausalLM | bf16 | 5120/40 | 4 | 49G | max_pos 4096 |
| 2 | codellama-7b-instruct-hf | LlamaForCausalLM | bf16 | 4096/32 | 2 | 26G | max_pos 16384 |
| 3 | deepseek-coder-6.7b-instruct | LlamaForCausalLM | bf16 | 4096/32 | 2 | 26G | max_pos 16384 |
| 4 | gemma-2-9b | Gemma2ForCausalLM | **float32** | 3584/42 | 8 | 35G | 无 chat_template |
| 5 | gemma-2-9b-it | Gemma2ForCausalLM | bf16 | 3584/42 | 4 | 18G | max_pos 8192 |
| 6 | gemma-3-12b-it | Gemma3ForConditionalGeneration | bf16 | 3840/48 | 5 | 23G | **vision_config 存在** |
| 7 | Mistral-7B-Instruct-v0.2 | MistralForCausalLM | bf16 | 4096/32 | 3 | 28G | max_pos 32768 |
| 8 | Qwen2.5-Coder-7B-Instruct | Qwen2ForCausalLM | bf16 | 3584/28 | 4 | 15G | max_pos 32768 |
| 9 | Qwen3-14B | Qwen3ForCausalLM | bf16 | 5120/40 | 8 | 28G | max_pos 40960 |
| 10 | Qwen3.5-9B | Qwen3_5ForConditionalGeneration | bf16 | 4096/32 | 4 | 19G | **vision_config 存在**，ctx 声明 262144 |
| 11 | starcoder2-7b | Starcoder2ForCausalLM | bf16 | 4608/32 | 3 | 14G | 无 chat_template |
| — | Zrald-Qwen3.8-27B-v2 | （已有 GGUF） | Q? | — | 1 | 16.5G | `zraldqwen3.8-accuracy.gguf` |
| — | ImageModel/Qwen-Image-2.1 | diffusers | — | — | 29 | — | **NOT_APPLICABLE**（不参与文本统一接入） |

全部模型均有 tokenizer（tokenizer.json / tokenizer.model）与 chat_template（除 gemma-2-9b、starcoder2 两个基座）。

---

## 2. Compatibility matrix

| Model | Architecture | Current Format | Ollama | llama.cpp | vLLM | Recommended Backend |
|---|---|---|---|---|---|---|
| CodeLlama-13b-Instruct-hf | LlamaForCausalLM | HF bf16 | 已有 `codellama:13b-instruct` | 支持 | 支持 | **ALREADY_COVERED_BY_OLLAMA** |
| Qwen2.5-Coder-7B-Instruct | Qwen2ForCausalLM | HF bf16 | 已有 `qwen2.5-coder:7b-instruct` | 支持 | 支持 | **ALREADY_COVERED_BY_OLLAMA** |
| Qwen3.5-9B | Qwen3_5ForConditionalGeneration（多模态） | HF bf16 | 本地导入 **成功**（completion+vision） | conversion 包无 qwen3_5 | transformers 兼容未验证 | **OLLAMA_REGISTERED** |
| Gemma-3-12B-it | Gemma3ForConditionalGeneration（多模态） | HF bf16 | 本地导入 **成功**（completion+vision） | 支持（gemma3） | 未验证 | **OLLAMA_REGISTERED** |
| DeepSeek-Coder-6.7B | LlamaForCausalLM | HF bf16 | 本地导入 **成功** | 支持 | 支持 | **OLLAMA_REGISTERED** |
| codellama-7b-instruct-hf | LlamaForCausalLM | HF bf16 | 本地导入 **成功** | 支持 | 支持 | **OLLAMA_REGISTERED** |
| Qwen3-14B | Qwen3ForCausalLM | HF bf16 | 导入 **失败**（unsupported "Qwen3ForCausalLM"） | 支持（qwen.py） | 支持（历史有 qwen3-14b 类配置） | **LLAMA_CPP_DYNAMIC** |
| Mistral-7B-Instruct-v0.2 | MistralForCausalLM | HF bf16 | 导入 **失败**（unsupported "MistralForCausalLM"） | 支持（mistral.py） | 支持 | **LLAMA_CPP_DYNAMIC** |
| Gemma-2-9B-it | Gemma2ForCausalLM | HF bf16 | 导入 **崩溃**（Ollama daemon panic） | 支持（gemma.py） | 支持 | **LLAMA_CPP_DYNAMIC** |
| Gemma-2-9B | Gemma2ForCausalLM | float32 | 导入 **崩溃**（同上） | 支持 | 支持 | **LLAMA_CPP_DYNAMIC** |
| StarCoder2-7B | Starcoder2ForCausalLM | HF bf16 | 导入 **失败**（unsupported "Starcoder2ForCausalLM"） | 支持（starcoder.py） | 支持 | **LLAMA_CPP_DYNAMIC** |
| Zrald-Qwen3.8-27B-v2 | （已 GGUF） | GGUF | —（原 Zrald 体系） | 支持（在用） | 不适用 | **LLAMA_CPP_DYNAMIC**（registry default） |
| Qwen-Image-2.1 | diffusers | safetensors | 不适用 | 不适用 | 不适用 | **NOT_APPLICABLE** |

**模型最终分类**：ALREADY_COVERED_BY_OLLAMA ×2、OLLAMA_REGISTERED ×4、LLAMA_CPP_DYNAMIC ×6（含 Zrald）、VLLM_DYNAMIC ×0、UNSUPPORTED ×0、NOT_APPLICABLE ×1（Image）。

---

## 3. Ollama import results（LEVEL 1）

导入方式：临时 Modelfile `FROM /data/vllm/<MODEL_DIR>`（权重不复制到临时目录），tag 均带 `-local` 后缀，不覆盖官方 tag。**必须 `OLLAMA_HOST=127.0.0.1:11435`**（默认 11434 是网关，`/api/blobs` 上传会被重置——本轮实测 `connection reset by peer`，此为关键运维事实）。

逐个串行：CREATE → SHOW → 网关 API SMOKE → keep_alive=0 → `/api/ps` 清空 → GPU 基线 → 下一个。

| 模型 | tag | CREATE | 真实错误 / 结果 | 最终 |
|---|---|---|---|---|
| Qwen3.5-9B | `qwen3.5:9b-local` | PASS（3m10s，F16 打包） | family=qwen35、9.7B、caps `completion+vision`；网关 chat 200、vision 200 | **OLLAMA_REGISTERED_PASS** |
| Qwen3-14B | `qwen3:14b-local` | **FAIL** | `unsupported architecture "Qwen3ForCausalLM"`（create.go:335） | OLLAMA_IMPORT_FAIL |
| Gemma-3-12B-it | `gemma3:12b-it-local` | PASS（219.6s） | caps `completion+vision`；chat 200 `OK`、vision 200 | **OLLAMA_REGISTERED_PASS** |
| Gemma-2-9B-it | `gemma2:9b-it-local` | **FAIL** | Ollama daemon **panic**：`interface conversion: interface {} is string, not map[string]interface {}`（11:31:18 / 11:33:22 两次），systemd `Restart=always` 3s 重启，manifest 未写成 | OLLAMA_IMPORT_FAIL |
| Gemma-2-9B | `gemma2:9b-local` | **FAIL** | 同上 panic | OLLAMA_IMPORT_FAIL |
| Mistral-7B | `mistral:7b-instruct-v0.2-local` | **FAIL** | `unsupported architecture "MistralForCausalLM"` | OLLAMA_IMPORT_FAIL |
| DeepSeek-Coder-6.7B | `deepseek-coder:6.7b-instruct-local` | PASS（167.3s） | chat 200 `OK`；code smoke 输出正确 `add` 函数 | **OLLAMA_REGISTERED_PASS** |
| CodeLlama-7B | `codellama:7b-instruct-local` | PASS（166.7s） | chat 200 `OK`；code smoke 输出正确 `add` 函数 | **OLLAMA_REGISTERED_PASS** |
| StarCoder2-7B | `starcoder2:7b-local` | **FAIL** | `unsupported architecture "Starcoder2ForCausalLM"` | OLLAMA_IMPORT_FAIL |
| CodeLlama-13B | — | 跳过 | ALREADY_COVERED → `codellama:13b-instruct` | ALREADY_COVERED |
| Qwen2.5-Coder-7B | — | 跳过 | ALREADY_COVERED → `qwen2.5-coder:7b-instruct` | ALREADY_COVERED |

- 失败的 create 未写入 manifest，**无残留 local tag 需要删除**（事后核对：`/api/tags` = 14 个 = 原 10 + 新 4，原 10 个名称/大小逐一完好）。
- Ollama 0.20.7 内置 safetensors 转换器**不依赖系统 transformers**（系统 python3 无该包也能转换）。
- daemon 两次 panic 均发生于 gemma2 转换，`Restart=always` 自动恢复，对原 10 模型与 Image 无影响（Image 全程 idle）。

### 3.1 新模型验证细节（全部经网关 SERVER_IP:11434）

| 模型 | 输出 | eval | load_duration | 释放 | peak VRAM |
|---|---|---|---|---|---|
| qwen3.5:9b-local chat | `OK`（含模板噪声） | 16 | 44.75s | ≤1s | — |
| qwen3.5:9b-local vision（真实图片 base64） | `A red apple on a white background.`（**准确**） | 21 | — | ≤1s | 30,511 MiB |
| gemma3:12b-it-local chat | `OK` | 2 | — | ≤1s | 33,427 MiB |
| gemma3:12b-it-local vision | `single, ripe red apple with a stem…`（**准确**） | 20 | — | ≤1s | 33,469 MiB |
| deepseek-coder:6.7b-instruct-local | `OK`；code：`def add(a, b): return a + b` | 3 / 64 | — | ≤1s | 21,981 MiB |
| codellama:7b-instruct-local | `OK`；code：`def add(a, b): return a + b` | 3 / 139 | — | ≤1s | 21,893 MiB |

---

## 4. llama.cpp compatibility

- 运行时：`/home/syy/ai-serving/runtime/llama.cpp`，commit `e85e15c`（2026-09），`build/bin/` 内 `llama-cli` / `llama-server` / `llama-quantize` 均已编译（含 `libggml-cuda.so`，CUDA 可用）。
- 转换脚本架构注册于 `conversion/` 包（qwen.py、llama.py、mistral.py、gemma.py、starcoder.py 等 100+ 模块）——**五个 LEVEL 2 目标架构全部被识别**，与 Ollama 内置转换器的覆盖面不同。
- 转换依赖：`torch`、`gguf`（脚本自带 `gguf-py`）、`numpy`、`transformers`、**`sentencepiece`**。系统 python3 无这些包；服务器 PyPI 直连与国内镜像均超时（`pypi.org` / `mirrors.aliyun.com` / `pypi.tuna.tsinghua.edu.cn` 全部不可达），故：
  - 复用已有 `env/image` venv（torch 2.14.0、transformers 5.17.0、numpy 2.5.3 齐备）；
  - 缺失的 `sentencepiece` 从执行机下载 `sentencepiece-0.2.0-cp312-manylinux` wheel 后 scp 安装（1.3 MB，`--no-index` 离线装）；
  - **未升级/改动全局 Python、CUDA、driver**。
- 磁盘前提：转换前 `df` 可用 **2.0T**（>500GB 红线），中间文件峰值估算约 95G（<200GB 红线）→ 允许转换。

---

## 5. GGUF conversions

输出目录 `/data/vllm/ConvertedGGUF/<MODEL_NAME>/`（本轮新建；原模型目录未写入任何文件）。策略：**Q4_K_M**（先 `--outtype f16` 再 `llama-quantize Q4_K_M`）。

| 模型 | F16 大小 | Q4_K_M 大小 | 转换 | 量化 |
|---|---|---|---|---|
| Qwen3-14B | 29,543,423,936 B | **9,001,753,536 B** | 2m03s | 92.9s |
| Mistral-7B-Instruct-v0.2 | 14,484,733,248 B | **4,368,440,640 B** | 1m24s | 51.8s |
| gemma-2-9b-it | 18,490,680,544 B | **5,761,058,016 B** | 1m40s | 64.4s |
| gemma-2-9b | 18,490,679,584 B | **5,761,057,056 B** | 2m22s | 50.1s |
| starcoder2-7b | 14,352,924,000 B | **4,461,280,608 B** | 1m10s | 50.4s |

### 5.1 完整性（每个 Q4 文件）

- **GGUF magic**：5/5 `b"GGUF"` ✓
- **file_type = 15**（= Q4_K_M）5/5 ✓
- **张量数与 HF index 一致**：mistral 291、qwen3 443、gemma2 464×2、starcoder2 515 ✓
- **llama-cli 极短 smoke（`-st -n 8`）5/5 rc=0 且有真实生成**：

| 文件 | 生成样例 | 速度（prompt/gen） |
|---|---|---|
| qwen3-14b-Q4_K_M | `[Start thinking]`（Qwen3 思考开头，8 token 用尽） | — |
| mistral-7b-instruct-v0.2-Q4_K_M | `The capital city of France is Paris.` | 408 / 118 t/s |
| gemma2-9b-it-Q4_K_M | 正常生成 | 200 / 78 t/s |
| gemma-2-9b-Q4_K_M | `Paris` | 417 / 79 t/s |
| starcoder2-7b-Q4_K_M | `The assistant of France is…`（基座续写，符合预期） | 763 / 97 t/s |

- **中间文件清理（§38）**：Q4 全部通过 header + llama-cli + manager 推理三重验证后，删除本轮 5 个 F16 中间文件，回收 **89G**；原始 Safetensors 完好（抽查 Qwen3-14B 28G、Qwen3.5-9B 19G、Mistral 28G 与审计一致）。
- **context_length / embedding_length 直读**：转换器写入的 metadata 由 llama-cli 实际加载成功间接证明；manager 侧 spawn 时以 registry 显式 `-c` 覆盖（40960/32768/8192/8192/16384）。

---

## 6. General llama.cpp manager architecture

将 Zrald 专用 manager（`zrald_lease_manager.py`，279 行、硬编码单模型）泛化为 registry 驱动的通用 manager：

```
/home/syy/ai-serving/
├── services/llama-manager/llama_manager.py      # 泛化实现
├── configs/llama-manager/models.yaml            # 模型 registry（参数不散落代码）
├── state/llama-manager/                         # 状态目录
├── logs/llama-manager/                          # manager + 每模型 llama-server 日志
```

- **registry**（models.yaml）：`default_model` + `backend_port` + `idle_timeout` + 6 个模型条目（path / context / alias / gpu_layers），绝对路径不进 Python 代码。
- **生命周期**：`REQUEST → model select → GPU admission（ollama ps 大模型 + nvidia-smi >1GB 双确认）→ flock gpu.lock → spawn llama-server → load → inference → idle 600s → SIGTERM → VRAM release`。
- **模型切换（§18）**：同模型 warm 直通；换模型时若 `inflight>0` 则 **QUEUE**（Condition 等待推理结束，绝不 kill 在跑任务）；空闲则 stop A（**租约跨切换保持**，不给 Image 插入窗口）→ spawn B。
- **端点（§19）**：`GET /health`、`GET /manager/status`、`GET /v1/models`、`POST /v1/chat/completions`（+ `POST` 任意路径代理），OpenAI `model` 字段选模型，转发前改写 body 的 `model` 为该模型 alias。
- **GPU lock（§20）**：继续用唯一 `state/gpu.lock`（flock），未建第二套互斥。

### 6.1 Zrald 向后兼容（§15，硬要求）

| 核对项 | 结果 |
|---|---|
| 端口 8010 不变 | ✓ |
| `GET /health` 200（含原 `status`/`backend_alive`/`ctx`/`port` 字段，新增字段仅追加） | ✓ |
| `GET /manager/status` 原字段全保留（`backend_alive`/`backend_pid`/`lease_held`/`inflight`/`idle_timeout`/`spawn_count`/`ctx`） | ✓ |
| **不带 `model` 字段的旧客户端请求 → 回退 default（zrald）→ 200 `OK`** | ✓（8.3s 冷载） |
| **未知 `model` 名（历史遗留值）→ 回退 default → 200 `OK`** | ✓（1.0s warm） |
| Zrald 从"唯一模型"变为 registry 中一项 | ✓（`zrald-qwen3.8-27b` = default） |

**Zrald backward compatibility: PASS**

---

## 7. Dynamic vLLM manager architecture

**结论：VLLM_DYNAMIC = NOT_NEEDED。**

- 11 个本地文本模型全部归入 Ollama（6）或 llama.cpp（6，含 Zrald）或已覆盖（2），没有出现"Ollama 不支持 ∧ llama.cpp 不支持 ∧ 仅 vLLM 支持"的模型。
- 因此未创建 `/home/syy/ai-serving/services/vllm-manager/`，未改动 `/home/yuyong/vllm/*.yaml`（只读参考），`:8000` 保持 **CLOSED**，无运行中的 vllm 进程。
- 服务器侧 `vllm` 未安装于系统 python（`ModuleNotFoundError`），历史运行环境在 `/home/yuyong/vllm/.venv`（本账号无执行权限）——本轮无需触碰。
- 若未来出现必须 vLLM 的模型，设计已预留：`REQUEST → MODEL SELECT → QUEUE → gpu.lock → spawn vllm serve（127.0.0.1:8100+ 内部口）→ /health → inference → idle 600s → terminate → 释放`，对外 Manager 与 backend 分端口。

---

## 8. GPU scheduler integration（§21-22）

**发现的新竞态**：原网关只感知 Image，llama.cpp 推理中 Ollama 仍可加载 30B → OOM 风险。

**修复**：网关新增 `LlamaGate`（轮询 `GATEWAY_LLAMA_STATUS`，默认 `http://127.0.0.1:8010/manager/status`，取 `lease_held`）。GPU 完成类端点放行条件改为 **Image idle ∧ llama-manager 无租约**，任一占用则扣住（超时仍 1800s → 503，新增 `LLAMA_GPU_BUSY` 错误码）。`BYPASS_RELEASE`（Image 资源等待时放行 keep_alive=0 释放请求）语义保留不变。

四个 workload 的共享状态闭环：

```
                     ┌── gpu.lock (flock, 唯一) ──┐
Image :8011 ─────────┤                            ├──── llama-manager :8010
  · VRAM 预算准入     │   Image 占用 → llama 拿锁失败│      · 拿锁前查 ollama/nvidia
  · 拿锁失败 → 等待   │   llama 占锁 → Image 等待   │      · 持锁 = 对外 busy 信号
                     └────────────┬───────────────┘
                                  │
Ollama :11434 网关 ─── 等待条件 = Image busy ∨ llama lease_held（本轮新增）
```

实测闭环（三场景，全部真实调用）：

| 场景 | 过程 | 结果 |
|---|---|---|
| **A. llama 持锁 → Ollama 等** | mistral 持锁时经网关发 `/api/embed` → 5s 未返回（被扣）→ SIGTERM llama-server（watchdog 释放锁）→ embed **200，总 13.8s** | 网关日志 `HELD POST /api/embed 12.0s (image/llama slot busy)` ✓ |
| **B. llama 持锁 → Image 等 → 释放 → 自动开始** | mistral 持锁发 Image 1024×1024 → 8s 后 `state=waiting_for_gpu`（queue waiting=1）→ 释放 llama → **Image 200 / 84.9s** | 无需人工干预 ✓ |
| **C. Image 运行 → 其它等待** | Image 推理中：llama 请求 → **503 GPU_BUSY**；网关 embed → 被扣 5s 未返回 → Image 完成 **200/65.5s** → embed 自动 **200/63.8s** | 严格串行 ✓ |

**GPU strict serialization: PASS**（OLLAMA / LLAMA_CPP / IMAGE 同时最多一个高显存 workload RUNNING；本轮 STRICT SERIAL，未引入 co-residency）

---

## 9. Per-model serving result（§44 总表）

| Model | Original Format | Ollama | llama.cpp | vLLM | Final Backend | API Model Name | Peak VRAM | Status |
|---|---|---|---|---|---|---|---|---|
| CodeLlama-13b-Instruct-hf | HF bf16 | 已有 | 支持 | 支持 | Ollama | `codellama:13b-instruct` | （既有，本轮未重测） | **ALREADY_COVERED** |
| Qwen2.5-Coder-7B-Instruct | HF bf16 | 已有 | 支持 | 支持 | Ollama | `qwen2.5-coder:7b-instruct` | （既有，本轮未重测） | **ALREADY_COVERED** |
| Qwen3.5-9B | HF bf16 | **成功** | 不支持 | — | **Ollama :11434** | `qwen3.5:9b-local` | 30,511（vision） | **PASS** |
| Gemma-3-12B-it | HF bf16 | **成功** | 支持 | — | **Ollama :11434** | `gemma3:12b-it-local` | 33,469（vision） | **PASS** |
| DeepSeek-Coder-6.7B | HF bf16 | **成功** | 支持 | — | **Ollama :11434** | `deepseek-coder:6.7b-instruct-local` | 21,981 | **PASS**（code smoke ✓） |
| codellama-7b-instruct-hf | HF bf16 | **成功** | 支持 | — | **Ollama :11434** | `codellama:7b-instruct-local` | 21,893 | **PASS**（code smoke ✓） |
| Qwen3-14B | HF bf16 | 失败 | **成功** | 支持 | **llama.cpp :8010** | `qwen3-14b-local` | 18,321 | **PASS** |
| Mistral-7B-Instruct-v0.2 | HF bf16 | 失败 | **成功** | 支持 | **llama.cpp :8010** | `mistral-7b-instruct-v0.2-local` | 9,321 | **PASS** |
| Gemma-2-9B-it | HF bf16 | 崩溃 | **成功** | 支持 | **llama.cpp :8010** | `gemma2-9b-it-local` | 9,291 | **PASS** |
| Gemma-2-9B | HF float32 | 崩溃 | **成功** | 支持 | **llama.cpp :8010** | `gemma2-9b-local` | 9,295 | **PASS** |
| StarCoder2-7B | HF bf16 | 失败 | **成功** | 支持 | **llama.cpp :8010** | `starcoder2-7b-local` | 6,351 | **PASS** |
| Zrald-Qwen3.8-27B-v2 | GGUF | — | **成功** | — | **llama.cpp :8010（default）** | `zrald-qwen3.8-27b` | 18,489 | **PASS** |
| Qwen-Image-2.1 | diffusers | — | — | — | Image :8011 | — | — | **NOT_APPLICABLE** |

无 UNSUPPORTED；无 VLLM_DYNAMIC。

### 9.1 llama.cpp manager 逐模型实测（经 :8010，OpenAI 协议）

| 请求 | HTTP | wall（含冷载/切换） | 输出 | 备注 |
|---|---|---|---|---|
| `zrald-qwen3.8-27b`（首个请求） | 200 | 12.9s | `OK` | spawn_count=1 |
| `qwen3-14b-local`（切换） | 200 | 6.2s | 48 token 全为 thinking | 切换正常 |
| `mistral-7b-instruct-v0.2-local` | 200 | 2.8s | `OK. I'm here to help…` | |
| `gemma2-9b-it-local` | 200 | 5.3s | `OK` | |
| `gemma2-9b-local` | 200 | 4.2s | 基座续写（符合预期） | |
| `starcoder2-7b-local` | 200 | 3.8s | 基座续写（符合预期） | |
| `qwen3-14b-local` + `enable_thinking:false` | 200 | 5.0s | **`OK`** | 思考关闭后可见输出 |
| 无 `model` 字段（旧 Zrald 客户端） | 200 | 8.3s | `OK` | 回退 default zrald |
| 未知 `model` 名 | 200 | 1.0s | `OK` | 回退 default，warm |

最终状态：`spawn_count=10, switch_count=9`，切换全程 `lease_held=true` 未中断（切换不释放租约）。

**模型切换排队（§18）实测**：A=qwen3-14b 发 900-token 长任务（13.5s 完成）→ 1.5s 后并发 B=mistral 请求 → **B 等待 14.8s 后 200**（等 A 推理完成 + 切换完成，A 未被 kill）→ `FINAL model=mistral`。**QUEUE 行为 PASS**。

---

## 10. Cold/warm/VRAM measurements（§33）

- **cold load**（模型加载到首 token）：llama.cpp 侧含于 wall（zrald 12.9s、qwen3-14b 6.2s、mistral 2.8s…）；Ollama 侧 `load_duration` 见 §3.1（qwen3.5 44.75s，其余 3-5s）。
- **warm inference**：同模型第二次请求（zrald warm 1.0s vs cold 8.3s；Ollama 侧 `eval_count=2` 即时返回）。
- **peak VRAM**：逐模型轮询 `nvidia-smi`，数值见 §9 表；全局峰值 **33,469 MiB**（gemma3 vision），远低于 47,000 MiB 的 HIGH_VRAM 阈值 → **无 HIGH_VRAM 标记**，未做任何压力测试。
- **idle unload / VRAM release**：`idle_timeout=600s` watchdog 实测 **631s 确认卸载**，
  GPU 9,321 → 682 MiB、`lease_held=false`（见 §12.4）；Ollama 单请求后 `keep_alive=0` 释放路径
  逐模型验证（每次 ≤1s 清空，GPU 回落 682-696 MiB）。
- 本轮 **CUDA OOM = 0 次**。

---

## 11. Disk usage

| 时点 | `/` 可用 | ConvertedGGUF | 说明 |
|---|---|---|---|
| 开始 | 2.0T 可用（62%） | 不存在 | /data/vllm 478G |
| 转换峰值 | 1.1T 可用（67%） | 117G（5×F16 + 5×Q4） | 远低于 200GB 中间峰值红线、500GB 可用红线 |
| F16 清理后 | 1.2T 可用（64%） | **28G**（5×Q4_K_M） | 回收 89G |

Ollama 侧新增 blob（本轮成功导入 4 个模型的 F16 打包，约 69G）含于 `/` 用量。原始权重目录未变（抽查 28G/19G/28G 与 §1 一致）。

**Disk before：2.0T 可用 / Disk after：1.2T 可用**（净增占用 = 5 个 Q4 28G + Ollama 4 模型 blob ~69G ≈ 97G，全部为本轮新产物，原权重零变化）。

---

## 12. Image/Ollama regression

### 12.1 Image 回归（§35，三场景）

| 场景 | 结果 |
|---|---|
| Image 1024×1024 正常生成 | **PASS**（200 / 84.9s / 65.5s，b64 完整 1.9-2.0MB，effective_steps=24） |
| llama.cpp running → Image WAIT → 释放 → 自动开始 | **PASS**（`waiting_for_gpu` → llama 释放 → 200，无需人工清理） |
| Image running → llama/Ollama 请求 WAIT → 完成后自动开始 | **PASS**（llama 503 GPU_BUSY；embed 扣 63.8s 后自动 200） |

### 12.2 Ollama 回归（§36，代表模型）

| 项 | 结果 |
|---|---|
| `qwen3:8b` 经网关 :11434 | **PASS**（200，`OK`，eval=2，3.7s，`think:false`） |
| `qwen3-embedding:0.6b` 经网关 :11434 | **PASS**（200，dim=1024，1.8s） |
| runner 释放 | PASS（≤1s `/api/ps` 清空，GPU 回落 696 MiB） |
| 原 10 模型完整 | **PASS**（`/api/tags` = 14 = 原 10 + 新 4，原 10 名称逐一完好，未删/未改名/未覆盖/未重量化） |

### 12.3 其它端点巡检

8011 health 200、8010 health 200、8010 /v1/models 200、8020 200、3000 200、11434 tags 200、11435 仅回环。

### 12.4 idle unload 实测（600s）

加载 `mistral-7b-instruct-v0.2-local`（T0 `lease_held=true`、GPU 9,321 MiB）后不再发任何请求：

```
t+30s … t+601s   lease=True  alive=True  gpu=9321   （驻留期）
t+631s           lease=False alive=False gpu=682     （watchdog SIGTERM → 租约释放 → VRAM 回落）
IDLE_UNLOAD CONFIRMED at 631s
```

- `idle_timeout=600s` + watchdog 5s 轮询 + 30s 采样精度 → 631s 确认，符合预期（600s 阈值 + ≤30s 观测延迟）
- **VRAM release PASS**：9,321 → **682 MiB**（回到全局基线）
- 租约同步释放，`lease_held=false` 后网关对 Ollama 恢复放行
- 补记：本项前两次尝试因 admission **正确拒绝**瞬时资源占用（GPU_BUSY：Ollama embed runner 未释放 / 锁被占）返回 503，资源释放后第三次通过——503 是准入生效的证据，非服务故障

---

## 13. Unsupported models

**无。** 所有 11 个本地模型均获得合适 backend（含 2 个已覆盖跳过、1 个 Image 不适用）。

Ollama 导入失败的 5 个模型全部经 llama.cpp 路线成功，失败原因如实记录：
1. `unsupported architecture "Qwen3ForCausalLM"`（Ollama 0.20.7 内置转换器）
2. `unsupported architecture "MistralForCausalLM"`
3. `unsupported architecture "Starcoder2ForCausalLM"`
4. gemma2 ×2：Ollama daemon Go panic（`interface conversion: string → map`），systemd 自动重启

---

## 14. Final topology

```
                        GPU Scheduler（gpu.lock 唯一 + 网关双条件 + VRAM 预算）
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
   Ollama :11434                  llama.cpp :8010                 （vLLM :8000）
   （gateway → :11435）         （llama-manager，:8012 后端）          CLOSED / NOT_NEEDED
        │                               │
  14 个注册模型                    models.yaml registry（6）
  ├ Chat/Gen（原6保留）             ├ zrald-qwen3.8-27b   [default]
  ├ qwen3.5:9b-local      ←新       ├ qwen3-14b-local             ←新
  ├ gemma3:12b-it-local   ←新       ├ mistral-7b-instruct-v0.2-local ←新
  ├ deepseek-coder:6.7b-instruct-local ←新   ├ gemma2-9b-it-local  ←新
  ├ codellama:7b-instruct-local     ←新       ├ gemma2-9b-local     ←新
  └ Embedding/Reranker（原3保留）            └ starcoder2-7b-local  ←新
        │                               │
        └───────────────┬───────────────┘
                        │
                  Qwen-Image :8011
              （VRAM 预算准入 + gpu.lock）
```

**STRICT SERIAL GPU EXECUTION**：任意时刻最多一个高显存 workload RUNNING；Image↔Ollama↔llama.cpp 三方互斥闭环实测通过。

---

## 15. Git

分阶段提交（白名单逐文件 add，禁 add -A）：

| 阶段 | message | 内容 |
|---|---|---|
| 1 | `feat: generalize llama cpp model manager` | `serving/services/llama-manager/`、`serving/configs/llama-manager/`、`serving/services/ollama/gateway.py`（LlamaGate 调度集成） |
| 2 | `docs: record local model serving matrix` | 本报告 + `coordination/` |

禁止项核对：模型权重 / GGUF / Ollama blobs / logs / tmp / 真实 IP / PID / secret / local env / node_modules 均未入 Git；secret scan PASS。

---

## 16. 停机条件核对（§41）

| 停机条件 | 实际 |
|---|---|
| 现有 Ollama 10 模型丢失 | 未发生（14 = 10 + 4，原 10 完好） |
| 11434 Gateway 异常 | 未发生（升级后业务全 200） |
| Image 调度破坏 | 未发生（三场景回归全过） |
| Zrald 无法调用 | 未发生（8010 兼容路径全过） |
| gpu.lock 死锁 | 未发生（每次释放后 `lease_held=false`） |
| 不可恢复 CUDA OOM | 未发生（0 次） |
| 磁盘可用 <500GB | 未发生（最低 1.1T） |
| 需要升级 driver/CUDA | 未需要 |
| 需要删除原模型 | 未发生（仅删本轮 F16 中间文件，§38 授权） |
| 需要修改 /home/yuyong/vllm 原配置 | 未发生（只读参考） |

## 17. Blocking issues

**NONE**
