# Agent Handoff System

每个新 Agent 会话在做任何事情前必须按顺序执行：

1. `cd /Users/sunyiyang/Desktop/Project/微调/`
2. 读取 `AGENTS.md`
3. 读取 `coordination/PROJECT_STATE.md`
4. 读取 `coordination/LAST_HANDOFF.md`
5. 读取 `coordination/NEXT_ACTION.md`
6. 读取 `coordination/REMOTE_RUNBOOK.md`
7. 如需 SSH：读取 `coordination/REMOTE_ACCESS.local.md`（本地私有，不入 Git）
8. 如涉及 vLLM：读取 `coordination/VLLM_RUNBOOK.local.md`（本地私有，不入 Git）
9. 连接 REMOTE-SERVER 做只读状态检查
10. 确认实际状态与文档一致后才能继续

任务完成后必须更新 `coordination/LAST_HANDOFF.md`。

## 项目硬约束

| 项 | 值 |
|---|---|
| Framework | LLaMA-Factory |
| Method | LoRA |
| Model | CodeLlama-13b-Instruct-hf（`/data/vllm/CodeLlama-13b-Instruct-hf`，READ ONLY） |
| Dataset | 1455 条（Assembly + Pseudocode → C/C++ Source） |
| Experiment ID | DEFAULT-LORA-001 |

不需要：benchmark、test set、Base vs LoRA comparison。

最终目标：完成 LoRA 微调，并记录 Token、wall time、loss、steps、throughput、VRAM、adapter/checkpoint。

## 训练参数已冻结（不得自行修改）

- template = llama2
- cutoff_len = 2048
- packing = false
- lora_rank = 8
- lora_alpha = 16
- lora_dropout = 0
- lora_target = all
- num_train_epochs = 3
- learning_rate = 5e-5
- per_device_train_batch_size = 2
- gradient_accumulation_steps = 8
- effective batch = 16
- bf16 = true
- gradient checkpointing = ENABLED
- training samples = 1455 / validation = 0 / test = 0

Token 口径（已冻结）：

- Input tokens / epoch = 1,411,053
- Output tokens / epoch = 263,850
- Total tokens / epoch = 1,674,903
- 3 Epoch Total Training Tokens = 5,024,709
- Optimizer steps = 273

## 写入边界

- REMOTE 唯一可写：`$HOME/codellama-lora/**`
- Base model 目录只读
- 禁止提交 GitHub：`coordination/*.local.md`、IP/密码/密钥/token/secret、Fine-Tuning.json、模型、venv、checkpoint、大型 log

## Git

- LOCAL：`/Users/sunyiyang/Desktop/Project/微调/`
- Remote：`https://github.com/sxyq/CodeLlama-.git` branch `main`
