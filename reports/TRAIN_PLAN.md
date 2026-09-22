# CodeLlama LoRA Training Plan

任务编号：TRAIN-CONFIG-001  
Experiment ID：**DEFAULT-LORA-001**  
生成时间：2026-09-22  
状态：TRAIN_CONFIG_READY = YES；TRAINING_STARTED = NO

## Experiment

| 项 | 值 |
|---|---|
| ID | DEFAULT-LORA-001 |
| Base model | `/data/vllm/CodeLlama-13b-Instruct-hf`（READ ONLY） |
| Framework | LLaMA-Factory `0.9.6.dev0` |
| Commit | `97b32d3133b501432141a82949d5c7bc4d94f23a` |
| Method | LoRA SFT |
| Workspace | `$HOME/codellama-lora` |

## Objective

仅完成 LoRA 微调并记录训练过程数据（token / time / loss / step / throughput / VRAM / adapter）。

明确：

```text
NO BENCHMARK
NO BASE-VS-LORA COMPARISON
NO TEST SET
NO VALIDATION SPLIT
```

## Dataset

| 项 | 值 |
|---|---|
| 注册名 | `codellama_asm_pseudo_to_cpp` |
| 注册文件 | `$HOME/codellama-lora/configs/datasets/dataset_info.json` |
| 数据文件 | `$HOME/codellama-lora/data/Fine-Tuning.json`（原文件只读，注册侧 symlink） |
| SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| training samples | **1455** |
| validation samples | **0** |
| test samples | **0** |
| format | sharegpt / conversations / human→gpt |
| 官方 `LLaMA-Factory/data/dataset_info.json` | **未修改** |

DATASET MODIFIED = NO

## Token Accounting

### A. Raw Dataset Tokens

| 口径 | Tokens |
|---|---:|
| RAW_INPUT_TOKENS | 1,444,375 |
| RAW_OUTPUT_TOKENS | 262,395 |
| RAW_TOTAL_TOKENS | 1,706,770 |

### B. Effective Dataset Tokens（template=`llama2`，未截断）

| 口径 | Tokens |
|---|---:|
| EFFECTIVE_INPUT / PROMPT | 1,456,015 |
| EFFECTIVE_OUTPUT / RESPONSE | 263,850 |
| EFFECTIVE_TOTAL | 1,719,865 |
| LOSS_BEARING（train_on_prompt=false） | 263,850 |

### C. cutoff_len=2048 Processed Tokens Per Epoch

实际 preprocessing（`llama2.encode_oneturn` + `infer_seqlen`，与 LLaMA-Factory supervised 路径一致）后：

| 口径 | Per Epoch |
|---|---:|
| TRAIN_INPUT_CONTEXT_TOKENS_PER_EPOCH | 1,411,053 |
| TRAIN_OUTPUT_RESPONSE_TOKENS_PER_EPOCH | 263,850 |
| TRAIN_TOTAL_TOKENS_PER_EPOCH | 1,674,903 |
| LOSS_BEARING_TOKENS_PER_EPOCH | 263,850 |
| truncated samples | 118 / 1455（8.11%） |
| response truncated | 0 |

### D. 3 Epoch Total Token Presentations

同一 token 在 3 个 epoch 中被处理 3 次：

| 口径 | 3 Epochs |
|---|---:|
| TRAIN_INPUT_CONTEXT_TOKENS_TOTAL_3E | 4,233,159 |
| TRAIN_OUTPUT_RESPONSE_TOKENS_TOTAL_3E | 791,550 |
| TRAIN_TOTAL_TOKEN_PRESENTATIONS_3E | 5,024,709 |
| LOSS_BEARING_TOKEN_PRESENTATIONS_3E | 791,550 |

说明：

- **Dataset Token Count** = 去重语料规模（A/B 口径）。
- **Training Token Presentations** = 训练循环实际处理次数（C×3 = D）。
- 二者不可混用。

## Training Configuration

| 参数 | 值 | 来源 |
|---|---|---|
| stage | sft | 显式 YAML |
| do_train | true | 显式 YAML |
| finetuning_type | lora | 显式 YAML |
| template | llama2 | 显式 YAML |
| dataset | codellama_asm_pseudo_to_cpp | 显式 YAML |
| dataset_dir | `$HOME/codellama-lora/configs/datasets` | 显式 YAML |
| cutoff_len | 2048 | 默认基线，显式 YAML |
| packing | false | 默认基线，显式 YAML |
| neat_packing | false | 显式 YAML |
| train_on_prompt | false | 默认基线，显式 YAML |
| mask_history | false | 显式 YAML |
| learning_rate | 5e-5 | 默认基线，显式 YAML |
| num_train_epochs | 3.0 | 默认基线，显式 YAML |
| per_device_train_batch_size | 2 | 默认基线，显式 YAML |
| gradient_accumulation_steps | 8 | 默认基线，显式 YAML |
| lr_scheduler_type | cosine | 默认基线，显式 YAML |
| lora_rank | 8 | 默认基线，显式 YAML |
| lora_alpha | 16 | 默认基线，显式 YAML |
| lora_dropout | 0 | 默认基线，显式 YAML |
| lora_target | all | 默认基线，显式 YAML |
| bf16 | true | 默认基线（WebUI compute_type），显式 YAML |
| val_size | 0 | 默认基线，显式 YAML |
| seed | 42 | 显式 YAML |
| **Gradient checkpointing** | **ENABLED** | LF `disable_gradient_checkpointing: false`（默认） |
| Control field | `disable_gradient_checkpointing` | `ModelArguments` |
| Default value | `false` | 保持 |
| Final value | `false` | 显式 YAML |
| trust_remote_code | 删除（默认 false） | CodeLlama 无需 remote code |
| preprocessing_num_workers | 删除（默认 None） | 非必需 |
| plot_loss | 删除（默认 false） | loss 走 trainer log / metrics |
| output_dir | `$HOME/codellama-lora/outputs/default_baseline_lora` | 显式 YAML |
| logging_dir | `$HOME/codellama-lora/logs/training/default_baseline_lora` | 显式 YAML |

主配置文件：`$HOME/codellama-lora/configs/training/default_baseline_lora.yaml`  
字段差异审计：`$HOME/codellama-lora/reports/CONFIG_DIFF.md`

## Batch / Steps

| 项 | 值 |
|---|---|
| micro batch size | 2 |
| gradient accumulation | 8 |
| effective batch size | **16** |
| samples | 1455 |
| last micro-batch size | 1 |
| micro steps per epoch | **728** = ceil(1455/2) |
| optimizer steps per epoch | **91** = ceil(728/8) |
| total optimizer steps（3 epochs） | **273** |

计算方法（与当前 Transformers Trainer 行为对齐）：

1. `dataloader_drop_last=false`：最后一个不完整 micro batch（1 条）保留，micro steps = ceil(1455/2)=728。
2. 梯度累积按 micro batch 计数；728 能被 8 整除（728=91×8），**无残留累积组**。
3. 即便存在残留，HF Trainer 会在 epoch 结束时对未满的 accumulation group 执行一次 `optimizer.step()`（本实验未触发）。
4. 总 optimizer steps = 91 × 3 = **273**（依据 `num_train_epochs=3` 的多次完整 epoch 遍历）。

## Training Metrics To Record

正式训练时必须采集：

| 类别 | 字段 |
|---|---|
| Token | raw in/out/total；effective in/out/total；train in/out/total per epoch 与 3E；loss-bearing |
| Time | `START_TIME_ISO` / `END_TIME_ISO` / `TOTAL_WALL_SECONDS`（真实 wall-clock）；`train_runtime` |
| Loss | `train_loss`；log_history |
| Step | `global_step` / optimizer steps=273；epoch |
| Throughput | `train_samples_per_second` / `train_steps_per_second`；可选 `train_flos` |
| VRAM | 训练前/中/后 `nvidia-smi`；`torch.cuda.max_memory_allocated` / `max_memory_reserved` |
| Artifact | adapter / checkpoint path；trainer_state.json；train_results.json；完整 stdout/stderr |
| Learning rate | 训练日志中的 learning_rate |

采集脚本：`$HOME/codellama-lora/scripts/collect_training_metrics.py`  
输出计划：`$HOME/codellama-lora/reports/TRAINING_METRICS.json`

## Training Launcher

`$HOME/codellama-lora/scripts/run_training.sh`（本轮 **未运行**）

流程：source env → activate venv → 记录 START → nvidia-smi → `llamafactory-cli train` → 记录 END / wall seconds / exit code → nvidia-smi → 调用 metrics collector。

## Static Validation

| 项 | 结果 |
|---|---|
| YAML 可解析 | PASS |
| 关键参数名称/值 | PASS |
| dataset registration | PASS |
| 1455 条可加载 | PASS |
| sharegpt → user/assistant 对齐 | PASS |
| llama2 preprocessing | PASS |
| cutoff_len=2048 预处理统计 | PASS |
| samples 仍为 1455 | PASS |
| CONFIG STATIC VALIDATION | **PASS** |

证据文件：`$HOME/codellama-lora/reports/train_token_accounting.json`

## Current Resource Blocker

- 1×NVIDIA RTX A6000；vLLM 持续占用约 43662 MiB。
- 当前空闲显存约 4574 MiB。
- **MEMORY FIT = UNVERIFIED**（本轮禁止加载 13B 权重实测）。
- GPU_READY = **NO**

## Before Training

仅剩：

1. 释放/迁移 vLLM 占用，使 GPU 具备 13B + LoRA 训练余量（或改用完整空闲卡）。
2. Commander 确认后执行 `run_training.sh`。

本轮不执行训练。
