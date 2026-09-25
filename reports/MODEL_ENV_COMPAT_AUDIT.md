# Model Environment Compatibility Audit

任务编号：MODEL-ENV-COMPAT-AUDIT-001
时间：2026-09-25 16:05–16:20 CST
性质：只读诊断（未停止/重启/下载/安装任何东西）
服务器：SERVER_IP_REDACTED（主机名 SERVER_HOSTNAME_REDACTED，用户 syy）

---

## 1. Hardware

### 服务器基础

| 项 | 值 |
|---|---|
| date | 2026-09-25 16:05 CST |
| OS kernel | Linux 6.8.0-87-generic x86_64 (Ubuntu) |
| CPU cores | 80（lscpu/nproc） |
| RAM total / used / available | 376 GiB / 21 GiB / 355 GiB（无 swap） |
| Disk total / free | 3.5T / 1.4T（60% used，`/`、`/home`、`/data` 同一根分区） |

### GPU

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX A6000（单卡，Ampere GA102） |
| VRAM total | 49,140 MiB |
| VRAM used（基线） | 43,812 MiB |
| VRAM free（基线） | ≈5,328 MiB |
| Driver | 580.159.03 |
| CUDA (driver) | 13.0 |
| Memory bandwidth（规格） | 768 GB/s |
| GPU utilization | 0%（审计期间 idle） |

---

## 2. Current services

| 服务 | PID | 状态 | 说明 |
|---|---|---|---|
| vLLM | 3068143（主）/ 3068373（EngineCore） | running，health 200 | syy + tmux `vllm`；`/usr/bin/python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml`；占显存 43,508 MiB |
| Ollama | 3561 | running，/api/tags 200 | systemd `ollama.service`（enabled）；`/usr/local/bin/ollama serve`；当前 `{"models":[]}`，0 显存占用 |

其他 GPU 进程：Xorg 4 MiB、gnome-remote-desktop 266 MiB（yuyong）。

**vLLM 当前显存 ≈43GB+（确认仍为 43,508 MiB）；Ollama 当前显存 0；GPU 剩余 ≈5.3GB。**

---

## 3. Ollama compatibility

| 项 | 值/结论 |
|---|---|
| OLLAMA_VERSION | **0.20.7**（`ollama --version`；二进制内嵌0.19.0 等历史串，运行时版本 0.20.7） |
| 服务状态 | active (running) since 2026-05-21，enabled，Restart=always |
| 当前已有模型数量 | **10**（`ollama list`：qwen3-coder:30b、qwen3-embedding:0.6b、nomic-embed-text、qwen2.5-coder:14b/7b、qwen3-embedding:8b、bge-reranker-v2-m3、codellama:13b-instruct、deepseek-r1:7b、qwen3:8b） |

### 能力验证（只验证能力，未创建新模型）

| 能力 | 结论 | 依据 |
|---|---|---|
| GGUF import | **YES** | `ollama create -f Modelfile` 存在；parser 包（Modelfile.CreateRequest / isValidCommand）；错误串 `supplied file was not in GGUF format`；`-q` 量化、`--experimental` safetensors 导入均在 |
| Vision model（运行时） | **YES** | 二进制含 clip_graph_qwen2vl / qwen3vl / llava / siglip / internvl / minicpmv 等图；多种 MultiModalProjector 实现；`application/vnd.ollama.image.projector` 媒体类型 |
| Embedding | **YES** | `/v1/embeddings` 实测 200（前一轮 qwen3-embedding 系列） |
| Reranker | **YES** | bge-reranker-v2-m3 已安装并实测可调用 |
| keep_alive | **YES** | 原生 `/api/generate keep_alive:0` 实测 `done_reason:"unload"`（前一轮）；OpenAI 兼容 `/v1/*` 内该参数不生效（默认 5 分钟过期） |
| 模型自动加载/自动卸载 | **YES** | 前一轮实测：空载 → 调用后新增 runner 进程 +4,579 MiB → 过期自动卸载 |
| LoRA | NO | 二进制串 `loras are not yet implemented` |
| 图像生成（内部能力） | 存在 flux2 / Z-Image 引擎代码与 `--imagegen-engine` 参数，但**无 qwen-image 识别串** | 与 Qwen-Image-2.1 部署判断无关（生图路径见 §10） |

---

## 4. Custom Vision GGUF 条件（JonathanColetti Qwen3.8-27B-Uncensored-GGUF）

目标形态：主 GGUF + 独立 mmproj 文件。

```
CUSTOM_GGUF_SUPPORT       = YES
CUSTOM_MM_PROJ_SUPPORT    = UNCERTAIN
```

依据：

**GGUF = YES**
1. `ollama create MODEL -f Modelfile`（FROM 指向本地 .gguf）为 0.20.7 标准路径，`create --help` 输出完整（含 `-q` 量化）。
2. parser/create 包函数齐全（ConfigFromModelfile、createModelfileLayers、createQuantizedLayers、readSafetensorsHeader 等）。
3. `--quantize`/`-q` 支持把导入模型压到 q5_K_M/q8_0 等级别。

**mmproj = UNCERTAIN**
1. 运行时确定支持 projector：媒体类型 `application/vnd.ollama.image.projector`、结构体字段 `ProjectorPath`/`ProjectorPaths`、`llm.projectorMemoryRequirements`、`hint: you may be using wrong mmproj`、`mismatch between text model and mmproj` 校验串——说明**加载路径**能处理独立 mmproj。
2. 但 Modelfile 命令集（parser.isValidCommand 可见词：from / parameter / template / system / adapter / license / message）**没有 PROJECTOR 命令**；`ollama create --help` 也没有任何 projector/mmproj 参数。
3. create 时"主 GGUF + 外部 mmproj 文件"如何配对（自动探测同目录 / 需要特定命名 / 不支持）在只读条件下无法确证——**本轮禁止真正创建 20GB 模型**，无从实测。
4. 二进制另见 `split vision models aren't supported`，提示并非所有 vision 拆分形态都被接受。

**结论依据边界**：运行时 vision 链路确定存在；create-time 外部 mmproj 导入未验证，需在获准后用小文件或首次真实导入时确认（属部署前验证项，非本轮动作）。

---

## 5. llama.cpp compatibility

```
LLAMA_CPP_INSTALLED = NO
```

| 核查项 | 结果 |
|---|---|
| which llama-cli / llama-server / llama-run | NOT_FOUND |
| /home/yuyong、/home/syy、/usr/local/bin、/usr/bin 搜索 | 无 llama.cpp 构建产物 |
| llama-cpp-python（python 绑定） | ModuleNotFoundError |

- 版本 / CUDA build / Vision-mmproj / MTP / 最大 context 参数：**均 N/A（未安装）**。
- 附注：Ollama 0.20.7 内部自带 llama.cpp 系 runner（含 `--mmproj` 支持串），但那是 Ollama 私有实现，不等于可独立调用的 llama.cpp 工具链。
- 未编译、未安装（遵守禁止项）。

---

## 6. vLLM version

| 项 | 值 |
|---|---|
| VLLM_VERSION | **0.22.0**（`import vllm` via `PYTHONPATH=/home/yuyong/vllm/.venv/lib/python3.12/site-packages`；与在线服务 `system_fingerprint: vllm-0.22.0-219e659d` 一致） |
| syy 默认 python3 | 无 vllm 模块（ModuleNotFoundError） |
| yuyong venv 直接执行 | 权限不足（只读 site-packages 可导入） |
| CURRENT_VLLM_COMMAND | `/usr/bin/python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml` |

配套环境（yuyong vllm venv）：torch 2.11.0+cu128、transformers 5.9.0、safetensors 0.7.0、accelerate 未装、CUDA available（A6000）。
训练 venv（syy）：torch 2.14.0+cu126、transformers 5.8.0、accelerate 1.11.0、safetensors 0.8.0。

---

## 7. vLLM Sleep compatibility

```
VLLM_SLEEP_SUPPORTED            = YES
CURRENT_INSTANCE_SLEEP_ENABLED  = NO
RESTART_REQUIRED_TO_ENABLE_SLEEP= YES
```

依据（vLLM 0.22.0 源码，只读）：

| 证据 | 位置/结果 |
|---|---|
| CLI 参数 | `vllm/engine/arg_utils.py:845` → `"--enable-sleep-mode"`（`enable_sleep_mode: bool = ModelConfig.enable_sleep_mode`，默认 False，`config/model.py:306`） |
| 引擎方法 | `entrypoints/llm.py:806 LLM.sleep(level=1, mode="abort")`、`:831 wake_up()`；`v1/worker/gpu_worker.py:157 sleep(level)`、`:181 wake_up(tags)`；core/protocol/async_llm 均有 is_sleeping |
| Level 1 / Level 2 | **均支持**：`gpu_worker.sleep` 中 `level == 2` 额外把 model buffers 克隆到 CPU；level 1 走 `allocator.sleep(offload_tags=("weights",))`；CuMemAllocator（`device_allocator/cumem.py`）提供 sleep/wake_up |
| HTTP 端点 | `entrypoints/serve/sleep/api_router.py`：`POST /sleep?level=&mode=`、`POST /wake_up?tags=`、`GET /is_sleeping` |
| HTTP 挂载条件 | `attach_router`：**仅当 `envs.VLLM_SERVER_DEV_MODE` 为真时挂载**（api_router.py 末尾） |
| 当前实例是否带 flag | **否**：cmdline 仅 `serve --config qwen3-5.yaml`；qwen3-5.yaml 全文无 sleep 字段（前一轮已读全文） |
| 当前实例端点 | `GET /is_sleeping` → **404**；`/openapi.json` 23 条路径中无 sleep/wake 路由 |

启用方式（建议，不执行）：重启时加 `--enable-sleep-mode`；如需 HTTP 端点还需 `VLLM_SERVER_DEV_MODE=1`。离线 Python（`LLM.sleep()`）路径不需要 HTTP 路由。**本轮未 sleep、未重启。**

---

## 8. vLLM-Omni compatibility

```
VLLM_OMNI_INSTALLED = NOT_INSTALLED
VERSION = N/A
```

- `import vllm_omni` → ModuleNotFoundError（默认 python、vllm venv、训练 venv 三个环境）。
- `which vllm-omni` → NOT_FOUND。
- Qwen-Image / Qwen-Image-2.1 是否被本版识别：**无法预检**（包不存在）。

---

## 9. Diffusers compatibility

| 模块 | 默认 python3 | yuyong vllm venv | syy 训练 venv |
|---|---|---|---|
| torch | NOT_INSTALLED | **2.11.0+cu128** | **2.14.0+cu126** |
| transformers | NOT_INSTALLED | 5.9.0 | 5.8.0 |
| diffusers | NOT_INSTALLED | NOT_INSTALLED | NOT_INSTALLED |
| accelerate | NOT_INSTALLED | NOT_INSTALLED | 1.11.0 |
| safetensors | NOT_INSTALLED | 0.7.0 | 0.8.0 |

- torch.cuda.is_available()：vllm venv **True**，训练 venv **True**
- torch.cuda.get_device_name(0)：**NVIDIA RTX A6000**
- torch.version.cuda：12.8（vllm venv）/ 12.6（训练 venv）
- 全机浅层扫描（/home/yuyong、/home/wsy anaconda 等）：**未发现 diffusers**

**DIFFUSERS_STATUS = NOT READY（缺 diffusers 本体；装包即可用，torch/CUDA 侧无阻碍）**

---

## 10. SGLang compatibility

```
SGLANG_INSTALLED = NO
SGLANG_DIFFUSION_AVAILABLE = N/A（包不存在，无法判定其 diffusion 能力）
```

- `import sglang` → ModuleNotFoundError（三个环境）；`which sglang` / `sglang.launch_server` → NOT_FOUND；浅层扫描无 sglang 目录。
- 未启动任何服务。

---

## 11. Qwen-Image-2.1 环境兼容判断（不下载模型）

前置事实：GPU A6000 48GB（但当前被 vLLM 占 43.5GB，生图路径成立的前提是 vLLM 释放显存或错峰）；RAM 376GB；torch/CUDA 就绪；diffusers / sglang / vllm-omni 均缺。

| 路径 | 判定 | 原因 |
|---|---|---|
| **A. Qwen-Image-2.1 + Diffusers + CPU offload** | **NEEDS_INSTALL** | 仅缺 `diffusers`（+ 它依赖的 accelerate 装在训练 venv 已有 1.11.0，或随 diffusers 一并补装）；torch 2.14+cu126 / CUDA 可用；RAM 355GB available 足以承接 offload。安装后即可用，版本无已知过旧问题 |
| **B. Qwen-Image-2.1 + SGLang-Diffusion** | **NEEDS_INSTALL** | sglang 完全未装；其 diffusion 子能力与 Qwen-Image-2.1 的版本匹配关系只能装后核实（UNKNOWN） |
| **C. Qwen-Image-2.1 + vLLM-Omni** | **NEEDS_INSTALL** | vllm_omni 完全未装；本环境无法只读确认它是否识别 Qwen-Image-2.1（UNKNOWN）。另注意与现役 vLLM 0.22 环境共存需独立 venv |

推荐倾向：A（安装量最小、CPU offload 与 376GB RAM 匹配），见 §16。

---

## 12. Qwen3.8 27B 两个 GGUF 版本（不下载文件）

前提：所有判断基于「Ollama GGUF 导入能力已验证 + 体积/显存算术」；**模型文件本身的架构识别（Qwen3.8 是否被 Ollama runner 认识）必须在下载后才能最终确认，标记 NEEDS_MODEL_DOWNLOAD**。

| Model | Ollama Text | Ollama Vision | llama.cpp Text | llama.cpp Vision |
|---|---|---|---|---|
| A. Zrald Accuracy 15.33GB | **YES\***（导入/量化/运行链路完备；\*架构识别待文件验证） | N/A（该条目未提 mmproj） | N/A（未安装） | N/A（未安装） |
| B. Uncensored Q5_K_M ~19.5GB | **YES\*** | **UNCERTAIN**（mmproj create 配对未验证，运行时 vision 链路 YES） | N/A | N/A |
| C. Uncensored Q8_0 ~29GB | **YES\***（体积 29GB < 49GB，可运行） | **UNCERTAIN**（同上） | N/A | N/A |

- MTP（multi-token prediction）：llama.cpp 未安装，N/A；Ollama 侧未发现 MTP 相关串，**MTP 加速不可预期**。
- 262K context：见 §14。
- Uncensored Q8_0 status：**可运行（text，Ollama）**，体积最大、速度最慢；vision 同 UNCERTAIN。

---

## 13. VRAM budget（以「vLLM 释放显存后」≈48.8GB 可用为基准）

估算含：权重、KV cache（16K 为参考点）、CUDA workspace、vision mmproj、image activation、VAE、runtime buffer。非只比较权重大小。

| 模型 | 构成估算 | 判定 |
|---|---|---|
| Zrald Accuracy 15.33GB | 权重 15.33 + KV 16K ≈2.5 + workspace/激活 ≈2.5–3.5 → ≈21GB | **SAFE** |
| Uncensored Q5_K_M 19.5GB + mmproj 0.9 | 19.5 + 0.9 + KV 2.5 + 图像激活与 buffer ≈3 → ≈26GB | **SAFE** |
| Uncensored Q8_0 29GB + mmproj 0.9 | 29 + 0.9 + KV 2.5 + buffer ≈3 → ≈35.5GB | **LIKELY**（再加大 ctx 或并发会变 TIGHT） |
| Qwen-Image-2.1 ~33GB | 权重 ≈33 + 文本编码器 ≈4–8 + VAE ≈0.3 + 1024² 激活与 buffer ≈3–6 → 全 GPU ≈41–48GB | **TIGHT**（全上 GPU 无余量）；**CPU offload → LIKELY**（RAM 充足） |

硬约束：**当前 vLLM 占 43.5GB 时，以上任何模型都没有运行空间**（仅剩 5.3GB）；本表成立前提是 vLLM 释放（或未来 sleep 生效，见 §7）。

---

## 14. Context capability

| 问题 | 结论 |
|---|---|
| 官方 Qwen3.8-27B native context | **NEEDS_MODEL_DOWNLOAD**（模型卡/GGUF 头未取，不下载 15GB 文件） |
| GGUF metadata 中 context_length | **NEEDS_MODEL_DOWNLOAD**（只读小文件 header 方案本轮未做——GGUF 头虽小，但 URL/仓库来源未给定） |
| 262144 是否架构支持 | **大概率架构层支持（Qwen 系列具备 YaRN 类扩展），但须以下载后 GGUF metadata 为准** |
| A6000 是否建议真设 262144 | **不建议** |

KV 估算（假设：27B Qwen 类 ≈40 层、8 个 KV 头、head_dim 128、fp16 KV → ≈160 KB/token；实际随架构 ±30%）：

| Context | KV 体积 | Zrald 15.33GB 组合 | Q5 19.5GB 组合 | Q8 29GB 组合 |
|---|---|---|---|---|
| 16K | ≈2.5 GB | **可用（推荐）** | 可用（推荐） | 可用（推荐） |
| 32K | ≈5 GB | 可用 | 可用 | 可用（舒适上限） |
| 64K | ≈10 GB | 可用 | 可用 | TIGHT |
| 128K | ≈20 GB | 可用（余量变小） | TIGHT | NOT_RECOMMENDED |
| 262K | ≈40 GB | **NOT_RECOMMENDED**（仅 KV 已 40GB，加权重必超 49GB） | NOT_RECOMMENDED | NOT_RECOMMENDED |

建议：Zrald 日常 **8K–32K**，峰值 64K；Q5 日常 8K–32K；Q8 不超过 32K。KV 量化（Ollama `num_ctx` + kv 类型）可再省一半，但以实测为准。

---

## 15. Concurrency estimate（ESTIMATE ONLY，非 benchmark）

前提：单卡 A6000、解码受 768 GB/s 显存带宽约束、Ollama `num_parallel` 控制并发、按短上下文估算。

**Zrald Accuracy（15.33GB）推荐并发：**

| Context | 推荐并发 |
|---|---|
| 8K | 2–4 |
| 16K | 2–3 |
| 32K | 1–2 |
| 64K | 1–2 |
| 128K | 1（KV 挤占显存后排队） |
| 262K | 不可行（见 §14） |

**Uncensored Q5_K_M（19.5GB）推荐并发：**

| Context | 推荐并发 |
|---|---|
| 8K | 2–3 |
| 16K | 2–3 |
| 32K | 1–2 |
| 64K | 1 |
| 128K | 1（TIGHT） |
| 262K | 不可行 |

以上全部为 **ESTIMATE ONLY**；真实并发能力需下载后压测得出。

---

## 16. Speed estimate（ESTIMATE，非实测）

依据：A6000 显存带宽 768 GB/s；量化权重读取效率按 55–70% 估；解码速度 ≈ 有效带宽 ÷ 权重体积；未编造任何 benchmark 数字（后续下载运行后才可标 MEASURED）。

Ollama CUDA：**已确认**（前一轮 runner 实际占 GPU 4,574 MiB 并完成推理）；llama.cpp 独立 CUDA build：未安装，N/A。

| 模型 | EXPECTED DECODE TOK/S RANGE（单流） | 标记 |
|---|---|---|
| Zrald Accuracy 15.33GB | **≈25–40 tok/s** | ESTIMATE |
| Uncensored Q5_K_M 19.5GB | **≈20–30 tok/s** | ESTIMATE |
| Uncensored Q8_0 29GB | **≈13–20 tok/s** | ESTIMATE |

参考：多流并发时总吞吐可上浮（短上下文约 1.5–2.5×），但单流延迟变差；prefill（长提示词灌入）粗估 800–2,500 tok/s，随长度与量化波动。Qwen-Image-2.1 单步生成耗时无法在缺包条件下估算（UNKNOWN）。

---

## 17. Recommended deployment path（推荐矩阵）

| Requirement | Best Choice |
|---|---|
| 最小体积高质量文本 | **Zrald Accuracy 15.33GB @ Ollama**（现装 0.20.7，零安装风险；预计 SAFE + 25–40 tok/s） |
| 去审查（uncensored） | **JonathanColetti Q5_K_M（19.5GB）@ Ollama**（体积/质量平衡优于 Q8；Q8 作高精度备选） |
| Vision（视觉） | **Uncensored Q5 + mmproj**：优先 Ollama（create 配对需首次导入验证）；不成立则改用 **llama.cpp llama-mtmd-cli（NEEDS_INSTALL）** 作为后备，mmproj 支持最明确 |
| 最大上下文 | Ollama `num_ctx` 32K（Zrald 可到 64K）；**不追 262K**（VRAM 不允许，见 §14） |
| Ollama | **首选**（已安装、已验证、自动加载可用） |
| llama.cpp | 未安装；如需精确 ctx 控制 / mmproj 后备 / 独立服务，**建议安装（NEEDS_INSTALL）** |
| 生图 | **Diffusers + CPU offload（NEEDS_INSTALL，路径 A）**；SGLang-B / vLLM-Omni-C 均缺件且支持待验 |
| A6000 48GB | 三个 GGUF 档位在释放 vLLM 后 SAFE/LIKELY 可跑；**与现役 vLLM 并存时全部不可跑** |
| 最低部署风险 | 纯文本需求 = 直接用现有 Ollama 导入 GGUF（唯一零安装路径）；vision/生图 = 必须先补装组件 |

---

## 18. 当前服务未改动确认

| 项 | 结果 |
|---|---|
| vLLM 主 PID 3068143 / EngineCore 3068373 | **未变化** |
| Ollama PID 3561 | **未变化** |
| GET :8000/health | **200** |
| GET :11434/api/tags | **200** |
| GPU used | 43,812 MiB（与审计开始时一致，无显著变化） |
| `ollama /api/ps` | `{"models":[]}`（无残留加载） |

---

## 19. Missing prerequisites（部署前缺口清单）

| # | 缺口 | 影响 | 动作（需批准，本轮未做） |
|---|---|---|---|
| 1 | diffusers + accelerate（可用环境）未装 | Qwen-Image-2.1 路径 A 不可用 | pip 安装（到指定 venv） |
| 2 | sglang 未装 | 路径 B 不可用 | pip 安装并核验 diffusion 能力 |
| 3 | vllm_omni 未装 | 路径 C 不可用 | pip 安装并核验 Qwen-Image 支持 |
| 4 | llama.cpp 未装 | mmproj 后备路径、独立 llama-server 不可用 | 构建或取 CUDA 预编译包 |
| 5 | Ollama create + 外部 mmproj 配对未实测 | vision 导入结论停在 UNCERTAIN | 获准后首次导入时验证（可先用小 mmproj 试） |
| 6 | Qwen3.8 架构识别与 context_length 未读 | 架构/262K 结论需文件落地 | 下载后读 GGUF 头（NEEDS_MODEL_DOWNLOAD） |
| 7 | vLLM 占 43.5GB 显存 | 所有目标模型无运行空间 | 部署前需与 Commander 确认显存释放策略（涉及 sleep/停服务，需另行授权） |
| 8 | 若需 HTTP sleep 端点 | 需 `VLLM_SERVER_DEV_MODE=1` + `--enable-sleep-mode`，均要重启 | 获批后执行（本轮禁止） |

---

## 16/附：Changes made

**NONE**（REMOTE 端零修改：未停/重启 vLLM 与 Ollama、未 sleep、未改 systemd/tmux/配置/模型、未下载任何模型文件、未 pip/apt 安装、未动 CUDA/驱动/防火墙/缓存。唯一副作用为对 8000 发起的只读探测请求与若干本地 python import，GPU 显存与服务 PID 全程与基线一致。）

> 说明：报告未记录真实服务器 IP、主机名（以 SERVER_IP_REDACTED / SERVER_HOSTNAME_REDACTED 代替）、密码、SSH key、token、credential。
