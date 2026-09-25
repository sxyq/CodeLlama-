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

- **当前状态（2026-09-25，UNIFIED-MODEL-DEPLOY-001）：vLLM 已停止，port 8000 CLOSED**（SIGTERM 干净退出，配置未改）
- 历史：由 tmux session `vllm` 托管 CodeLlama-13b（`qwen3-5.yaml`，port 8000）
- 停止/恢复命令细节：`coordination/VLLM_RUNBOOK.local.md`（本地私有）
- AUTO_RESTART = NO；恢复需 Commander 授权
- LoRA 训练 **不需要** vLLM（LLaMA-Factory + PyTorch 直接读基础模型）

## AI Serving（2026-09-25 起）

| 对象 | 位置/端口 |
|---|---|
| 统一 Serving 目录 | `$HOME/ai-serving/`（configs / services / scripts / state / logs / env） |
| Image 服务 | port **8011**（FastAPI，lazy load，idle 600s；启动：`env/image/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8011`，cwd=`services/image`） |
| Image API 端点 | `GET /health` `GET /status` `POST /v1/images/generations` **`POST /v1/images/edits`（multipart 图生图，无 mask/strength）** `POST /unload` |
| Zrald 文本服务 | port **8010**（llama.cpp 管理器，ctx 32768，按需启动 8012 后端，idle 600s SIGTERM；启动：`python3 $HOME/ai-serving/services/zrald/zrald_lease_manager.py`） |
| Ollama Zrald duplicate | 已于 2026-09-26 E2E 验证后删除（`ollama rm qwen3.8-27b-zrald-accuracy`，回收≈16GB；/data 源 GGUF 未动） |
| 统一 GPU lease | `$HOME/ai-serving/state/gpu.lock`（flock 原子锁，Image 与 Zrald 共用；Ollama 直连客户端不受约束） |
| Image 模型 | `/data/vllm/ImageModel/Qwen-Image-2.1`（diffusers，local_files_only） |
| Zrald GGUF | `/data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf`（已导入 Ollama alias `qwen3.8-27b-zrald-accuracy`；**推理暂受引擎限制**） |
| Ollama | port 11434，systemd `ollama.service`，internal store 由 Ollama 自管 |
| Open WebUI | port 3000 |

常用只读核验：

```bash
curl -sS http://127.0.0.1:11434/api/tags
curl -sS http://127.0.0.1:8011/health
curl -sS http://127.0.0.1:8011/status
nvidia-smi
```

## 禁止写入本文

IP 以外的任何凭据；SSH 细节仅在 `REMOTE_ACCESS.local.md`。
