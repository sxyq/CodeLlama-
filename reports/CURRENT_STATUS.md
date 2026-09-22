# CodeLlama LoRA 微调项目——当前状态

任务编号：STATUS-AUDIT-RESET-001  
审计角色：Execution Agent（只调查、整理、写报告、推送 GitHub）  
本轮禁止训练。

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| 审计时间 | 2026-09-22T17:02:56+08:00 |
| 本地项目路径 | `/Users/sunyiyang/Desktop/Project/微调/` |
| Git 状态 | 分支 `main`，与 `origin/main` 对齐；工作区曾删除旧 `reports/CURRENT_STATUS.md`，本文件为重写产物 |
| 数据集状态 | LOCAL 未找到；REMOTE 未找到 |
| 远程服务器是否确认 | CONFIRMED（按 Commander 指定的 SSH 目标连通） |
| 硬件类型 | NVIDIA GPU |
| 设备数量 | 1 |
| 当前资源是否可用 | CONSTRAINED（单卡几乎被 vLLM 占满，空闲显存 4574 MiB） |
| LLaMA-Factory 状态 | NOT FOUND |
| CodeLlama 状态 | READY（远程存在 CodeLlama-13b-Instruct-hf，tokenizer 文件齐全） |
| 当前是否正在训练 | NO |
| 当前能否开始 LoRA | NO |
| 当前第一阻塞项 | Fine-Tuning 训练数据在 LOCAL 与 REMOTE 均不存在 |

## 1. 实验固定要求

以下为 Commander 已确定的实验要求，不代表环境已经满足：

| 项 | 要求 |
|---|---|
| Base Model | CodeLlama-13B-Instruct-hf |
| Framework | LLaMA-Factory |
| Finetuning Method | LoRA |
| 任务方向 | Assembly Code + Pseudocode → C/C++ Source Code |
| 数据规模（已知） | 约 1455 条 |

说明：上述为项目要求，不是对当前环境状态的假设。环境是否满足见第 10 节。

## 2. LOCAL-MAC 当前项目

### 2.1 Git

| 项 | 值 |
|---|---|
| 工作目录 | `/Users/sunyiyang/Desktop/Project/微调/` |
| 当前分支 | `main` |
| 远程 | `origin` → `https://github.com/sxyq/CodeLlama-.git` |
| 上游跟踪 | `origin/main` |
| 近期提交 | `39590d1` docs: translate status audit to Chinese |
|  | `3752355` status: initial local and remote environment audit |
| HEAD 跟踪文件 | 仅 `reports/CURRENT_STATUS.md` |
| 工作区状态（审计时） | `reports/CURRENT_STATUS.md` 已删除（待本文件重建）；`reports/.DS_Store` 未跟踪 |

证据：[LOCAL-MAC] `git status` / `git branch -avv` / `git remote -v` / `git log --oneline -15` / `git ls-tree -r HEAD --name-only`。

### 2.2 项目目录

```text
/Users/sunyiyang/Desktop/Project/微调/
├── .git/
└── reports/
    └── .DS_Store
```

除 Git 元数据与 `reports/` 外，工作区无其他源码、配置、脚本或数据文件。

### 2.3 已有文件

| 路径 | 用途 | 完成度 | 是否执行过 | 是否仍有效 |
|---|---|---|---|---|
| `reports/CURRENT_STATUS.md` | 环境状态报告 | 本轮重写 | 本轮生成 | 有效（本文件） |
| `reports/.DS_Store` | macOS 目录元数据 | 不适用 | 不适用 | 不参与项目 |

未发现：`README*`、`AGENTS.md`、`CLAUDE.md`、`*.py`、`*.sh`、`*.yaml`、`*.yml`、`*.log`、`*.txt`、`*.json`（工作区）。

### 2.4 已有脚本和配置

| 类型 | 状态 | 证据 |
|---|---|---|
| LLaMA-Factory 配置 | NOT FOUND | 工作区无 yaml/yml/json 配置 |
| LoRA YAML | NOT FOUND | 同上 |
| tokenizer 统计脚本 | NOT FOUND | 无 `.py`/`.sh` |
| dataset 注册配置 | NOT FOUND | 无 dataset_info / data 配置 |
| train shell | NOT FOUND | 无 `.sh` |
| Python 训练脚本 | NOT FOUND | 无 `.py` |
| benchmark 脚本 | NOT FOUND | 无相关文件 |
| 环境确认脚本 | NOT FOUND | 无相关文件 |
| 训练日志 | NOT FOUND | 无 `.log` |
| checkpoint 信息 | NOT FOUND | 无输出目录/日志 |
| 实验笔记 | NOT FOUND | 无笔记文件 |
| 服务器连接说明 | NOT FOUND | 工作区无 SSH/连接文档；本轮凭 Commander 给定目标完成连通 |

结论：LOCAL-MAC 当前没有可复用的训练工程，仅有状态报告仓库。

### 2.5 数据集

在 `/Users/sunyiyang/Desktop/Project/微调/` 内以多种命名模式搜索：

- `Fine-Tuning*.json`
- `Fine_Tuning*.json`
- `*Fine*Tun*.json`
- `*finetun*.json`
- `*.json` / `*.jsonl`

结果：**0 个数据文件**。

扩展搜索 `/Users/sunyiyang/Desktop`、`/Users/sunyiyang/Downloads`、`/Users/sunyiyang/Documents`（深度有限）中的 Fine-Tuning / finetune / fine_tun 命名 JSON：**0 个命中**。

| 项 | 值 |
|---|---|
| 文件路径 | NOT FOUND |
| 文件大小 | N/A |
| SHA256 | N/A |
| JSON 合法性 | N/A |
| 顶层结构 | N/A |
| 样本数量 | N/A |
| conversations / human / gpt | N/A |
| unique input / output / 重复样本 | N/A |

### 2.6 已完成工作

基于 Git 历史与当前工作区：

1. 已建立远程 GitHub 仓库跟踪（`sxyq/CodeLlama-`）。
2. 已有 2 条与状态报告相关的提交历史。
3. 本轮完成从零重审计并重建 `reports/CURRENT_STATUS.md`。

未完成（本地）：

1. 训练数据未落地。
2. LLaMA-Factory 配置、LoRA YAML、训练脚本、数据集注册均不存在。
3. tokenizer 统计脚本与历史 token 统计结果均不存在。

## 3. REMOTE-SERVER

### 3.1 目标服务器确认过程

1. [LOCAL-MAC] 在项目内搜索 README / 脚本 / 配置 / 笔记中的远程线索：工作区无此类文件。
2. [LOCAL-MAC] 读取 `~/.ssh/config`（仅取 Host / User / IdentityFile 等连接元数据，不记录地址与密钥内容）。可见其他机器别名，但 Commander 本轮明确指定 SSH 用户与目标，故以该目标为 REMOTE-SERVER。
3. [LOCAL-MAC] 先尝试口令登录：远端仅接受 `publickey`，口令认证不可用。
4. [LOCAL-MAC] 使用本地专用密钥（`~/.ssh/id_ed25519_remote_server`）以 `BatchMode` 登录成功，只读采集系统与硬件信息。
5. 结论：**REMOTE TARGET = CONFIRMED**。报告中统一称 `REMOTE-SERVER`，不写真实 hostname / IP。

备注：本机 SSH 配置中另有其他计算资源别名；本轮未将其纳入本项目目标，也未修改任何远程环境。

### 3.2 系统信息

| 项 | 值 |
|---|---|
| 时间 | 2026-09-22T17:02:56+08:00 |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | 6.8.0-87-generic x86_64 |
| 用户 | `syy` |
| HOME | `/home/syy` |
| 登录后 pwd | `/home/syy` |

### 3.3 存储和 RAM

| 项 | 值 |
|---|---|
| RAM total | 376 GiB |
| RAM used（采集时） | 22 GiB |
| RAM available | 354 GiB |
| Swap | 0 B |
| 根文件系统 | 3.5 T 总量，2.0 T 已用，1.4 T 可用（约 60%） |
| `/data`、`/workspace`、`/opt`、`/srv` | 同属根卷可见路径；`/data` 存在，`/workspace` 未列出 |

### 3.4 GPU / NPU

`which npu-smi`：NOT FOUND。Ascend 相关：NOT FOUND。

`which nvidia-smi`：FOUND。`nvidia-smi` 实测：

| 项 | 值 |
|---|---|
| GPU 型号 | NVIDIA RTX A6000 |
| GPU 数量 | 1 |
| 单卡总显存 | 49140 MiB |
| 当前显存使用 | 43966 MiB |
| 当前空闲显存 | 4574 MiB |
| 当前 GPU 利用率 | 0 % |
| Driver | 580.159.03 |
| CUDA（驱动报告） | 13.0 |
| CUDA SDK | 13.0.3（`/usr/local/cuda/version.json`） |
| Persistence | On |
| 完整空闲卡数量 | 0（唯一一张卡非空闲） |

占用进程（GPU）：

| PID 类型 | 进程摘要 | 显存 |
|---|---|---|
| G | Xorg | 4 MiB |
| C+G | gnome-remote-desktop-daemon | 266 MiB |
| C | VLLM::EngineCore | 43662 MiB |

### 3.5 当前占用进程

| 服务/任务 | 状态 | 备注 |
|---|---|---|
| vLLM | RUNNING | 用户 `yuyong`，`vllm serve --config qwen3-5.yaml`，启动时间 2026-09-22 13:18:48；GPU 显存 43662 MiB |
| Ollama | RUNNING | 用户 `ollama`，`/usr/local/bin/ollama serve` |
| LLaMA-Factory / llamafactory-cli | NOT FOUND in process list | — |
| torchrun / deepspeed / accelerate | NOT FOUND | — |
| LoRA training / CodeLlama train | NOT FOUND | — |

```text
TRAINING_RUNNING = NO
```

本轮未 kill、未停止任何服务。

## 4. ML 环境

评估对象：REMOTE-SERVER 上用户 `syy` 可直接使用的 Python 环境。  
`/home/yuyong/vllm/.venv/bin/python3` 存在，但对 `syy` 为“权限不够”，不能作为本项目训练环境读取包版本。

### 4.1 Python

| 项 | Status | 版本/路径 |
|---|---|---|
| 系统 Python | FOUND | Python 3.12.3，`/usr/bin/python3` |
| conda | NOT FOUND | — |
| venv / `.venv`（syy 可访问） | NOT FOUND | — |
| uv | NOT FOUND | — |
| pyenv | NOT FOUND | — |
| `/home/syy/.local` | FOUND | 无可用训练解释器证据 |

### 4.2 PyTorch

| 项 | Status | 版本 |
|---|---|---|
| torch | NOT FOUND | ModuleNotFoundError（syy 系统 Python） |
| torch CUDA build | UNKNOWN | torch 未安装，无法读取 |

### 4.3 CUDA 或 CANN

| 项 | Status | 版本 |
|---|---|---|
| NVIDIA driver | FOUND | 580.159.03（nvidia-smi） |
| CUDA toolkit | FOUND | 13.0.3 |
| nvcc | FOUND | 13.0.88 |
| torch_npu | NOT FOUND | — |
| CANN / ASCEND_HOME_PATH | NOT FOUND | — |

### 4.4 Transformers

| 项 | Status | 版本 |
|---|---|---|
| transformers | NOT FOUND | ModuleNotFoundError |
| tokenizers | NOT FOUND | ModuleNotFoundError |
| safetensors | NOT FOUND | ModuleNotFoundError |

### 4.5 PEFT

| 项 | Status | 版本 |
|---|---|---|
| peft | NOT FOUND | ModuleNotFoundError |

### 4.6 Accelerate

| 项 | Status | 版本 |
|---|---|---|
| accelerate | NOT FOUND | ModuleNotFoundError |

### 4.7 Datasets

| 项 | Status | 版本 |
|---|---|---|
| datasets | NOT FOUND | ModuleNotFoundError |

小结：REMOTE-SERVER 对当前用户缺少可训练的 Python/ML 栈；系统仅有 Python 3.12.3 与 CUDA 工具链。硬件驱动可用，训练库不可用。

## 5. LLaMA-Factory

搜索范围：REMOTE-SERVER 的 `/home/syy`、`/data`、`/workspace`、`/opt`、`/srv`（maxdepth 有限），以及 LOCAL-MAC 项目目录。

| 项 | 结果 |
|---|---|
| 目录 LLaMA-Factory / llama_factory | NOT FOUND |
| 命令 llamafactory-cli / llamafactory | NOT FOUND |
| Python 包 llamafactory | NOT FOUND（syy Python） |
| git branch / commit / status | N/A |
| version | N/A |
| 现成 YAML | NOT FOUND |
| 本项目数据注册 | NOT FOUND |

```text
LLaMA-Factory = NOT FOUND
```

本轮未安装、未拉取、未修改任何源码。

## 6. CodeLlama-13B-Instruct-hf

REMOTE-SERVER 命中等价目录（命名大小写与 `13B`/`13b` 略有差异）：

`/data/vllm/CodeLlama-13b-Instruct-hf`

| 项 | 值 |
|---|---|
| 模型路径 | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| 总大小 | 约 49 GiB；目录内普通文件合计 52394549031 bytes |
| config.json | FOUND（589 bytes） |
| generation_config.json | FOUND |
| tokenizer.json | FOUND（约 1.8 MB） |
| tokenizer.model | FOUND |
| tokenizer_config.json | FOUND |
| special_tokens_map.json | FOUND |
| safetensors | 3 个分片（`model-0000x-of-00003.safetensors`） |
| pytorch bin | 3 个分片（同名 `.bin`，并存） |
| model.safetensors.index.json | FOUND |
| pytorch_model.bin.index.json | FOUND |
| model_type | `llama` |
| torch_dtype | `bfloat16` |
| max_position_embeddings | 16384 |
| vocab_size | 32016 |
| hidden_size | 5120 |
| num_hidden_layers | 40 |
| num_attention_heads | 40 |
| architectures | `['LlamaForCausalLM']` |

同机还存在其他 CodeLlama 相关缓存/目录（如 7b Instruct、13b-hf、13b-Python-hf 等），本项目目标以 Instruct 13b 为准。

```text
TOKENIZER READY
```

本轮未加载模型到 GPU，未启动推理，未重新下载。

## 7. Fine-Tuning 数据

| 位置 | 路径 | 大小 | SHA256 | 样本数 |
|---|---|---|---|---|
| LOCAL-MAC | NOT FOUND | N/A | N/A | N/A |
| REMOTE-SERVER | NOT FOUND | N/A | N/A | N/A |

搜索模式（两侧）：`Fine-Tuning*.json`、`Fine_Tuning*.json`、`*Fine*Tun*.json`、`*finetun*.json`、`*fine_tun*.json` 等。

```text
DATASET_MATCH = UNKNOWN
```

原因：两侧均无数据文件，无法比较 SHA256。  
未修改任何数据文件。

历史 token 统计结果（Input Tokens / Output Tokens / Total Tokens）：NOT FOUND。本轮不做完整 token 统计。

## 8. 当前训练配置

```text
NOT CONFIGURED
```

工作区与远程用户可读路径均未发现 LLaMA-Factory YAML、LoRA 配置或训练入口脚本。

| 参数 | 状态 |
|---|---|
| cutoff_len | NOT YET DECIDED |
| packing | NOT YET DECIDED |
| lora_rank | NOT YET DECIDED |
| lora_alpha | NOT YET DECIDED |
| lora_target | NOT YET DECIDED |
| epoch | NOT YET DECIDED |
| learning_rate | NOT YET DECIDED |
| batch size | NOT YET DECIDED |
| gradient accumulation | NOT YET DECIDED |
| precision | NOT YET DECIDED |

本轮不擅自确定最终参数。

## 9. 当前训练状态

| 项 | 值 |
|---|---|
| TRAINING_RUNNING | NO |
| 推理/常驻占用 | vLLM（约 43.7 GB 显存）、Ollama |
| checkpoint | NOT FOUND |
| 训练日志 | NOT FOUND |
| 是否已开始 LoRA | NO |

## 10. Readiness Matrix

| Component | Status | Evidence | Blocking Problem |
|---|---|---|---|
| Local project | PARTIAL | 仅有 Git 状态报告仓库；无训练代码/配置 | 缺少可执行训练工程 |
| Dataset local | NOT READY | 项目与常见用户目录搜索 0 命中 | 无 Fine-Tuning JSON |
| SSH | READY | 专用密钥 `BatchMode` 登录成功 | 口令认证不可用（仅 publickey） |
| Remote target | CONFIRMED | Commander 指定目标 + 只读连通验证 | 无 |
| Hardware | CONSTRAINED | 1×RTX A6000，空闲 4574 MiB，vLLM 占 43662 MiB | 单卡几乎被占用，完整空闲卡=0 |
| Python environment | NOT READY | syy 仅有系统 Python 3.12.3；torch 等均 NOT FOUND | 无训练用 ML 栈 |
| LLaMA-Factory | NOT FOUND | 多路径与包导入均未命中 | 未安装/不可见 |
| CodeLlama model | READY | `/data/vllm/CodeLlama-13b-Instruct-hf` 文件与 config 齐全 | 无 |
| Dataset remote | NOT READY | 多路径搜索 0 命中 | 无 Fine-Tuning JSON |
| LoRA configuration | NOT READY | 无 YAML/脚本；超参 NOT YET DECIDED | 配置未起草 |
| Training can start | NO | 数据、框架、可训练环境、显存均不满足 | 见 Blocking Issues |

## 11. Blocking Issues

按严重度排序：

1. **训练数据不存在**  
   LOCAL-MAC 与 REMOTE-SERVER 均未找到约 1455 条 Assembly + Pseudocode → C/C++ 的 Fine-Tuning JSON。没有数据则无法注册数据集、无法统计 token、无法训练。

2. **缺少可训练 Python/ML 环境与 LLaMA-Factory**  
   REMOTE-SERVER 用户 `syy` 环境中 torch / transformers / peft / accelerate / datasets 均为 NOT FOUND，LLaMA-Factory 为 NOT FOUND。现有 `/home/yuyong/vllm/.venv` 对 `syy` 不可读。

3. **单卡显存被 vLLM 长期占用**  
   1×RTX A6000（49140 MiB）当前空闲仅 4574 MiB，VLLM::EngineCore 占用 43662 MiB。完整空闲卡数量=0，CodeLlama-13B + LoRA 训练无法在当前空闲显存下开展。

4. **训练配置未起草**  
   cutoff_len / packing / LoRA 超参 / epoch / lr / batch / grad accum / precision 全部为 NOT YET DECIDED。此项不阻止环境准备，但阻止正式开训。

## 12. 下一阶段建议

仅建议，本轮不执行：

1. 由 Commander/数据侧提供 Fine-Tuning JSON 的稳定来源与期望 SHA256，落到 LOCAL-MAC 后再同步 REMOTE-SERVER，并复核样本数（目标约 1455）与 conversations 字段。
2. 在 REMOTE-SERVER 为 `syy` 准备独立训练环境（Python + PyTorch CUDA + transformers/peft/accelerate/datasets + LLaMA-Factory），与 vLLM 推理环境隔离。
3. 明确 vLLM 服务的去留策略：释放或迁移其显存占用，使 A6000 具备可训练余量；或改用其他完整空闲 GPU 节点。
4. 由 LoRA 参数决策人给出 cutoff_len、packing、lora_rank、lora_alpha、lora_target、epoch、learning_rate、batch size、gradient accumulation、precision，并起草 LLaMA-Factory YAML 与 dataset_info 注册。
5. 以上就绪后先做 tokenizer 长度统计与显存估算，再进入正式训练审批。

## 13. 审计轨迹

本轮真正执行的重要命令（已脱敏，不含 IP/口令/密钥/令牌）：

[LOCAL-MAC]
- `cd /Users/sunyiyang/Desktop/Project/微调/ && pwd`
- `git status`
- `git branch -avv`
- `git remote -v`
- `git log --oneline -15`
- `git ls-tree -r HEAD --name-only`
- `git show --stat HEAD`
- `git log --all --name-status --oneline`
- `find . -type f`（项目全量文件）
- `find` / 命名模式搜索 Fine-Tuning / finetune / fine_tun 相关 JSON（项目目录 + Desktop/Downloads/Documents 有限深度）
- 读取 `~/.ssh/config`、`ssh-add -l`（仅用于判断可用认证方式）
- SSH 只读连通验证（专用密钥，`BatchMode`）
- 口令认证尝试（失败，服务端仅允许 publickey）

[REMOTE-SERVER]
- `date -Is`
- `uname -a`
- `cat /etc/os-release`
- `pwd` / `whoami`
- `free -h`
- `df -h`
- `which nvidia-smi npu-smi python3 ...`
- `nvidia-smi`
- `nvidia-smi --query-gpu=memory.total,memory.used,memory.free,utilization.gpu,name --format=csv`
- `ps -eo pid,user,lstart,cmd`（过滤 vLLM/Ollama/训练相关）
- `find` 搜索 LLaMA-Factory / CodeLlama / Fine-Tuning 数据
- `python3` 读取模型 `config.json` 与目录分片信息
- `python3` 导入 torch/transformers/peft/accelerate/datasets/safetensors/tokenizers/torch_npu/llamafactory
- `cat /usr/local/cuda/version.json`

本轮未修改远程文件、未安装依赖、未上传数据、未停止服务、未启动训练、未下载模型。
