# Final Config vs Pinned Defaults

任务编号：CONFIG-FINALIZE-001  
Experiment ID：DEFAULT-LORA-001  
Pinned LLaMA-Factory commit：`97b32d3133b501432141a82949d5c7bc4d94f23a`  
配置文件：`$HOME/codellama-lora/configs/training/default_baseline_lora.yaml`

Type 含义：

- **EXACT_DEFAULT**：与 pinned dataclass / HF TrainingArguments 默认值完全一致
- **WEBUI_DEFAULT**：与 pinned WebUI 默认一致，且属于 DEFAULT-LORA-001 已确认基线
- **PROJECT_REQUIRED**：路径 / 数据注册 / 实验输出等必须指定的项目字段
- **NON_DEFAULT**：偏离默认且无必要（目标 = 0）

| Parameter | Pinned Default | Final | Type | Reason |
|---|---|---|---|---|
| model_name_or_path | （必填） | `/data/vllm/CodeLlama-13b-Instruct-hf` | PROJECT_REQUIRED | 只读基础模型路径 |
| stage | — | `sft` | PROJECT_REQUIRED | 实验阶段 |
| do_train | HF `False` | `true` | PROJECT_REQUIRED | 训练入口 |
| finetuning_type | — | `lora` | PROJECT_REQUIRED | 方法 |
| template | None | `llama2` | PROJECT_REQUIRED | 已解析模板 |
| dataset | None | `codellama_asm_pseudo_to_cpp` | PROJECT_REQUIRED | 数据注册名 |
| dataset_dir | `data` | `$HOME/codellama-lora/configs/datasets` | PROJECT_REQUIRED | 本项目注册目录 |
| output_dir | （必填） | `.../outputs/default_baseline_lora` | PROJECT_REQUIRED | 输出目录 |
| logging_dir | None | `.../logs/training/default_baseline_lora` | PROJECT_REQUIRED | 日志目录 |
| disable_gradient_checkpointing | `false` | `false` | EXACT_DEFAULT | LF 默认开启 GC；显式写出行为 |
| cutoff_len | `2048` | `2048` | EXACT_DEFAULT | 核心实验参数 |
| packing | `None`→SFT false | `false` | EXACT_DEFAULT | 核心实验参数 |
| train_on_prompt | `false` | `false` | EXACT_DEFAULT | 核心实验参数 |
| val_size | `0.0` | `0` | EXACT_DEFAULT | 无验证集 |
| lora_rank | `8` | `8` | EXACT_DEFAULT | 核心实验参数 |
| lora_alpha | `None`→16 | `16` | EXACT_DEFAULT | 核心实验参数 |
| lora_dropout | `0.0` | `0` | EXACT_DEFAULT | 核心实验参数 |
| lora_target | `all` | `all` | EXACT_DEFAULT | 核心实验参数 |
| learning_rate | `5e-05` | `5e-5` | EXACT_DEFAULT | 核心实验参数 |
| num_train_epochs | `3.0` | `3.0` | EXACT_DEFAULT | 核心实验参数 |
| seed | `42` | `42` | EXACT_DEFAULT | 核心实验参数 |
| per_device_train_batch_size | HF `8` / WebUI `2` | `2` | WEBUI_DEFAULT | DEFAULT-LORA-001 已确认 |
| gradient_accumulation_steps | HF `1` / WebUI `8` | `8` | WEBUI_DEFAULT | DEFAULT-LORA-001 已确认 |
| lr_scheduler_type | HF `linear` / WebUI `cosine` | `cosine` | WEBUI_DEFAULT | DEFAULT-LORA-001 已确认 |
| bf16 | HF `false` / WebUI `bf16` | `true` | WEBUI_DEFAULT | DEFAULT-LORA-001 已确认 |

## 已删除的非必要字段

| Parameter | 原值 | Pinned Default | 处理 | Reason |
|---|---|---|---|---|
| trust_remote_code | `true` | `false` | **删除** | CodeLlama 为标准 `LlamaForCausalLM`，无 `auto_map`、无自定义 `.py`，不需要 remote code |
| preprocessing_num_workers | `4` | `None` | **删除** | 非运行必需；保持默认 |
| plot_loss | `true` | `false` | **删除** | loss 由 trainer log / metrics collector 记录 |
| gradient_checkpointing | `false` | HF `false` | **删除** | 属 HF TrainingArguments；与 LF 行为表述冲突。LF 正式参数为 `disable_gradient_checkpointing` |
| overwrite_output_dir | `true` | `false` | **删除** | 非运行必需 |
| warmup_ratio | `0.0` | `None` | **删除** | `warmup_steps=0` 已是默认语义 |
| warmup_steps | `0` | `0` | **删除** | 与 pinned 默认一致，无需写入 |
| optim | `adamw_torch` | `adamw_torch_fused` | **删除** | 非核心实验参数；保持 HF 默认 |
| logging_steps | `5` | `500` | **删除** | 非核心实验参数 |
| save_steps | `100` | `500` | **删除** | 非核心实验参数 |
| max_samples | `null` | `None` | **删除** | 与默认一致（用全部 1455） |
| save_total_limit | `null` | `None` | **删除** | 与默认一致 |
| dataloader_num_workers | `0` | `0` | **删除** | 与默认一致 |
| dataloader_drop_last | `false` | `false` | **删除** | 与默认一致 |
| max_grad_norm | `1.0` | `1.0` | **删除** | 与默认一致 |
| additional_target | `null` | `None` | **删除** | 与默认一致 |
| use_rslora / use_dora | `false` | `false` | **删除** | 与默认一致 |
| neat_packing / mask_history / fp16 | `false` | `false` | **删除** | 与默认一致 |
| do_eval / eval_strategy | `false` / `no` | `false` / `no` | **删除** | 与默认一致（本项目无 eval） |
| report_to | `none` | `none` | **删除** | 与默认一致 |

## Gradient Checkpointing 专项

| 项 | 结论 |
|---|---|
| LF 控制字段 | `ModelArguments.disable_gradient_checkpointing` |
| pinned 默认 | `false` |
| 最终值 | `false` |
| **LLaMA-Factory Gradient Checkpointing** | **ENABLED** |
| Default | **YES** |
| 源码依据 | `src/llamafactory/model/model_utils/checkpointing.py`：`if not model_args.disable_gradient_checkpointing:` → `gradient_checkpointing_enable(...)` → log `"Gradient checkpointing enabled."` |
| HF 字段 `TrainingArguments.gradient_checkpointing` | 默认 `false`；**不写入 YAML**，避免被误解为关闭 LF 的 GC |

## trust_remote_code

| 项 | 值 |
|---|---|
| Previous | `true` |
| Pinned Default | `false` |
| Final | **删除（等价默认 false）** |
| Reason | 模型 `architectures=['LlamaForCausalLM']`，`model_type=llama`，无 `auto_map`，目录内无自定义 Python |

## 汇总

| 指标 | 值 |
|---|---|
| NON_DEFAULT without explicit reason | **0** |
| EXACT_DEFAULT（显式写出） | 11 |
| WEBUI_DEFAULT（已确认基线） | 4 |
| PROJECT_REQUIRED | 10 |
| Token accounting changed | NO |
| Optimizer steps changed | NO |
