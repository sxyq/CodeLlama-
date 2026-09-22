# REMOTE_RUNBOOK

非敏感远程操作说明（可提交 Git）。禁止写入密码、私钥内容、token、secret。

## 路径

| 对象 | 路径 |
|---|---|
| REMOTE workspace | `$HOME/codellama-lora` |
| Base Model | `/data/vllm/CodeLlama-13b-Instruct-hf`（READ ONLY） |
| Dataset | `$HOME/codellama-lora/data/Fine-Tuning.json` |
| Python | `$HOME/codellama-lora/.venv` |
| LLaMA-Factory | `$HOME/codellama-lora/LLaMA-Factory` |
| Training config | `$HOME/codellama-lora/configs/training/default_baseline_lora.yaml` |
| Launcher | `$HOME/codellama-lora/scripts/run_training.sh` |
| Metrics collector | `$HOME/codellama-lora/scripts/collect_training_metrics.py` |

## 激活环境

```bash
source $HOME/codellama-lora/configs/project_env.sh
source $HOME/codellama-lora/.venv/bin/activate
```

## 常用只读命令

```bash
nvidia-smi
df -h
free -h
ps -eo pid,ppid,user,lstart,etime,args | grep -E "vllm|llamafactory" | grep -v grep
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/v1/models
```

## 训练启动（需 GPU 就绪且 Commander 批准）

```bash
bash $HOME/codellama-lora/scripts/run_training.sh
```

训练指标由 launcher 调用 `collect_training_metrics.py` 汇总到 `$HOME/codellama-lora/reports/TRAINING_METRICS.json`。

## vLLM 生命周期（公开摘要）

- 当前模型由 vLLM 托管（推理/托管服务）
- LoRA 训练 **不需要** vLLM（LLaMA-Factory + PyTorch 直接读基础模型）
- 训练前需释放 vLLM 显存；训练后需恢复服务
- 管理方式：tmux session `vllm`（细节见私有 runbook）
- stop/restart 具体命令与验证清单：仅本地 `coordination/VLLM_RUNBOOK.local.md`（历史方案；训练后已恢复，**当前勿再 stop/restart**）
- AUTO_RESTART = NO
- FINAL-PROJECT-CLOSEOUT-001 核验：health=200，models=OK；当前实例由 syy 启动、yuyong venv PATH/PYTHONPATH、`qwen3-5.yaml`

## 禁止写入本文

IP 以外的任何凭据；SSH 细节仅在 `REMOTE_ACCESS.local.md`。
