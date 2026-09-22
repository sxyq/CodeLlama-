# CodeLlama LoRA 微调项目——当前状态

任务编号：GPU-RELEASE-AUDIT-001  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | **GPU RELEASE BLOCKED — STOP_EXECUTION_PERMISSION = NO** |
| Experiment ID | DEFAULT-LORA-001 |
| STOP_AUTHORIZED_BY_USER | YES |
| STOP_EXECUTION_PERMISSION | **NO** |
| VLLM_STOPPED | NO |
| PORT_8000 | LISTENING |
| GPU_RELEASED | NO |
| GPU_READY | NO |
| TRAINING_PREFLIGHT_READY | NO |
| TRAINING_STARTED | NO |
| OUTPUT_DIR_CLEAN | YES |

## 1. 停止尝试结果

- 实时 PID：主 `2570949`，EngineCore `2571460`，owner `yuyong`
- `kill 2570949`（SIGTERM）→ 不允许的操作
- 已有授权入口核查均不可用（sudo 需密码、su 失败、无 yuyong/root 公钥登录）
- 未猜密码、未改 sudoers、未 kill -9

## 2. 训练前审计

详见 `reports/SERVER_PRETRAIN_AUDIT.md`：

- Workspace 全套就绪（12G）
- Python/Torch/LLaMA-Factory 可用，CUDA True
- Dataset/YAML 正常；output dir 干净
- GPU 仍被 vLLM 占用 43662 MiB

## 3. Blocking Issues

1. **STOP_EXECUTION_PERMISSION = NO**（主阻塞）
2. GPU 未释放

## 4. 下一步

由 `yuyong` 或管理员执行 SIGTERM 停止 vLLM（或提供已授权执行方式）→ 确认释放 → 运行 `run_training.sh`。
