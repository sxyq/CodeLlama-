# CodeLlama LoRA 微调项目——当前状态

任务编号：HANDOFF-VLLM-AUDIT-001 完成后更新  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | **VLLM LIFECYCLE / HANDOFF READY** |
| Experiment ID | DEFAULT-LORA-001 |
| TRAIN_CONFIG_READY | YES |
| DEFAULT_BASELINE_VERIFIED | YES |
| AGENT_HANDOFF_READY | YES |
| SSH_ACCESS_DOCUMENTED | YES |
| VLLM_LIFECYCLE_READY | YES |
| GPU_CURRENTLY_OCCUPIED | YES |
| GPU_RECLAIMABLE | YES |
| TRAINING_STARTED | NO |
| vLLM stopped | NO（本轮未停止） |
| vLLM required for LoRA training | NO |

## 1. 交接体系

```text
AGENTS.md
coordination/
├── PROJECT_STATE.md
├── LAST_HANDOFF.md
├── NEXT_ACTION.md
├── REMOTE_RUNBOOK.md
├── REMOTE_ACCESS.local.md   # PRIVATE
└── VLLM_RUNBOOK.local.md    # PRIVATE
```

新 Agent 必须按 `AGENTS.md` 顺序读取后再行动。

## 2. vLLM 生命周期摘要

| 项 | 值 |
|---|---|
| VLLM_MODEL_MATCH | YES（CodeLlama-13b-Instruct-hf） |
| PID | 2570949 / EngineCore 2571460 |
| Owner | yuyong |
| Launch method | tmux `vllm` → zsh → `vllm serve --config qwen3-5.yaml` |
| Working directory | `/home/yuyong/vllm`（推断） |
| Python | `/home/yuyong/vllm/.venv` |
| Host / Port | 0.0.0.0:8000 |
| AUTO_RESTART | NO |
| Graceful stop / Restart | 方案已写入私有 runbook，NOT EXECUTED |
| POST_RESTART_VALIDATION | 已定义 |

## 3. 训练状态

```text
TRAINING_STARTED = NO
GPU MODEL LOADED = NO
TOKEN ACCOUNTING CHANGED = NO
OPTIMIZER STEPS = 273
```

## 4. Blocking Issues

1. A6000 被 vLLM 占用（可回收）。
2. MEMORY FIT = UNVERIFIED。
3. vLLM 属主为 `yuyong`，停止/恢复可能需要对应权限。

## 5. 下一步

见 `coordination/NEXT_ACTION.md`：审核 → 停 vLLM → 确认显存 → 训练 → 恢复 vLLM。
