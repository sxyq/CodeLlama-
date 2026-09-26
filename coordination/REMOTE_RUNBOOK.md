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
| 统一 Serving 目录 | `$HOME/ai-serving/`（configs / services / scripts / state / logs / env / webui / tmp） |
| Image 服务 | port **8011**（FastAPI，lazy load，idle 600s；启动：`bash $HOME/ai-serving/scripts/image/start_image_service.sh`，内部 source `configs/image/service.local.env` 后 uvicorn） |
| Image API 端点 | `GET /health` `GET /status`（含 queue.running/pending/max_pending） `POST /v1/images/generations`（含 `b64_json`） **`POST /v1/images/edits`（multipart，字段 `image` 或 `image[]`，`size=auto` 保持原尺寸，无 mask）** `POST /unload` |
| Image 统一队列 | `services/image/queue_manager.py`：max_concurrent=1 / max_pending=8 / timeout=480s；超限 429 `QUEUE_FULL`；与 gpu.lock 顺序：queue → flock → 推理 |
| Image 临时输出 | `$HOME/ai-serving/tmp/image-output/`（TTL 1800s，300s 扫描，启动即扫；env：`IMAGE_OUTPUT_RETENTION_SECONDS` / `IMAGE_CLEANUP_INTERVAL_SECONDS`） |
| Image CORS | env `IMAGE_ALLOWED_ORIGINS`（逗号分隔精确 origin，**代码内无真实 IP**；真实值仅在 `service.local.env`，永不入 Git） |
| WebUI 图像平台 | port **8020**（`webui/image-platform/scripts/serve_static.py` 服务 `dist/`；构建：`bash scripts/build_webui.sh`，Node 于 `env/node-v22.23.3-linux-x64/`） |
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
curl -sS http://127.0.0.1:8011/status     # 含 queue.{running,pending,max_pending}
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8020/
curl -sS http://127.0.0.1:11434/api/ps    # 有 >1GB size_vram 模型时 Image 冷加载会 503 GPU_BUSY
nvidia-smi
```

注意：

- LAN 客户端会周期调用 `/api/embed`，`qwen3-embedding:8b` 可能长期驻留 ~14.4GB；Image 需加载的测试要抓 `/api/ps` 空闲窗口，不绕开该保护。
- 杀进程勿用 `pkill -f "uvicorn server:app"`（会误杀含同串的自身会话）；用 `pgrep -f "[s]erver:app"` 取 PID 后 kill，并与启动分两次会话。

## 禁止写入本文

IP 以外的任何凭据；SSH 细节仅在 `REMOTE_ACCESS.local.md`。
