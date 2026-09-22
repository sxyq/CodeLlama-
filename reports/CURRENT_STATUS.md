# CodeLlama LoRA 微调项目——当前状态

任务编号：TOKEN-AUDIT-001 完成后更新  
上一阶段：ENV-WORKSPACE-001  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | DATA / TOKEN AUDIT |
| 审计时间 | 2026-09-22 |
| 本地项目路径 | `/Users/sunyiyang/Desktop/Project/微调/` |
| Git 状态 | 分支 `main`，状态同步仓库 |
| 数据集状态 | 1455 条；LOCAL/REMOTE SHA256 一致 |
| 远程服务器是否确认 | CONFIRMED（REMOTE-SERVER） |
| 硬件类型 | NVIDIA GPU 1×RTX A6000 |
| 当前资源是否可用 | CONSTRAINED（vLLM 占用中） |
| LLaMA-Factory 状态 | READY（0.9.6.dev0 @ 97b32d3） |
| CodeLlama 状态 | READY + READ ONLY |
| Tokenizer | READY |
| Template | `llama2`（已解析） |
| TOKEN AUDIT READY | YES |
| TRAINING NOT STARTED | YES |
| 当前能否开始 LoRA | NO（显存占用 + 超参未由 Commander 终定） |
| 当前第一阻塞项 | 单卡几乎被 vLLM 占满 |

## 1. 实验固定要求

| 项 | 要求 |
|---|---|
| Base Model | CodeLlama-13B-Instruct-hf |
| Framework | LLaMA-Factory |
| Finetuning Method | LoRA |
| 任务方向 | Assembly Code + Pseudocode → C/C++ Source Code |
| 数据规模 | 1455 条 |

## 2. LOCAL-MAC 当前项目

### 2.1 Git

`main` → `https://github.com/sxyq/CodeLlama-.git`

### 2.2 项目目录

```text
/Users/sunyiyang/Desktop/Project/微调/
├── data/
│   ├── Fine-Tuning.json     # 不入 Git
│   └── README.md
├── reports/
│   ├── CURRENT_STATUS.md
│   ├── ENV_SETUP_STATUS.md
│   ├── TOKEN_AUDIT.md
│   └── token_stats.json
├── scripts/
│   ├── token_audit.py
│   └── run_token_audit.sh
└── .git/
```

### 2.3 已有文件

| 路径 | 用途 | 状态 |
|---|---|---|
| `reports/TOKEN_AUDIT.md` | Token / cutoff / 泄漏 / 默认参数审计 | 有效 |
| `reports/token_stats.json` | 机器可读统计 | 有效 |
| `scripts/token_audit.py` | 可复现审计脚本 | 有效 |
| `scripts/run_token_audit.sh` | 远程执行入口 | 有效 |
| `reports/ENV_SETUP_STATUS.md` | 环境准备结果 | 有效 |
| `data/Fine-Tuning.json` | 原始数据（不入 Git） | 只读 |

### 2.4 已有脚本和配置

正式 LoRA YAML：**NOT CONFIGURED**（待 Commander 参数）。  
远程已有 `configs/project_env.sh`、`WORKSPACE_POLICY.md`、`coordination/LLaMA-Factory.revision`。

### 2.5 数据集

| 项 | 值 |
|---|---|
| samples | 1455 |
| unique inputs | 1406 |
| unique outputs | 51 |
| duplicate full pairs | 49 |
| target groups | 51 |
| SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| DATASET_MATCH | YES |

### 2.6 已完成工作

1. 状态审计与远程工作区准备（ENV-WORKSPACE-001）。
2. CodeLlama raw + effective token 精确统计（TOKEN-AUDIT-001）。
3. cutoff 截断模拟（512–16384）。
4. target grouping / 函数名 / 泄漏风险分析。
5. LLaMA-Factory WebUI / dataclass / example YAML 默认参数审计。

## 3. REMOTE-SERVER

REMOTE TARGET = CONFIRMED。不记录 hostname / IP。

### 3.1 目标服务器确认过程

专用密钥只读/工作区写入验证完成。

### 3.2 系统信息

Ubuntu 24.04.4 LTS，kernel 6.8.0-87-generic x86_64。

### 3.3 存储和 RAM

RAM 376 GiB；根卷可用约 1.4 T。

### 3.4 GPU / NPU

1×NVIDIA RTX A6000，49140 MiB；审计前后 vLLM 仍占 43662 MiB。NPU：NOT FOUND。

### 3.5 当前占用进程

vLLM RUNNING（未改动）、Ollama RUNNING（未改动）。

```text
TRAINING_RUNNING = NO
TRAINING_STARTED = NO
GPU_MODEL_LOADED_BY_THIS_TASK = NO
VLLM_AFFECTED = NO
```

## 4. ML 环境

| 组件 | 版本 |
|---|---|
| Python | 3.12.3 @ `$HOME/codellama-lora/.venv` |
| PyTorch | 2.14.0+cu126 |
| CUDA available | True |
| Transformers | 5.8.0 |
| PEFT | 0.18.1 |
| Accelerate | 1.11.0 |
| Datasets | 4.0.0 |
| Tokenizers | 0.22.2 |
| Safetensors | 0.8.0 |

## 5. LLaMA-Factory

path：`$HOME/codellama-lora/LLaMA-Factory`  
version：`0.9.6.dev0`  
commit：`97b32d3133b501432141a82949d5c7bc4d94f23a`

Template：`llama2`（与 `tokenizer_config.json` 的 `chat_template` 同构）。  
pinned 源码无 `codellama` 专用 template 名。

## 6. CodeLlama-13B-Instruct-hf

path：`/data/vllm/CodeLlama-13b-Instruct-hf`  
READ ONLY。MODEL_READABLE = YES，TOKENIZER_READABLE = YES。  
Base model modified = NO。

## 7. Fine-Tuning 数据

LOCAL / REMOTE SHA256 一致：`28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6`  
DATASET_MATCH = YES  
明细见 `reports/TOKEN_AUDIT.md` / `reports/token_stats.json`。

## 8. 当前训练配置

```text
NOT CONFIGURED
```

最终 LoRA / 优化器参数 **NOT YET DECIDED**（本轮只记录框架默认值）。

## 9. 当前训练状态

```text
TRAINING_STARTED = NO
TOKEN AUDIT READY = YES
```

## 10. Readiness Matrix

| Component | Status | Evidence | Blocking Problem |
|---|---|---|---|
| Local project | READY | 报告 + 脚本 + 数据 | 无 |
| Dataset | READY | 1455 条，SHA256 一致 | 无 |
| SSH / Remote | READY | 已连通 | 无 |
| Hardware | CONSTRAINED | 空闲 4574 MiB | vLLM 占用 |
| Python env | READY | `.venv` | 无 |
| LLaMA-Factory | READY | 0.9.6.dev0 | 无 |
| CodeLlama | READY | 只读可访问 | 无 |
| Tokenizer / Token audit | READY | TOKEN-AUDIT-001 通过 sanity | 无 |
| LoRA configuration | NOT READY | 超参未终定 | 待 Commander |
| Training can start | NO | 显存 + 参数 | 见 Blocking Issues |
| TOKEN AUDIT READY | YES | — | — |

## 11. Blocking Issues

1. **单卡显存被 vLLM 占用**（空闲 4574 MiB）。
2. **LoRA / 训练参数未终定**（仅有框架默认值事实）。

## 12. 下一阶段建议

1. 处理 vLLM 显存占用或更换完整空闲设备。
2. Commander 基于 token/cutoff/泄漏事实决定序列长度与 LoRA 参数。
3. 再起草正式 LLaMA-Factory YAML 与数据划分（需按 target group 防泄漏）。
4. 显存方案确认后进入训练审批。

## 13. 审计轨迹（TOKEN-AUDIT-001 节选）

[LOCAL-MAC]
- 写入 `scripts/token_audit.py`、`scripts/run_token_audit.sh`
- 同步远程报告到 `reports/TOKEN_AUDIT.md`、`reports/token_stats.json`
- 更新 `reports/CURRENT_STATUS.md`
- `git push origin main`

[REMOTE-SERVER]
- 数据 SHA256 / 结构核对
- 只读加载 CodeLlama tokenizer（不加载 13B 权重）
- pinned 源码检索 template / 默认参数
- 执行 `run_token_audit.sh`（CPU）
- `nvidia-smi` 前后对照（vLLM 未受影响）
