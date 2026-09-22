# ENV_INSTALL_PLAN

任务编号：ENV-WORKSPACE-001  
生成时间：2026-09-22T17:32:00+08:00  
依据：LLaMA-Factory 官方仓库 `pyproject.toml` / `README.md`（Installation、Requirement）

## Project root

`$HOME/codellama-lora`

## Python interpreter

- 选择：`/usr/bin/python3.12`（Python 3.12.3）
- 原因：LLaMA-Factory `pyproject.toml` 声明 `requires-python = ">=3.11.0"`，classifiers 覆盖 3.11 / 3.12 / 3.13。服务器已有 3.11.15 与 3.12.3；`python3.12` 具备 `venv`+`ensurepip`，`python3.11` 缺少 `ensurepip`，故选 3.12。
- 不使用系统 Python site-packages 作为安装目标。

## venv path

`$HOME/codellama-lora/.venv`

创建命令：

```bash
/usr/bin/python3.12 -m venv "$HOME/codellama-lora/.venv"
```

## LLaMA-Factory revision

| 项 | 值 |
|---|---|
| path | `$HOME/codellama-lora/LLaMA-Factory` |
| upstream | `https://github.com/hiyouga/LLaMA-Factory` |
| branch | `main` |
| git commit SHA | `97b32d3133b501432141a82949d5c7bc4d94f23a` |
| 源码版本串 | `0.9.6.dev0`（`src/llamafactory/extras/env.py`） |
| 获取方式 | codeload tarball of that exact SHA（完整 `git clone` 超时） |
| revision 文件 | `$HOME/codellama-lora/coordination/LLaMA-Factory.revision` |

安装方式（官方 Install from Source）：

```bash
pip install -e "$HOME/codellama-lora/LLaMA-Factory"
pip install -r "$HOME/codellama-lora/LLaMA-Factory/requirements/metrics.txt"
```

## 版本兼容依据（来自官方 pyproject.toml）

| 包 | 官方约束 | 本轮策略 |
|---|---|---|
| python | `>=3.11.0` | 3.12.3 |
| torch | `>=2.4.0` | 先装 GPU 版到 venv |
| torchvision | `>=0.19.0` | 随 torch 同索引安装 |
| torchaudio | `>=2.4.0` | 随 torch 同索引安装 |
| transformers | `>=4.55.0,<=5.8.0,!=4.57.0,!=5.6.0` | 由 LLaMA-Factory 依赖解析 |
| datasets | `>=2.16.0,<=4.0.0` | 同上 |
| accelerate | `>=1.3.0,<=1.11.0` | 同上 |
| peft | `>=0.18.0,<=0.18.1` | 同上 |
| tokenizers | （transformers 传递） | 随依赖安装 |
| safetensors | （显式依赖） | 随依赖安装 |
| sentencepiece | （显式依赖） | 随依赖安装 |

### PyTorch version

- 计划安装渠道：`https://download.pytorch.org/whl/cu126`
- 原因：官方 README「Install PyTorch」示例使用 `cu126`；当前 driver 580.x / nvidia-smi 报告 CUDA 13.0，可运行 CUDA 12.x 用户态库。不手写固定小版本号，由该索引解析，安装后回填实测版本。
- 实际安装版本：安装完成后写入 `reports/ENV_SETUP_STATUS.md`。

### Transformers / PEFT / Accelerate / Datasets 版本

不在安装前臆造具体版本号。全部须落在官方上下界内，安装后以 import 实测回填。

## 安装命令（顺序）

```bash
export PROJECT_ROOT="$HOME/codellama-lora"
export HF_HOME="$PROJECT_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/cache/huggingface/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/cache/huggingface/transformers"
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
export TMPDIR="$PROJECT_ROOT/cache/tmp"
export TOKENIZERS_PARALLELISM=false

/usr/bin/python3.12 -m venv "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/pip" install -U pip setuptools wheel
"$PROJECT_ROOT/.venv/bin/pip" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
"$PROJECT_ROOT/.venv/bin/pip" install -e "$PROJECT_ROOT/LLaMA-Factory"
"$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/LLaMA-Factory/requirements/metrics.txt"
```

## 将被修改的路径（全部位于项目工作区）

- `$HOME/codellama-lora/.venv/**`
- `$HOME/codellama-lora/LLaMA-Factory/**`（源码已放置；`pip -e` 可能写入构建元数据，仍在该目录内）
- `$HOME/codellama-lora/cache/pip/**`
- `$HOME/codellama-lora/cache/tmp/**`
- `$HOME/codellama-lora/cache/huggingface/**`（若依赖拉取子资源）
- `$HOME/codellama-lora/reports/**`
- `$HOME/codellama-lora/logs/**`（如记录 pip 日志）

## 明确不会修改的路径

- `/data/vllm/CodeLlama-13b-Instruct-hf/**`（READ ONLY）
- `/data/**` 其他内容
- 其他用户 home（含 vLLM/Ollama 所属环境）
- 现有 vLLM / Ollama 进程与服务
- `/usr/**`、`/opt/**`、`/etc/**`
- 系统 Python site-packages
- 系统 CUDA、NVIDIA driver
- `~/.bashrc`、`~/.zshrc`、`/etc/profile`
- `$HOME/codellama-lora/**` 以外的任何路径

## WRITE 目标确认

所有主动写入目标均位于：

`$HOME/codellama-lora/`

确认后才允许继续安装。
