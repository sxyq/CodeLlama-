# Pre-Training Server Audit

任务编号：GPU-RELEASE-AUDIT-001  
时间：2026-09-22T20:06:00+08:00

## vLLM

| 项 | 值 |
|---|---|
| STOP_AUTHORIZED_BY_USER | YES |
| STOP_EXECUTION_PERMISSION | **NO** |
| Stopped | **NO**（kill 被拒绝） |
| Port 8000 | **LISTENING** |
| Remaining processes | YES（主 2570949 / resource_tracker 2571459 / EngineCore 2571460） |
| Owner | yuyong |
| Model match | YES（`/data/vllm/CodeLlama-13b-Instruct-hf/`） |

权限证据：

- `kill 2570949` → 不允许的操作
- `os.kill` 信号探测 → PERMISSION_DENIED
- `sudo -n` → 需要密码
- `su yuyong` → 认证失败（禁止猜密码）
- SSH `yuyong@…` / `root@…`（已有密钥）→ Permission denied
- 未使用任何未授权凭据，未改 sudoers

## GPU

| 项 | 值 |
|---|---|
| Model | NVIDIA RTX A6000 |
| Total VRAM | 49140 MiB |
| Used | 43966 MiB |
| Free | 4574 MiB |
| Utilization | 0% |
| Driver / CUDA | 580.159.03 / 13.0 |

GPU processes：Xorg 4MiB；gnome-remote-desktop 266MiB；VLLM::EngineCore 43662MiB。  
UNKNOWN_GPU_PROCESS_COUNT = 0（均识别）

## CPU / RAM

见远程 `free -h` / `uptime` / top 内存进程（审计时记录于命令输出）。

## Disk

`$HOME/codellama-lora` 所在根卷约 3.5T，可用约 1.4T；workspace 目录已 `du -sh`。

## Training Environment

| 项 | 状态 |
|---|---|
| Python | `$HOME/codellama-lora/.venv` |
| PyTorch | 2.14.0+cu126，CUDA available True |
| Device | NVIDIA RTX A6000 |
| LLaMA-Factory | 0.9.6.dev0 @ 97b32d3… |

## Workspace

Dataset / YAML / Launcher / Monitor / Metrics / reports / outputs / logs / coordination：见核对列表。

## Output Directory

`outputs/default_baseline_lora` 不存在 → **OUTPUT_DIR_CLEAN = YES**

## Final Readiness

| 项 | 值 | 原因 |
|---|---|---|
| GPU_READY | **NO** | vLLM 仍占用约 43.7GB |
| TRAINING_PREFLIGHT_READY | **NO** | GPU 未释放；stop 执行权限不足 |
| TRAINING_STARTED | NO | 本轮禁止训练 |
| VLLM_RESTORED | NO | 本轮未停止，无需恢复 |
