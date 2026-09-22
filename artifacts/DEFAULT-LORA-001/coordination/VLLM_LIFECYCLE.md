# VLLM LIFECYCLE

- 当前 CodeLlama-13b-Instruct-hf 由 vLLM 托管（推理服务，port 8000）
- LoRA 训练 **不需要** vLLM；训练使用 LLaMA-Factory + PyTorch，只读基础模型
- 训练前需停止 vLLM 以释放 A6000 显存
- 训练后需恢复 vLLM 服务
- 管理方式：tmux session `vllm`（属主非本项目用户）
- AUTO_RESTART = NO
- stop/restart 具体命令与验证清单：已确认并保存在 LOCAL 私有 runbook
- 本轮 STATUS：NOT EXECUTED（未停止 vLLM）

禁止在本文写入任何 secret。
