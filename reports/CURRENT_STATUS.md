# CodeLlama LoRA 项目——当前状态

> **审计编号：** STATUS-AUDIT-001  
> **生成时间：** 2026-09-22T15:34 Asia/Shanghai  
> **模式：** 只读——未执行任何安装、删除、配置变更、进程控制、下载或训练操作。

---

## 0. 总览快照

| 条目 | 值 |
|------|-------|
| 审计日期 | 2026-09-22 |
| 本地机器 | `[LOCAL-MAC]` macOS |
| 远程机器 | `[REMOTE-SERVER]` Ubuntu 24.04.4 LTS，内核 6.8.0-87-generic x86_64 |
| 指定项目 | `/Users/sunyiyang/Desktop/Project/路由`（ModelRouter 研究） |
| 状态同步仓库 | `https://github.com/sxyq/CodeLlama-.git`（`main` 分支；本报告随后完成首次同步） |
| CodeLlama 模型 | **FOUND**——位于 `[REMOTE-SERVER]`，CodeLlama-13b-Instruct-hf（约 49 GB） |
| Fine-Tuning.json | **NOT FOUND**——在可访问的 `[LOCAL-MAC]` 和 `[REMOTE-SERVER]` 搜索范围内未找到 |
| LLaMA-Factory | **NOT FOUND**——两端均未找到 |
| `[REMOTE-SERVER]` 是否有训练任务在运行 | **NO** |
| `[LOCAL-MAC]` / `[REMOTE-SERVER]` 能否立即开始 LoRA 训练 | **NO** |

---

## 1. 本地 Mac

### 1.1 工作目录与 Git

本节所有检查来源：`[LOCAL-MAC]`。

| 检查项 | 结果 |
|-------|--------|
| `pwd` | `/Users/sunyiyang/Desktop/Project/路由` |
| 分支 | `main` |
| 远程仓库 | `origin` → `https://github.com/sxyq/modelrouter.git` |
| HEAD 提交 | `2557d3f Move deck trio into汇报/PPT, add script and screenshots` |

**最近提交记录（git log --oneline -5）：**

```
2557d3f Move deck trio into汇报/PPT, add script and screenshots
62a16e2 Add deck player, restore Claude models, revamp P4 interactive component
9bfdfaa Remove obsolete blog integration plan
2a15e4a Add model matrix dashboard and update PPT planning
1de62d8 Add P4 KV cache slide
```

**工作区状态（用户已有的变更——本次审计未做任何修改）：**

| 状态 | 文件 |
|--------|------|
| D | `our-project/papers/unified-ai-gateway.txt` |
| D | `our-project/slides/assets/unified-ai-gateway-concept.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-12.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-14.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-20.png` |
| ?? | `our-project/汇报/data-readiness-routing-report.html` |

### 1.2 项目结构与关键文件

| 路径 | 说明 |
|------|-------------|
| `README.md` | ModelRouter 研究项目；`our-project/` 存放研究资料，`external-projects/` 存放外部项目注册。明确排除原始服务器日志和凭据。 |
| `our-project/README.md` | 文献、数据、论文和计划目录。 |
| `our-project/data/README.md` | 源数据/清洗数据/汇总数据分层；数据粒度为调用级别，非任务级别计费。 |
| `our-project/planning/IMPLEMENTATION_RESEARCH.md` | 路由研究设计（Agent 轨迹/成本日志、准入时预测、模型 × 工作量选择）。**LoRA 不是本文档的关注点。** |
| `our-project/literature/` | 相关论文、简报、报告。 |
| `our-project/汇报/` | PPT 策划、幻灯片图片、数据就绪报告。 |
| `external-projects/` | 已注册的 semantic-router、RouterBench、TwinRouterBench、MTRouter、LangGraph、AgentOpt、Best-Route-LLM。 |

### 1.3 本地 Mac 上的 CodeLlama / LoRA / 微调相关产物

| 产物 | 状态 |
|----------|--------|
| `Fine-Tuning.json`（或 `Fine_Tuning.json`） | **NOT FOUND**——已扫描 Desktop、Documents、Downloads 及指定项目目录。 |
| CodeLlama 模型目录 | **NOT FOUND**——本地未找到。 |
| LLaMA-Factory 仓库克隆 | **NOT FOUND**——本地未找到。 |
| CodeLlama LoRA YAML 配置 | **NOT FOUND**——本地未找到。 |
| CodeLlama 训练脚本 | **NOT FOUND**——本地未找到。 |
| CodeLlama 评测脚本 | **NOT FOUND**——本地未找到。 |
| CodeLlama 训练日志 | **NOT FOUND**——本地未找到。 |
| `AGENTS.md` / 根目录 `CLAUDE.md` | **NOT FOUND**——项目根目录未找到（嵌套副本属于外部引入的第三方仓库）。 |

> **备注：** 引入的 `semantic-router` 目录树中包含无关的 BERT/ModernBERT 分类器微调脚本，使用 PEFT/LoRA 和公开数据集。文件头检查确认它们是分类示例，**并非** CodeLlama-13B 指令微调。未发现执行痕迹。

### 1.4 Fine-Tuning.json 详情

| 字段 | 值 |
|-------|-------|
| 路径 | **NOT FOUND** |
| 大小 | N/A |
| SHA256 | N/A |
| 解析结果 | N/A |
| 样本数 | N/A |

---

## 2. 远程服务器

本节所有检查来源：`[REMOTE-SERVER]`。

### 2.1 系统信息

| 检查项 | 结果 |
|-------|--------|
| 主机名 | `REMOTE-SERVER`（已脱敏） |
| 检查时日期 | `2026-09-22T14:41:28+08:00` |
| 操作系统 | Ubuntu 24.04.4 LTS |
| 内核 | Linux 6.8.0-87-generic x86_64 |
| Shell | `/bin/bash` |
| 运行时长 | 17 周 5 天 2 小时 47 分钟 |

### 2.2 存储

| 文件系统 | 类型 | 总容量 | 已用 | 可用 | 使用率 |
|------------|------|------|------|-------|------|
| 根分区（`/`） | ext4 | 3.5 T | 2.0 T | 1.4 T | 60% |

`df -hT` 未报告单独的模型文件系统。

### 2.3 内存

| 指标 | 值 |
|--------|-------|
| 总 RAM | 376 GiB |
| 已用 RAM | 22 GiB |
| 空闲 RAM | 50 GiB |
| 可用 RAM | 354 GiB |
| Swap | 0 B |

### 2.4 GPU / NPU

| 设备 | 详情 |
|--------|---------|
| GPU | **NVIDIA RTX A6000**（GA102GL），总显存 49,140 MiB |
| GPU 已用显存 | 43,966 MiB（vLLM 约 43,662 MiB + GNOME remote-desktop 约 266 MiB） |
| GPU 空闲显存 | 4,574 MiB |
| GPU 利用率 | 检查时为 0% |
| NPU（`npu-smi`） | **NOT FOUND** |
| 昇腾 PCI 设备 | **NOT FOUND**——PCI 设备清单仅显示 NVIDIA GA102GL |

### 2.5 相关进程

| 进程 | 备注 |
|---------|-------|
| vLLM 引擎 | 运行中，服务 CodeLlama-13b-Instruct-hf，占用约 43.7 GiB GPU 显存 |
| Ollama | 服务活跃 |
| Jupyter | 端口 8888 |
| Open WebUI | 端口 3000 |
| SSH | 活跃 |
| Docker | 服务活跃（审计账号无 socket 权限） |
| `torchrun` / `deepspeed` / `accelerate launch` / LLaMA-Factory 训练 | **NONE** |

### 2.6 相关端口

| 端口 | 服务 |
|------|---------|
| 8000 | vLLM API |
| 8888 | Jupyter |
| 3000 | Open WebUI |
| 11434 | Ollama |

---

## 3. 机器学习环境

### 3.1 [REMOTE-SERVER] Python

| 检查项 | 结果 |
|-------|--------|
| 系统 Python | `/usr/bin/python3` → Python 3.12.3 |
| `python` 命令 | **NOT FOUND**——审计账号 PATH 中不存在 |
| conda / mamba / micromamba | **NOT FOUND** |
| `llamafactory-cli` | **NOT FOUND** |

### 3.2 [REMOTE-SERVER] 系统 Python 导入测试（全部失败）

`torch`、`torch_npu`、`transformers`、`peft`、`accelerate`、`datasets`、`safetensors`、`llamafactory`、`vllm`、`tokenizers`——从系统 Python 导入均报 **ModuleNotFoundError**。

### 3.3 [REMOTE-SERVER] vLLM 虚拟环境

| 字段 | 值 |
|-------|-------|
| 路径 | `/home/████/vllm/.venv`（所有者已脱敏） |
| 基础 Python | CPython 3.12.10（由 uv 管理） |
| 审计账号可访问性 | 仅可读取元数据；解释器不可执行 |

**vLLM 虚拟环境中已安装的包：**

| 包名 | 版本 |
|---------|---------|
| `torch` | 2.11.0+cu128 |
| `transformers` | 5.9.0 |
| `safetensors` | 0.7.0 |
| `tokenizers` | 0.22.2 |
| `vllm` | 0.22.0 |

**vLLM 虚拟环境中未安装的包：**

`torch_npu`、`peft`、`accelerate`、`datasets`、`llamafactory`

### 3.4 [REMOTE-SERVER] CANN / 昇腾

| 检查项 | 结果 |
|-------|--------|
| `torch_npu` | **NOT FOUND**（任何位置均未安装） |
| CANN 工具包 | **NOT FOUND** |
| 昇腾环境变量 | **NOT FOUND** |
| 昇腾目录 | **NOT FOUND**——`/usr/local/Ascend`、`/opt` 下均未找到 |

> **结论：** 远程服务器为 **CUDA/NVIDIA** 环境（RTX A6000 + CUDA 12.8）。该服务器**不具备**昇腾环境，且无 NPU 硬件。

---

## 4. LLaMA-Factory

| 检查项 | 位置 | 结果 |
|-------|----------|--------|
| LLaMA-Factory 目录 | `[REMOTE-SERVER]` 可访问范围内（`/home`、`/data`、`/opt`、`/workspace`、`/srv`） | **NOT FOUND** |
| LLaMA-Factory 目录 | `[LOCAL-MAC]` 指定项目 | **NOT FOUND** |
| `llamafactory-cli` | `[REMOTE-SERVER]` PATH | **NOT FOUND** |
| LLaMA-Factory git 仓库克隆 | `[REMOTE-SERVER]` 可访问范围 | **NOT FOUND** |
| LoRA 训练 YAML 配置 | `[REMOTE-SERVER]` | **NOT FOUND** |
| 训练 shell/Python 脚本 | `[REMOTE-SERVER]` | **NOT FOUND** |
| 评测脚本 | `[REMOTE-SERVER]` | **NOT FOUND** |
| 训练日志 | `[REMOTE-SERVER]` | **NOT FOUND** |

> 远程搜索范围有限，仅遵循审计账号可读取的路径。`/home` 下属于其他用户的私有目录无法完全枚举，因此以上结果表示"在可访问搜索范围内未找到"，而非证明不存在其他副本。

---

## 5. CodeLlama 模型

### 5.1 [REMOTE-SERVER] 模型文件

| 字段 | 值 |
|-------|-------|
| 状态 | **FOUND** |
| 路径 | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| 大小 | 约 49 GB |
| `model_type` | `llama` |
| `architectures` | `[LlamaForCausalLM]` |
| `torch_dtype` | `bfloat16` |
| `max_position_embeddings` | 16384 |
| `hidden_size` | 5120 |
| `num_hidden_layers` | 40 |
| `num_attention_heads` | 40 |
| `vocab_size` | 32016 |
| `rope_theta` | 1000000 |

**分词器文件：** `tokenizer.json`、`tokenizer.model`、`tokenizer_config.json`、`special_tokens_map.json`、`generation_config.json`——全部存在。

**权重文件：** 3 × safetensors 分片 + 索引；3 × PyTorch `.bin` 分片 + 索引（两种格式重复存储，占用额外磁盘空间——审计期间未删除任何文件）。

### 5.2 [REMOTE-SERVER] 活跃的 vLLM 服务

| 字段 | 值 |
|-------|-------|
| vLLM 版本 | 0.22.0 |
| 健康检查 | HTTP 200 |
| `/v1/models` | HTTP 200 |
| 对外模型 ID | `codellama-13b-instruct-hf` |
| 模型根路径 | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| `max_model_len` | 16384 |
| `gpu_memory_utilization` | 0.92 |
| 活跃配置文件 | `/home/████/vllm/qwen3-5.yaml`（文件名遗留/具有误导性；实际内容指向 CodeLlama-13B） |
| 微调权限 | `false`（推理端点的预期行为） |

**审计时的指标：**

| 指标 | 值 |
|--------|-------|
| `num_requests_running` | 0 |
| `num_requests_waiting` | 0 |
| `prompt_tokens_total` | 14 |
| `generation_tokens_total` | 3 |
| `request_success_total`（stop） | 1 |

> 此前仅有一次极小请求；检查时无正在处理的请求。

**备用配置：** `/home/████/vllm/codellama13b.yaml` 同样指向同一模型，对外名称为 `codellama-13b`，设置 `max_num_batched_tokens=32768`。根据进程命令行判断，该配置当前未激活。

---

## 6. 数据集

| 检查项 | 位置 | 结果 |
|-------|----------|--------|
| `Fine-Tuning.json` | `[LOCAL-MAC]` Desktop、Documents、Downloads、项目目录 | **NOT FOUND** |
| `Fine-Tuning.json` | `[REMOTE-SERVER]` 可访问范围内（`/data`、`/home`、`/opt`、`/workspace`、`/srv`） | **NOT FOUND** |
| `Fine_Tuning.json` | `[LOCAL-MAC]` 和 `[REMOTE-SERVER]` 可访问搜索范围 | **NOT FOUND** |
| 任意微调 JSON 文件 | `[LOCAL-MAC]` 和 `[REMOTE-SERVER]` 可访问搜索范围 | **NOT FOUND** |
| SHA256 比对 | — | **UNKNOWN**（未找到数据集文件，无法计算摘要） |
| 样本数 | — | **N/A** |
| 唯一 input/output 数 | — | **N/A** |
| 函数数 | — | **N/A** |

> 远程搜索范围有限，仅遵循审计账号可读取的路径。`/home` 下属于其他用户的私有目录无法完全枚举，因此数据集结果仍为**在可访问搜索范围内 NOT FOUND**，比对结果仍为 **UNKNOWN**。

---

## 7. 当前训练状态

| 问题 | 回答 |
|----------|--------|
| 是否有 CodeLlama/LoRA 训练进程正在运行？ | **NO** |
| 是否有 `torchrun` / `deepspeed` / `accelerate launch` 正在运行？ | **NO** |
| 是否有 LLaMA-Factory 进程正在运行？ | **NO** |
| 现有 GPU 工作负载 | vLLM 推理（CodeLlama-13b-Instruct-hf）占用约 43.7 GiB / 49.1 GiB GPU 显存 |
| 是否找到训练检查点 | **NONE** |
| 是否找到训练日志 | **NONE** |
| 是否找到训练输出目录 | **NONE** |

---

## 8. 就绪性评估

| 组件 | 状态 | 证据 | 问题 |
|-----------|--------|----------|---------|
| 本地项目 | ⚠️ PARTIAL | `[LOCAL-MAC]` Git 仓库已存在（`modelrouter`），研究资料齐全 | 项目为 ModelRouter 研究，而非 CodeLlama LoRA 流水线。本地无训练脚本、数据集或 LoRA 配置。 |
| SSH | ✅ READY | `[REMOTE-SERVER]` 通过已配置的密钥成功连接 SSH | — |
| 昇腾运行时 | ❌ NOT READY | `[REMOTE-SERVER]` 无 NPU 硬件、无 `npu-smi`、无 `torch_npu`、无 CANN | 服务器为 NVIDIA CUDA 环境，非昇腾。若昇腾为硬性要求则存在需求不匹配。 |
| LLaMA-Factory | ❌ NOT READY | `[REMOTE-SERVER]` + `[LOCAL-MAC]` 两端均未安装 | 训练前必须完成安装和配置。 |
| CodeLlama 模型 | ✅ READY | `[REMOTE-SERVER]` `/data/vllm/CodeLlama-13b-Instruct-hf`（约 49 GB），配置和分词器已验证 | 模型当前由 vLLM 提供推理服务；可作为 LoRA 训练的基座模型。 |
| 数据集 | ❌ NOT READY | `[LOCAL-MAC]` + `[REMOTE-SERVER]` 未找到 `Fine-Tuning.json` | 训练前必须创建/上传数据集。 |
| NPU 资源 | ❌ NOT APPLICABLE | `[REMOTE-SERVER]` 硬件为 NVIDIA RTX A6000，非昇腾 NPU | 若要求昇腾 NPU，需更换服务器。 |
| GPU 资源（CUDA） | ⚠️ CONSTRAINED | `[REMOTE-SERVER]` RTX A6000：49,140 MiB 中仅 4,574 MiB 空闲（vLLM 占用约 43.7 GiB） | 训练无法与活跃的 vLLM 服务共享 GPU，除非停止 vLLM 或另行规划资源。 |
| **LoRA 训练能否立即开始** | ❌ **NO** | 存在多项阻塞 | 见 §9 阻塞问题。 |

---

## 9. 阻塞问题

| # | 阻塞项 | 严重程度 | 详情 |
|---|---------|----------|---------|
| 1 | **无数据集** | 🔴 CRITICAL | 在可访问的 `[LOCAL-MAC]` 和 `[REMOTE-SERVER]` 搜索范围内均未找到 `Fine-Tuning.json`。没有数据则无法训练。 |
| 2 | **无 LLaMA-Factory** | 🔴 CRITICAL | `[REMOTE-SERVER]` 上未安装或克隆 LLaMA-Factory。没有可用的训练框架。 |
| 3 | **无训练流水线** | 🔴 CRITICAL | 两端均不存在 LoRA YAML 配置、训练脚本或实验配置。 |
| 4 | **GPU 容量受限** | 🟠 HIGH | vLLM 推理占用约 89% 的 GPU 显存（43.7/49.1 GiB），仅剩约 4.6 GiB 空闲。训练需要停止 vLLM 或另行配置 GPU 资源。 |
| 5 | **缺少 `peft` / `accelerate` / `datasets`** | 🟠 HIGH | 在 `[REMOTE-SERVER]` 可访问的环境中未找到这些包。LoRA 微调必须依赖它们。 |
| 6 | **昇腾/NPU 需求不匹配** | 🟡 MEDIUM | 若项目计划要求昇腾 NPU，当前服务器（NVIDIA CUDA）无法满足。需重新规划或更换服务器。 |
| 7 | **本地项目范围不匹配** | 🟡 MEDIUM | 指定的本地项目（`modelrouter`）为 API 路由研究，而非 CodeLlama LoRA 微调。可能需要建立专用项目目录或分支。 |

---

## 10. 重要发现

1. **模型已在线提供推理服务。** CodeLlama-13b-Instruct-hf 正通过 vLLM v0.22.0 在端口 8000 上对外服务 `[REMOTE-SERVER]`。模型文件完整且已验证（配置、分词器、权重）。这是一项有利条件——基座模型已在服务器上就绪。

2. **权重格式重复存储。** `[REMOTE-SERVER]` 模型目录同时包含 safetensors 和 PyTorch `.bin` 分片，约重复了 25 GB 的权重文件。建议在确认 LLaMA-Factory 偏好格式后仅保留一种（推荐 safetensors）。

3. **配置文件名具有误导性。** `[REMOTE-SERVER]` 活跃的 vLLM 配置文件名为 `qwen3-5.yaml`，但实际服务的是 CodeLlama-13b。仅为命名问题，不影响所观测到的推理端点。

4. **未检测到昇腾硬件。** `[REMOTE-SERVER]` 所有硬件检查均确认仅有 NVIDIA CUDA。若上游计划要求昇腾/NPU，需更换服务器。

5. **vLLM 虚拟环境不适用于训练。** `[REMOTE-SERVER]` 其可读取的包元数据中缺少 `peft`、`accelerate` 和 `datasets`。应为训练创建独立环境。

6. **可用 RAM 充裕。** `[REMOTE-SERVER]` 354 GiB 可用 RAM 完全满足 LoRA 训练期间的数据加载和预处理需求。

7. **无既有训练产物。** `[REMOTE-SERVER]` 未找到任何检查点、日志或训练输出目录。训练将从零开始。

---

## 11. 建议的后续检查

> 以下仅为建议。本次审计期间未采取任何操作。

1. **准备并上传 `Fine-Tuning.json`**——确定指令微调数据集格式（例如 Alpaca 风格的 `instruction`/`input`/`output`），创建或整理数据，计算 SHA256，上传至 `[REMOTE-SERVER]`。

2. **在 `[REMOTE-SERVER]` 上安装 LLaMA-Factory**——克隆仓库，创建专用 Python 虚拟环境并安装 `torch`、`peft`、`accelerate`、`datasets`、`transformers` 和 `safetensors`。验证新环境可访问 GPU。

3. **规划 GPU 资源分配**——决定训练期间是否停止 vLLM，或安排在低峰时段训练。使用 4-bit 量化对 CodeLlama-13B 进行 LoRA 训练可能仅需约 20 GiB 显存，但必须先解决当前 vLLM 的显存占用问题。

4. **创建 LoRA 训练配置**——编写 LLaMA-Factory YAML，指定 LoRA rank、alpha、目标模块、学习率、batch size 和输出目录，目标模型为 CodeLlama-13b-Instruct-hf。

5. **明确昇腾/NPU 需求**——若不再要求昇腾（服务器为 NVIDIA），请更新项目计划。若昇腾为硬性要求，需寻找并配置配备昇腾硬件的服务器。

---

## 12. 审计轨迹

### [LOCAL-MAC] 命令

| # | 命令 | 用途 |
|---|---------|---------|
| 1 | `pwd` | 验证工作目录 |
| 2 | `git status --short --branch` | 检查分支和工作区状态 |
| 3 | `git branch --show-current` | 确认当前分支 |
| 4 | `git log --oneline -10` | 最近提交历史 |
| 5 | `git remote -v` | 远程仓库 URL |
| 6 | `find`（多次调用） | 定位项目文件（MD、YAML、JSON、PY、SH、LOG） |
| 7 | `rg` / `mdfind` | 搜索 Fine-Tuning.json 和 CodeLlama 相关产物 |
| 8 | 文件读取 | README.md、our-project/README.md、our-project/data/README.md、IMPLEMENTATION_RESEARCH.md、第三方脚本文件头 |

### [REMOTE-SERVER] 命令（全部通过 SSH 以只读方式执行）

| # | 命令 | 用途 |
|---|---------|---------|
| 1 | `hostname` | 服务器标识（报告中已脱敏） |
| 2 | `date -Is` | 时间戳 |
| 3 | `uname -a` | 内核和架构 |
| 4 | `cat /etc/os-release` | 操作系统版本 |
| 5 | `uptime` | 服务器运行时长 |
| 6 | `free -h` | 内存使用情况 |
| 7 | `df -hT` | 磁盘使用情况 |
| 8 | `nvidia-smi` | GPU 状态、显存、进程 |
| 9 | `which npu-smi` / `nv-smi` | 检查是否存在 NPU 工具 |
| 10 | `lspci` | PCI 设备清单 |
| 11 | `ps aux` | 运行中的进程 |
| 12 | `systemctl list-units` | 活跃的服务 |
| 13 | `ss -tlnp` | 监听端口 |
| 14 | `find`（限定深度） | 搜索 LLaMA-Factory、数据集、训练产物 |
| 15 | `python3 -c "import ..."` | 测试 ML 包可用性 |
| 16 | `cat .venv/pyvenv.cfg` | vLLM 虚拟环境 Python 版本 |
| 17 | 包元数据读取 | torch、transformers 等版本检查 |
| 18 | `cat config.json` | 模型架构验证 |
| 19 | `ls` 模型目录 | 分词器和权重文件清单 |
| 20 | `curl` vLLM `/version`、`/health`、`/v1/models`、`/metrics` | API 状态验证 |
| 21 | `cat qwen3-5.yaml`、`codellama13b.yaml` | vLLM 配置检查 |
| 22 | 环境变量检查（已过滤） | CANN/昇腾环境变量 |

### 合规性

- ✅ 本报告未写入任何 SSH 密码、私钥、API 密钥、令牌、Cookie 或密钥。
- ✅ 本报告未写入任何服务器公网/内网 IP 地址。
- ✅ 本报告未写入任何完整的"用户名+主机"组合。
- ✅ 本报告未写入任何环境变量中的敏感信息。
- ✅ 服务器引用仅使用 `REMOTE-SERVER`；本地引用仅使用 `LOCAL-MAC`。
- ✅ 未执行任何远程安装、删除、配置变更、进程控制、下载或训练操作。

---

*本报告由 STATUS-AUDIT-001 根据审计期间收集的只读命令证据生成。报告结束。*
