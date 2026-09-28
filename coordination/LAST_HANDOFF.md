# Last Agent Handoff

Updated At: 2026-09-28  
Last Task ID: LOCAL-MODEL-UNIFIED-DYNAMIC-SERVING-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW

## Completed（本轮：11 个本地模型三级 Serving 统一接入）

- **LEVEL 1（Ollama 本地导入）**：临时 Modelfile `FROM /data/vllm/<dir>`，tag 带 `-local`。
  **成功 4**：`qwen3.5:9b-local`（caps completion+**vision**，真实图片实测准确描述）、
  `gemma3:12b-it-local`（同，vision ✓）、`deepseek-coder:6.7b-instruct-local`（code smoke ✓）、
  `codellama:7b-instruct-local`（code smoke ✓）。
  **失败 5 进 LEVEL 2**：Qwen3-14B/Mistral/StarCoder2 = `unsupported architecture`；
  gemma2 ×2 = Ollama daemon Go panic（`interface conversion: string→map`，systemd 3s 自恢复）。
  **跳过 2**：CodeLlama-13B、Qwen2.5-Coder-7B = ALREADY_COVERED。
  失败 create 无残留 tag；事后 `/api/tags`=14（原 10 完好 + 新 4）。
- **关键运维事实**：`ollama create` 必须 `OLLAMA_HOST=127.0.0.1:11435`——默认打 11434 网关，
  `/api/blobs` 上传会 `connection reset by peer`。
- **LEVEL 2（GGUF + llama.cpp）**：llama.cpp `e85e15c` 的 `conversion/` 包支持全部 5 个目标架构。
  转换用 `env/image` venv（torch2.14/tf5.17）+ 执行机下载 `sentencepiece` wheel scp 离线安装
  （**服务器 PyPI 与国内镜像全超时**）。5×F16 → `llama-quantize Q4_K_M`：
  qwen3-14b 9.0G / mistral 4.4G / gemma2-it 5.8G / gemma2 5.8G / starcoder2 4.5G，
  落 `/data/vllm/ConvertedGGUF/<NAME>/`。**GGUF magic + file_type=15 + 张量数 + llama-cli 5/5 rc=0
  全过**；验证后删 5 个 F16 中间文件回收 89G（§38 授权），原始 safetensors 抽查完好。
  `/data/vllm/ConvertedGGUF` 需 sudo 创建（原目录 syy 无写权限）。
- **泛化 Manager**：`services/llama-manager/llama_manager.py` + `configs/llama-manager/models.yaml`
  （6 模型 registry，default=zrald-qwen3.8-27b，参数不散落代码）。
  - 生命周期：admission（ollama ps >1G + nvidia >1G 双确认）→ flock gpu.lock → spawn :8012 → idle 600s SIGTERM
  - **切换不释放租约**（stop A → spawn B 全程 lease_held=true，不给 Image 插入窗口）
  - **推理中换模型 = QUEUE**（Condition 等待，实测 B 排 14.8s 后 200，A 未被 kill）
  - 端点：/health、/manager/status（原 zrald 字段全保留+追加）、/v1/models、/v1/chat/completions
  - **Zrald 向后兼容 PASS**：无 model 字段 → 回退 default zrald 200 `OK`；未知 model 名同回退
- **统一调度（§21 竞态修复）**：网关新增 `LlamaGate`（轮询 `GATEWAY_LLAMA_STATUS` 默认
  8010 `/manager/status` 的 `lease_held`）；GPU 完成类等待条件 = **Image busy ∨ llama lease_held**，
  超时 1800s → 503（新增 `LLAMA_GPU_BUSY`）。三场景闭环实测全 PASS（详见报告 §8）。
- **Level 3**：VLLM_DYNAMIC = **NOT_NEEDED**（无模型落在 Ollama∧llama.cpp 都不支持的区间），
  未建 vllm-manager，`/home/yuyong/vllm/*.yaml` 只读未动，8000 保持 CLOSED。
- **回归全过**：Image 1024×1024 200×2（84.9s/65.5s）；`qwen3:8b` 200 `OK`、`embed0.6b` 200 dim1024；
  端点 8010/8011/8020/3000/11434 全 200；runner 每次 ≤1s 释放；GPU 峰值 33,469 MiB（<47,000 HIGH_VRAM 线）；
  **本轮 CUDA OOM = 0**。
- **磁盘**：可用 2.0T → 峰值 1.1T → 1.2T；ConvertedGGUF 117G → 28G（F16 清理后）。
- 报告：`reports/LOCAL_MODEL_UNIFIED_DYNAMIC_SERVING.md`（17 节）

## Previous Tasks（要点保留）

- **OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001**：原 10 模型全 smoke PASS；reranker `/api/rerank`
  404（MODEL_PRESENT + ENDPOINT_UNAVAILABLE）；网关日志 `ok` 只代表透传成功≠推理成功
- **OLLAMA-QWEN3-EMBEDDING-06B**：0.6b = REUSED（Q8_0/32768/1024），keep_alive 注入实证
- **IMAGE-WEBUI-TIMEOUT-ALIGN**：`IMAGE_REQUEST_TIMEOUT_MS = 1_200_000` 唯一常量，600 用例全绿
- **GPU-SCHEDULER-STRICT**：Image admission = runner空 ∧ lock ∧ VRAM+3072；queue1200 ≥ wait900

## Status Flags

| Flag | Value |
|---|---|
| OLLAMA MODELS | 14（原 10 完好 + 4 `-local`） |
| LEVEL 1 / 2 / 3 | 4 PASS / 5→GGUF PASS / NOT_NEEDED |
| LLAMA MANAGER | :8010 registry 6 模型，spawn_count 验证，切换/排队 PASS |
| GPU STRICT SERIAL | 三方互斥闭环实测 PASS（网关 LlamaGate 上线） |
| ZRALD COMPAT | PASS（8010 原字段与行为全保留） |
| IMAGE | 回归 PASS，调度未破坏 |
| VLLM | 8000 CLOSED，原配置未动 |
| CUDA OOM（本轮） | NO；峰值 33,469 MiB |
| 原始权重 | PRESERVED（未删/未移/未覆盖；仅新增 ConvertedGGUF 与 Ollama blob） |
| GIT | 见最终回复 |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 | **llama-manager**（泛化 Zrald，registry 6 模型，default zrald，idle 600s） |
| 8011 Image | RUNNING（严格准入未改） |
| 8020 WebUI | RUNNING |
| 11434 | 网关（**新代码：Image + LlamaGate 双条件**）→ 11435 |
| 11435 | Ollama backend（回环，14 模型） |
| 3000 OWUI | RUNNING |
| 8000 vLLM | CLOSED |
| GPU | 682-9321 MiB（随当前占用），gpu.lock 空闲时 FREE |

## 环境要点（下轮必读）

- **网关等待条件已变**：Image busy **∨** llama-manager `lease_held`（8010）；`BYPASS_RELEASE`
  只针对 Image 资源等待，llama busy 时全扣（含 release 请求）
- **ollama create/show 必须 `OLLAMA_HOST=127.0.0.1:11435`**（网关不支持 blob 上传）
- **服务器 PyPI 不通**（直连+国内镜像全超时）：Python 依赖从执行机下载 wheel scp + `pip --no-index`；
  ML 转换用 `env/image` venv（已有 torch/tf/numpy + 本轮补的 sentencepiece）
- **Ollama 0.20.7 内置转换器缺口**：Qwen3ForCausalLM / MistralForCausalLM / Starcoder2ForCausalLM
  架构缺失；gemma2 导入触发 daemon panic（`interface conversion: string→map`，Restart=always 自愈）
- **`/data/vllm/ConvertedGGUF` 权限**：新建子目录需 sudo（原目录属 root/vllm 组）
- llamar-manager 请求 503 = admission 正确拒绝（GPU_BUSY：ollama runner 未释放 / 锁被占 /
  nvidia >1G 进程），**等资源释放重试即可**，不是服务故障
- llama-cli 非交互 smoke：`-st -m file -n 8 -p "..." --seed 42 < /dev/null`（`-no-cnv` 已不存在）
- 历史沿用：sudo 密码仅当次 heredoc 首行；pkill 自匹配用 PID 直杀；curl `--noproxy '*'`；
  Node 于 `env/node-v22.23.3-linux-x64/bin`；真实 IP 永不入 Git；`ollama stop` CLI 404 勿用
- 释放 Ollama 模型用 API `keep_alive:0`；reasoning 模型用 `think:false`（qwen3 系）或足量 num_predict

## Exact Next Action

WAIT FOR COMMANDER REVIEW（Git 分阶段提交见最终回复）

## Do Not

- 未授权不动：原权重、`/home/yuyong/vllm`、systemd、Image 后端、CUDA/driver、网络、Open WebUI
- 不 `ollama pull/rm/create`（新任务需授权）、不删原 10 模型、不删本轮 Q4
- 网关 `LlamaGate` 与 llama-manager 是互斥闭环两侧，勿单独关闭
- 测试图/tmp/logs/GGUF/blob/真实IP/secret 不入 Git；禁 git add -A
