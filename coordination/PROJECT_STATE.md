# PROJECT_STATE

更新时间：2026-09-22（HANDOFF-VLLM-AUDIT-001）

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | **VLLM PERMISSION GATE — BLOCKED**（FORMAL-TRAIN-001） |
| Framework | LLaMA-Factory `0.9.6.dev0` @ `97b32d3133b501432141a82949d5c7bc4d94f23a` |
| Method | LoRA SFT |
| Objective | 全量 1455 条微调 + 训练指标记录（无 benchmark / test / 对比） |

## 已完成任务

1. STATUS-AUDIT-RESET-001 环境审计
2. ENV-WORKSPACE-001 工作区与训练环境
3. TOKEN-AUDIT-001 Token / cutoff / 泄漏
4. TRAIN-CONFIG-001 默认 LoRA 配置
5. CONFIG-FINALIZE-001 严格默认基线校正
6. HANDOFF-VLLM-AUDIT-001 交接体系 + vLLM 生命周期审计

## 训练参数（冻结）

llama2 / cutoff 2048 / packing=false / rank 8 / alpha 16 / dropout 0 / target all / 3 epoch / lr 5e-5 / batch 2 / accum 8 / effective batch 16 / bf16 / GC ENABLED / val 0 / test 0。

## Token / Steps（冻结）

| 口径 | Input | Output | Total |
|---|---:|---:|---:|
| / epoch | 1,411,053 | 263,850 | 1,674,903 |
| 3E presentations | 4,233,159 | 791,550 | 5,024,709 |

Optimizer steps = 273

## 路径

| 对象 | 路径 |
|---|---|
| REMOTE workspace | `$HOME/codellama-lora` |
| 模型 | `/data/vllm/CodeLlama-13b-Instruct-hf`（READ ONLY） |
| 数据 | `$HOME/codellama-lora/data/Fine-Tuning.json`（1455 条，SHA256 `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6`） |
| LLaMA-Factory | `$HOME/codellama-lora/LLaMA-Factory` |
| 训练 YAML | `$HOME/codellama-lora/configs/training/default_baseline_lora.yaml` |
| Launcher | `$HOME/codellama-lora/scripts/run_training.sh` |
| Metrics | `$HOME/codellama-lora/scripts/collect_training_metrics.py` |

## 运行状态

| 项 | 值 |
|---|---|
| TRAINING_STARTED | NO（权限门禁 FAIL，未开训） |
| GPU | 1×RTX A6000，vLLM 占用约 43662 MiB，空闲约 4574 MiB |
| GPU_RECLAIMABLE | YES |
| vLLM | RUNNING，model=CodeLlama-13b-Instruct-hf，port=8000，owner=`yuyong` |
| VLLM required for LoRA | NO |
| AUTO_RESTART | NO |
| 最后 Git commit | 见 `LAST_HANDOFF.md` |

## 标志

```text
TRAIN_CONFIG_READY = YES
DEFAULT_BASELINE_VERIFIED = YES
AGENT_HANDOFF_READY = YES
SSH_ACCESS_DOCUMENTED = YES
VLLM_LIFECYCLE_READY = YES
GPU_CURRENTLY_OCCUPIED = YES
GPU_RECLAIMABLE = YES
TRAINING_STARTED = NO
```


FORMAL-TRAIN-001: VLLM_PERMISSION_GATE=FAIL；STOP/RESTART_PERMISSION=NO；详见 LAST_HANDOFF.md。
