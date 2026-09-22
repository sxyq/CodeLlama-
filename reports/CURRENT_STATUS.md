# CodeLlama LoRA 微调项目——当前状态

任务编号：FORMAL-TRAIN-001（preflight 后因权限门禁中止）  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | **VLLM PERMISSION GATE — BLOCKED** |
| Experiment ID | DEFAULT-LORA-001 |
| Preflight | 部分完成；权限门禁 FAIL |
| VLLM_PERMISSION_GATE | **FAIL** |
| STOP_PERMISSION | NO |
| RESTART_PERMISSION | NO |
| vLLM stop | NOT EXECUTED |
| GPU_CURRENTLY_OCCUPIED | YES |
| GPU_READY | NO |
| TRAINING_STARTED | NO |
| TRAINING_STATUS | NOT STARTED |
| OUTPUT_DIR_NOT_CLEAN | NO（输出目录不存在） |
| Launcher ready | YES |
| GPU monitor ready | YES |
| Metrics collector ready | YES |

## 1. 权限门禁证据

- `os.kill(vllm_pid, 0)` → `PERMISSION_DENIED`（`syy` → `yuyong` 进程）
- `kill -0` / 信号探测：不允许的操作
- `sudo -n true`：需要密码
- 禁止猜密码 / 改 sudoers / 提权绕过 → 按任务要求 **保持 vLLM 运行、不训练**

## 2. vLLM 身份（stop 前已复核）

Model match YES；served `codeellama-13b-instruct-hf`；host 0.0.0.0:8000；owner `yuyong`；tmux `vllm` → `vllm serve --config qwen3-5.yaml`；AUTO_RESTART=NO。

## 3. 已就绪（待门禁通过即可训）

- `run_training.sh`：可靠 TRAIN_EXIT_CODE、完整日志、GPU monitor
- `monitor_gpu.sh`：5s 采样 CSV
- `collect_training_metrics.py`：含 GPU 峰值/均值
- Token/Steps 基线未改（273 steps；3E tokens 5,024,709）

## 4. Blocking Issues

1. 无 stop/restart 权限（主阻塞）
2. GPU 仍被 vLLM 占用

## 5. 下一步

见 `coordination/NEXT_ACTION.md`。
