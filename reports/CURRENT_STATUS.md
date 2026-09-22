# CodeLlama LoRA 微调项目——当前状态

任务编号：ENV-WORKSPACE-001（环境准备）之后更新  
上一轮：STATUS-AUDIT-RESET-001  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| 审计/执行时间 | 2026-09-22 |
| 本地项目路径 | `/Users/sunyiyang/Desktop/Project/微调/` |
| Git 状态 | 分支 `main`，状态报告仓库 |
| 数据集状态 | LOCAL 与 REMOTE 均存在；SHA256 一致；1455 条 |
| 远程服务器是否确认 | CONFIRMED（REMOTE-SERVER） |
| 硬件类型 | NVIDIA GPU |
| 设备数量 | 1×RTX A6000 |
| 当前资源是否可用 | CONSTRAINED（空闲 4574 MiB，vLLM 占用中） |
| LLaMA-Factory 状态 | READY（`$HOME/codellama-lora/LLaMA-Factory`，0.9.6.dev0） |
| CodeLlama 状态 | READY + READ ONLY |
| 当前是否正在训练 | NO |
| 当前能否开始 LoRA | NO（显存被占用；LoRA 参数未定） |
| 当前第一阻塞项 | 单卡几乎被 vLLM 占满，无法承载 CodeLlama-13B LoRA |
| ENV READY | YES |

## 1. 实验固定要求

以下为 Commander 已确定的实验要求，不代表训练已开始：

| 项 | 要求 |
|---|---|
| Base Model | CodeLlama-13B-Instruct-hf |
| Framework | LLaMA-Factory |
| Finetuning Method | LoRA |
| 任务方向 | Assembly Code + Pseudocode → C/C++ Source Code |
| 数据规模 | 1455 条（已核实） |

## 2. LOCAL-MAC 当前项目

### 2.1 Git

| 项 | 值 |
|---|---|
| 工作目录 | `/Users/sunyiyang/Desktop/Project/微调/` |
| 分支 | `main` |
| 远程 | `origin` → `https://github.com/sxyq/CodeLlama-.git` |
| 角色 | 状态同步仓库（reports / coordination / scripts / configs / data/README.md） |

### 2.2 项目目录

```text
/Users/sunyiyang/Desktop/Project/微调/
├── data/
│   ├── Fine-Tuning.json     # 不入 Git
│   └── README.md
├── reports/
│   ├── CURRENT_STATUS.md
│   └── ENV_SETUP_STATUS.md
├── Fine-Tuning(1).json      # 本地原始下载名
└── .git/
```

### 2.3 已有文件

| 路径 | 用途 | 完成度 | 是否执行过 | 是否仍有效 |
|---|---|---|---|---|
| `reports/CURRENT_STATUS.md` | 项目总状态 | 已更新 | 是 | 有效 |
| `reports/ENV_SETUP_STATUS.md` | 环境准备结果 | 完成 | 是 | 有效 |
| `data/Fine-Tuning.json` | 训练原始数据 | 已校验并上传 | 是 | 有效 |
| `data/README.md` | 数据说明（可入 Git） | 完成 | 是 | 有效 |

### 2.4 已有脚本和配置

训练 YAML / train shell / benchmark 脚本：**NOT CONFIGURED**（本轮禁止创建最终 LoRA 参数与开训配置执行体）。

远程侧已存在：

| 路径 | 用途 |
|---|---|
| `$HOME/codellama-lora/configs/project_env.sh` | 项目缓存与 PATH |
| `$HOME/codellama-lora/reports/ENV_INSTALL_PLAN.md` | 安装前计划 |
| `$HOME/codellama-lora/WORKSPACE_POLICY.md` | 写入边界 |
| `$HOME/codellama-lora/README.md` | 工作区说明 |
| `$HOME/codellama-lora/coordination/LLaMA-Factory.revision` | 固定 revision |
| `$HOME/codellama-lora/logs/env_install.log` | 安装日志 |

### 2.5 数据集

| 项 | 值 |
|---|---|
| 样本数 | 1455 |
| 格式 | list of `{conversations: [{from: human/gpt, value: ...}]}` |
| LOCAL SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| REMOTE SHA256 | 同上 |
| DATASET_MATCH | YES |

### 2.6 已完成工作

1. 本地数据校验与规范路径放置。
2. 远程工作区 `$HOME/codellama-lora` 建立。
3. 数据上传且 SHA256 对齐，远程原始数据只读。
4. 隔离 `.venv` + PyTorch CUDA + LLaMA-Factory 及官方依赖。
5. 模型只读确认；README 与 WORKSPACE_POLICY 落盘。
6. 本报告与 `ENV_SETUP_STATUS.md` 同步 GitHub。

## 3. REMOTE-SERVER

### 3.1 目标服务器确认过程

REMOTE TARGET = CONFIRMED。报告中统一称 `REMOTE-SERVER`，不写 hostname / IP。

### 3.2 系统信息

Ubuntu 24.04.4 LTS，kernel 6.8.0-87-generic x86_64，用户 `syy`。

### 3.3 存储和 RAM

RAM 376 GiB；根卷 3.5 T，可用约 1.4 T。

### 3.4 GPU / NPU

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX A6000 × 1 |
| total / used / free | 49140 / 43966 / 4574 MiB |
| util | 0% |
| NPU | NOT FOUND |
| 完整空闲卡 | 0 |

### 3.5 当前占用进程

| 服务 | 状态 | 显存 |
|---|---|---|
| vLLM | RUNNING（未改动） | 43662 MiB |
| Ollama | RUNNING（未改动） | — |
| LoRA training | NOT RUNNING | — |

```text
TRAINING_RUNNING = NO
TRAINING_STARTED = NO
```

## 4. ML 环境

安装目标：`$HOME/codellama-lora/.venv`（Python 3.12.3）。

| 组件 | Status | 版本 |
|---|---|---|
| Python | FOUND | 3.12.3 |
| PyTorch | FOUND | 2.14.0+cu126 |
| CUDA available | YES | torch CUDA 12.6 |
| Transformers | FOUND | 5.8.0 |
| PEFT | FOUND | 0.18.1 |
| Accelerate | FOUND | 1.11.0 |
| Datasets | FOUND | 4.0.0 |
| Tokenizers | FOUND | 0.22.2 |
| Safetensors | FOUND | 0.8.0 |
| SentencePiece | FOUND | import 成功 |

## 5. LLaMA-Factory

| 项 | 值 |
|---|---|
| path | `$HOME/codellama-lora/LLaMA-Factory` |
| version | 0.9.6.dev0 |
| git commit | `97b32d3133b501432141a82949d5c7bc4d94f23a` |
| branch | main |
| CLI | 可用 |

## 6. CodeLlama-13B-Instruct-hf

| 项 | 值 |
|---|---|
| path | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| policy | READ ONLY |
| MODEL_READABLE | YES |
| TOKENIZER_READABLE | YES |
| Base model modified | NO |
| 训练引用方式 | `model_name_or_path=/data/vllm/CodeLlama-13b-Instruct-hf` |

## 7. Fine-Tuning 数据

| 位置 | 路径 | SHA256 | 样本数 |
|---|---|---|---|
| LOCAL | `data/Fine-Tuning.json` | `28bab944…c7b6` | 1455 |
| REMOTE | `$HOME/codellama-lora/data/Fine-Tuning.json` | `28bab944…c7b6` | 1455 |

```text
DATASET_MATCH = YES
```

完整 SHA256：`28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6`

历史 token 统计：NOT FOUND。TOKENIZER READY。

## 8. 当前训练配置

```text
NOT CONFIGURED
```

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

## 9. 当前训练状态

```text
TRAINING_STARTED = NO
GPU TRAINING NOT STARTED
```

未做 smoke training / benchmark / QLoRA / Full Fine-Tuning。

## 10. Readiness Matrix

| Component | Status | Evidence | Blocking Problem |
|---|---|---|---|
| Local project | READY | 状态同步仓库 + 数据 + 报告 | 无 |
| Dataset local | READY | 1455 条，SHA256 已记录 | 无 |
| SSH | READY | 专用密钥登录 | 无 |
| Remote target | CONFIRMED | 只读连通与写入边界验证 | 无 |
| Hardware | CONSTRAINED | 1×A6000，空闲 4574 MiB | vLLM 占用 43662 MiB |
| Python environment | READY | `.venv` 3.12.3 | 无 |
| LLaMA-Factory | READY | 0.9.6.dev0 @ 97b32d3 | 无 |
| CodeLlama model | READY | 只读可访问 | 无 |
| Dataset remote | READY | SHA256 与 LOCAL 一致 | 无 |
| LoRA configuration | NOT READY | 超参 NOT YET DECIDED | 待 Commander 参数 |
| Training can start | NO | 显存不足 + 参数未定 | 见 Blocking Issues |
| ENV READY | YES | 见 ENV_SETUP_STATUS.md | — |

## 11. Blocking Issues

按严重度：

1. **单卡显存被 vLLM 占用**  
   空闲仅 4574 MiB，完整空闲卡=0。CodeLlama-13B + LoRA 当前无法开训。
2. **LoRA / 训练参数未定**  
   全部超参 NOT YET DECIDED，尚无可执行 YAML。
3. **（不阻塞开训前置）token 统计未做**  
   tokenizer 已就绪，统计需在参数与 cutoff 方案确定后进行。

## 12. 下一阶段建议

1. 由服务负责人决定 vLLM 显存释放或迁移策略，腾出完整训练余量。
2. Commander 给出 LoRA 与优化器、序列长度相关参数。
3. 起草 LLaMA-Factory YAML 与 dataset_info 注册（衍生划分用新文件）。
4. 运行 tokenizer 长度统计（Input/Output/Total Tokens）。
5. 参数与显存方案确认后再进入正式训练审批。

## 13. 审计轨迹（ENV-WORKSPACE-001 节选）

[LOCAL-MAC]
- 校验 `Fine-Tuning(1).json` / `data/Fine-Tuning.json`（JSON 解析、SHA256、样本数、conversations 结构）
- `scp` 上传数据至 REMOTE 工作区
- 整理 `reports/ENV_SETUP_STATUS.md`、`reports/CURRENT_STATUS.md`、`data/README.md`
- `git add` / `commit` / `push origin main`

[REMOTE-SERVER]
- 创建 `$HOME/codellama-lora/**` 目录骨架
- 写入 `configs/project_env.sh`
- 拉取 LLaMA-Factory 源码（固定 commit）并写 `coordination/LLaMA-Factory.revision`
- 写入 `reports/ENV_INSTALL_PLAN.md`
- `python3.12 -m venv .venv`
- `pip install` torch/torchvision/torchaudio（cu126）
- `pip install -e LLaMA-Factory` + `requirements/metrics.txt`
- import / `llamafactory-cli version` 验证
- 只读读取基础模型 `config.json` 与 tokenizer 配置
- 写入 `README.md`、`WORKSPACE_POLICY.md`
- `nvidia-smi` 记录占用（未打断服务）
