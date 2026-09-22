# CodeLlama LoRA 微调项目——当前状态

任务编号：FORMAL-LORA-RUN-001
更新时间：2026-09-22

| 项目 | 事实 |
|---|---|
| Current Phase | **FORMAL TRAINING COMPLETED** |
| TRAINING_STARTED | YES |
| TRAINING_COMPLETED | YES |
| TRAINING_STATUS | SUCCESS |
| TRAIN_EXIT_CODE | 0 |
| METRICS_COLLECTED | YES |
| LORA_ADAPTER_READY | YES |
| VLLM_STOPPED | YES |
| VLLM_RESTORED | NO（待 sudo） |
| PORT_8000 | NOT LISTENING |
| Epochs / Global steps | 3.0 / 273 |
| TOTAL_WALL_SECONDS | 8989 |
| train_runtime | 8905（2:28:25） |
| Train Loss | 未记录（logging_steps=500 > 273） |
| Peak VRAM | 32188 MiB |
| Adapter SHA256 | 191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9 |

训练期间曾出现未授权 run_training.sh 重拉起覆盖根目录 metrics/logs；已停止，adapter 自 checkpoint-273 恢复且 SHA 一致。

下一步：恢复 vLLM（需 sudo -u yuyong），验证 health / models。
