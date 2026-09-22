# DEFAULT-LORA-001 Formal Training Result

## 0. Status

SUCCESS

- TRAIN_EXIT_CODE = 0
- 3 epoch 完成
- global_step = 273（期望 273）
- adapter 已保存
- 未执行 benchmark / 效果对比

说明：训练结束后出现未授权的 run_training.sh 反复重拉起，覆盖了 output 根目录的 metrics/logs。adapter 已从 `checkpoint-273` 恢复（SHA256 一致）。下列计时取自首次真实训练。

## 1. Configuration

| 项 | 值 |
|---|---|
| stage | sft |
| finetuning_type | lora |
| template | llama2 |
| cutoff_len | 2048 |
| packing | false |
| train_on_prompt | false |
| lora_rank | 8 |
| lora_alpha | 16 |
| lora_dropout | 0 |
| lora_target | all |
| learning_rate | 5e-5 |
| num_train_epochs | 3 |
| per_device_train_batch_size | 2 |
| gradient_accumulation_steps | 8 |
| effective batch | 16 |
| lr_scheduler_type | cosine |
| bf16 | true |
| gradient checkpointing | ENABLED |
| seed | 42 |
| Framework | LLaMA-Factory 0.9.6.dev0 |
| Commit | 97b32d3133b501432141a82949d5c7bc4d94f23a |
| Trainable params | 31,293,440 |
| All params | 13,047,321,600 |
| Trainable % | 0.2398 |

## 2. Dataset

- samples = 1455
- dataset_sha256 = 28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6
- validation = 0 / test = 0

## 3. Token Accounting

| 口径 | Input | Output | Total |
|---|---:|---:|---:|
| Raw | 1,444,375 | 262,395 | 1,706,770 |
| Effective (pre-cutoff) | 1,456,015 | 263,850 | 1,719,865 |
| Per epoch (post 2048 cutoff) | 1,411,053 | 263,850 | 1,674,903 |
| 3 Epoch | 4,233,159 | 791,550 | 5,024,709 |

Loss-bearing tokens (3E) = 791,550

## 4. Training Runtime

| 项 | 值 |
|---|---|
| Start | 2026-09-22T20:47:56+08:00 |
| End | 2026-09-22T23:17:45+08:00 |
| TOTAL_WALL_SECONDS | 8,989（约 2h 29m 49s） |
| train_runtime | 8,905（2:28:25，来自 trainer_log.jsonl） |

主口径：TOTAL_WALL_SECONDS = 8989。附：train_runtime = 8905。

## 5. Training Progress

| 项 | 值 |
|---|---|
| Epochs completed | 3.0 |
| Global steps | 273 |
| Train Loss | 未记录（logging_steps=500 > max_steps=273，log_history 为空） |
| Samples/sec | 0.4902 |
| Steps/sec | 0.03066 |
| total_flos | 4.861465323474125e+17 |

## 6. GPU

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX A6000 (49140 MiB) |
| Peak VRAM used | 32,188 MiB |
| Minimum free VRAM | 16,352 MiB |
| Average utilization | 100% |
| Max utilization | 100% |
| Max temperature | 84 C |
| Max power | 298.51 W |

GPU 数据来自训练期间实时观测（原 gpu_monitor.csv 被重拉起覆盖）。

## 7. Artifacts

| 项 | 路径 |
|---|---|
| Adapter path | /home/syy/codellama-lora/outputs/default_baseline_lora |
| adapter_model.safetensors | 125,248,064 bytes |
| adapter SHA256 | 191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9 |
| Checkpoint | /home/syy/codellama-lora/outputs/default_baseline_lora/checkpoint-273 |

## 8. vLLM Lifecycle

| 项 | 值 |
|---|---|
| Stopped before training | YES |
| Restored after training | NO（待 sudo 恢复） |
| Health | pending |
| Models endpoint | pending |

## 9. Final

No benchmark performed.
No Base vs LoRA comparison performed.
No second experiment performed.
