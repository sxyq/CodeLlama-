# NEXT_ACTION

Updated At: 2026-09-22  
Current Phase: **VLLM Lifecycle / GPU Resource Preparation**

Next Action（顺序执行）：

1. Commander 审核 vLLM stop/restart 方案（见私有 `VLLM_RUNBOOK.local.md`）
2. 停止 vLLM（Graceful Stop，禁止默认 `kill -9`）
3. 确认 A6000 显存释放（`nvidia-smi`）
4. 运行 `bash $HOME/codellama-lora/scripts/run_training.sh`（DEFAULT-LORA-001）
5. 训练结束后恢复 vLLM 并执行 POST_RESTART_VALIDATION
6. 更新 `LAST_HANDOFF.md` / `PROJECT_STATE.md`，确认 `TRAINING_METRICS.json`

步骤 2 与 4 需 Commander 明确授权后执行。
