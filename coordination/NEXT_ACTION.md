# NEXT_ACTION

Updated At: 2026-09-22  
Current Phase: **BLOCKED — VLLM Permission Gate**

FORMAL-TRAIN-001 已执行 preflight，但 **VLLM_PERMISSION_GATE = FAIL**：

- `syy` 不能向 `yuyong` 的 vLLM 发送信号（PERMISSION_DENIED）
- `sudo` 需要密码，禁止猜测
- 因此 **未停止 vLLM、未开始训练**

Next Action：

1. 提供可执行 stop/restart 的权限（以 `yuyong` 操作，或为 `syy` 配置明确授权且不依赖口令猜测）
2. 重新跑权限门禁：STOP_PERMISSION=YES 且 RESTART_PERMISSION=YES
3. 停止 vLLM → 确认 A6000 显存释放
4. `bash $HOME/codellama-lora/scripts/run_training.sh`
5. 训练后恢复 vLLM + POST_RESTART_VALIDATION
6. 产出 `FORMAL_TRAINING_RESULT.md` / `TRAINING_METRICS.json` 并更新交接

训练侧脚本（launcher / monitor / collector）已就绪，可在门禁通过后直接开跑。
