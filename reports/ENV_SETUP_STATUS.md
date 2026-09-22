# ENV_SETUP_STATUS

任务编号：ENV-WORKSPACE-001  
审计/执行时间：2026-09-22  
平台：LOCAL-MAC 整理；REMOTE-SERVER 落地

## Workspace

REMOTE project root：

`$HOME/codellama-lora`

directory structure：

```text
$HOME/codellama-lora/
├── .venv/
├── LLaMA-Factory/
├── data/
│   └── Fine-Tuning.json          # 只读原始数据
├── configs/
│   └── project_env.sh
├── scripts/
├── logs/
│   └── env_install.log
├── outputs/
├── reports/
│   ├── ENV_INSTALL_PLAN.md
│   └── ENV_SETUP_STATUS.md 镜像（本文件同步至 LOCAL Git）
├── coordination/
│   └── LLaMA-Factory.revision
├── cache/
│   ├── huggingface/
│   ├── pip/
│   └── tmp/
├── README.md
└── WORKSPACE_POLICY.md
```

## Write Boundary

唯一可写范围：

`$HOME/codellama-lora/**`

项目 shell 环境变量写在：

`$HOME/codellama-lora/configs/project_env.sh`

未写入 `~/.bashrc`、`~/.zshrc`、`/etc/profile`。

## Base Model

| 项 | 值 |
|---|---|
| path | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| policy | READ ONLY |
| MODEL_READABLE | YES |
| TOKENIZER_READABLE | YES |
| model_type | `llama` |
| torch_dtype | `bfloat16` |
| max_position_embeddings | 16384 |
| Base model modified | NO |

**DO NOT MODIFY BASE MODEL DIRECTORY.**

## Dataset

| 项 | 值 |
|---|---|
| LOCAL path | `/Users/sunyiyang/Desktop/Project/微调/data/Fine-Tuning.json` |
| REMOTE path | `$HOME/codellama-lora/data/Fine-Tuning.json` |
| LOCAL SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| REMOTE SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| sample count | 1455 |
| JSON | 合法 list；1455 条 `conversations`；`human`/`gpt` 各 1455 |
| unique input | 1406 |
| unique output | 51 |
| full-pair 重复 | 49 |
| size | 3318956 bytes |
| MATCH | **YES** |
| REMOTE 权限 | `444`（只读原始数据） |

说明：本地原始文件名为 `Fine-Tuning(1).json`，已放置为规范路径 `data/Fine-Tuning.json` 后上传；两侧字节一致。

## Python Environment

| 项 | 值 |
|---|---|
| path | `$HOME/codellama-lora/.venv` |
| version | Python 3.12.3 |
| base interpreter | `/usr/bin/python3.12`（只读来源，未改装系统环境） |

## PyTorch

| 项 | 值 |
|---|---|
| version | `2.14.0+cu126` |
| CUDA availability | True |
| torch CUDA build | 12.6 |
| device name | NVIDIA RTX A6000 |

## LLaMA-Factory

| 项 | 值 |
|---|---|
| path | `$HOME/codellama-lora/LLaMA-Factory` |
| version | `0.9.6.dev0` |
| git commit | `97b32d3133b501432141a82949d5c7bc4d94f23a` |
| branch | `main` |
| revision 文件 | `$HOME/codellama-lora/coordination/LLaMA-Factory.revision` |
| CLI | `llamafactory-cli version` 可运行 |
| 安装方式 | `pip install -e` + `requirements/metrics.txt` |

## Dependencies

| 包 | 版本 | 状态 |
|---|---|---|
| Transformers | 5.8.0 | FOUND |
| PEFT | 0.18.1 | FOUND |
| Accelerate | 1.11.0 | FOUND |
| Datasets | 4.0.0 | FOUND |
| Tokenizers | 0.22.2 | FOUND |
| Safetensors | 0.8.0 | FOUND |
| SentencePiece | import 成功 | FOUND |

以上版本落在 LLaMA-Factory 官方 `pyproject.toml` 约束内。

## GPU

仅记录当前状态：

| 项 | 值 |
|---|---|
| GPU | 1×NVIDIA RTX A6000 |
| total | 49140 MiB |
| used | 43966 MiB |
| free | 4574 MiB |
| util | 0% |
| 占用 | VLLM::EngineCore 43662 MiB；gnome-remote-desktop 266 MiB |

**GPU TRAINING NOT STARTED**

## Verification

| 项 | 结果 |
|---|---|
| Workspace ready | YES |
| Dataset ready | YES（SHA256 一致，1455 条） |
| Python ready | YES（`.venv` / 3.12.3） |
| LLaMA-Factory ready | YES（0.9.6.dev0 @ 97b32d3） |
| Base model readable | YES |
| Training started | **NO** |

```text
TRAINING_STARTED = NO
BASE_MODEL_MODIFIED = NO
VLLM_AFFECTED = NO
OLLAMA_AFFECTED = NO
ENV READY = YES
```

## 未执行事项

- 未进行 LoRA / smoke training / benchmark
- 未停止 vLLM / Ollama
- 未加载 13B 模型到 GPU 做训练或完整推理
- 未修改基础模型
- 未生成最终 LoRA 参数
- 未使用 sudo / apt / kill / systemctl
