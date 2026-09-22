# CodeLlama LoRA 微调项目——当前状态

任务编号：CONFIG-FINALIZE-001 完成后更新  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | **TRAINING CONFIGURATION FINALIZATION** |
| Experiment ID | DEFAULT-LORA-001 |
| TRAIN_CONFIG_READY | **YES** |
| DEFAULT_BASELINE_VERIFIED | **YES** |
| TRAINING_STARTED | **NO** |
| GPU_READY | **NO** |
| NON_DEFAULT_WITHOUT_REASON | **0** |
| Token accounting changed | NO |
| Optimizer steps changed | NO |
| Training samples | 1455 |
| Validation / Test | 0 / 0 |
| Base model / Dataset | 未修改 |
| vLLM | 未受影响 |

## 1. Gradient Checkpointing（已校正）

| 项 | 值 |
|---|---|
| LLaMA-Factory Gradient Checkpointing | **ENABLED** |
| Default | **YES** |
| Control field | `disable_gradient_checkpointing` |
| Default / Final | `false` / `false` |
| HF `gradient_checkpointing` | 不写入 YAML |
| 源码 | `checkpointing.py`：`if not model_args.disable_gradient_checkpointing` → enable |

## 2. 最终 YAML

`configs/training/default_baseline_lora.yaml`

核心参数保持：sft / lora / llama2 / cutoff 2048 / packing false / train_on_prompt false / lr 5e-5 / epochs 3 / batch 2 / accum 8 / cosine / rank 8 / alpha 16 / dropout 0 / target all / bf16 / val_size 0 / seed 42。

已删除非必要字段：`trust_remote_code`、`preprocessing_num_workers`、`plot_loss`、`gradient_checkpointing`、`overwrite_output_dir`、`warmup_*`、`optim`、`logging_steps`、`save_steps` 等。详见 `reports/CONFIG_DIFF.md`。

## 3. Token / Steps（未变）

| 口径 | Input | Output | Total |
|---|---:|---:|---:|
| Train / epoch（2048 后） | 1,411,053 | 263,850 | 1,674,903 |
| 3E presentations | 4,233,159 | 791,550 | 5,024,709 |

Optimizer steps = **273**

## 4. 确认项

```text
TRAINING STARTED = NO
GPU MODEL LOADED = NO
VLLM AFFECTED = NO
DATASET MODIFIED = NO
BASE MODEL MODIFIED = NO
TOKEN ACCOUNTING CHANGED = NO
OPTIMIZER STEPS CHANGED = NO
NON_DEFAULT_WITHOUT_REASON = 0
```

## 5. Blocking Issues

1. GPU 显存被 vLLM 占用（GPU_READY = NO）。
2. MEMORY FIT = UNVERIFIED。

## 6. 下一步

Commander 确认后执行 `scripts/run_training.sh`（本轮未运行）。
