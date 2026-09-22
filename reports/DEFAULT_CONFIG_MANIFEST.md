# DEFAULT_CONFIG_MANIFEST

任务编号：TRAIN-CONFIG-001  
Experiment ID：DEFAULT-LORA-001  
pinned LLaMA-Factory commit：`97b32d3133b501432141a82949d5c7bc4d94f23a`

原则：关键实验参数 **显式写入** `configs/training/default_baseline_lora.yaml`，不依赖未来版本隐式默认。

| Parameter | WebUI Default | Dataclass Default | Final Baseline Value |
|---|---|---|---|
| stage | sft（TRAINING_STAGES 首项） | — | sft |
| finetuning_type | lora（LoRA 面板） | — | lora |
| template | WebUI `get_template`（CodeLlama 无映射→default） | None→parse tokenizer chat_template | **llama2**（显式） |
| cutoff_len | 2048 | 2048 | **2048** |
| packing | false（Checkbox 未勾选） | None；SFT 解析为 false | **false** |
| neat_packing | false | false | **false** |
| train_on_prompt | false | false | **false** |
| mask_history | false | false | **false** |
| val_size | 0 | 0.0 | **0** |
| max_samples | 100000 | None | **null**（用全部 1455） |
| learning_rate | 5e-5 | 5e-05（HF） | **5e-5** |
| num_train_epochs | 3.0 | 3.0（HF） | **3.0** |
| per_device_train_batch_size / batch_size | 2 | 8（HF） | **2** |
| gradient_accumulation_steps | 8 | 1（HF） | **8** |
| lr_scheduler_type | cosine | linear（HF） | **cosine** |
| warmup_steps | 0 | 0（HF） | **0** |
| warmup_ratio | 未在主行暴露 | None（HF） | **0.0** |
| lora_rank | 8 | 8 | **8** |
| lora_alpha | 16 | None→rank*2=16 | **16** |
| lora_dropout | 0 | 0.0 | **0** |
| lora_target | 空 Textbox | `all` | **all** |
| additional_target | 空 | None | **null** |
| use_rslora | false | false | **false** |
| use_dora | false | false | **false** |
| use_pissa | WebUI 有 use_pissa | **字段不存在于本 pinned FinetuningArguments** | 不写入 YAML |
| resize_vocab | false | false（ModelArguments） | **不写入 / 默认 false** |
| bf16 | compute_type=bf16 | False（HF） | **true** |
| fp16 | 未选 | False | **false** |
| gradient_checkpointing | 非主 UI 行 | False（HF） | **false** |
| optim | extra_args `{"optim": "adamw_torch"}` | adamw_torch_fused（HF） | **adamw_torch** |
| logging_steps | 5 | 500（HF） | **5** |
| save_steps | 100 | 500（HF） | **100** |
| seed | 42（train_seed） | 42（HF） | **42** |
| report_to | none | none（HF） | **none** |
| plot_loss | 未在主行 | false（FinetuningArguments） | **true** |
| max_grad_norm | 1.0 | 1.0（HF） | **1.0** |
| dataloader_drop_last | — | False（HF） | **false** |
| do_eval / eval_strategy | — | — | **false / no** |

## 特别确认

| 项 | 结论 |
|---|---|
| WebUI num_train_epochs default | 3.0 |
| Parser/dataclass num_train_epochs default | 3.0 |
| Example YAML epoch | 3.0 |
| WebUI packing default | false |
| Parser/dataclass packing default | None→SFT false |
| packing 是否默认开启 | 否 |
| WebUI lora_rank default | 8 |
| dataclass lora_rank default | 8 |
| example YAML lora_rank | 8 |
| lora_alpha | WebUI 16；dataclass None→16 |
| lora_dropout | 0 |
| lora_target | dataclass `all`（全部 linear）；WebUI 空；YAML `all` |

## 显式写入策略

以下字段已在正式 YAML 显式写出（不依赖隐式默认）：

`model_name_or_path`, `stage`, `do_train`, `finetuning_type`, `template`, `dataset`, `dataset_dir`, `cutoff_len`, `packing`, `neat_packing`, `train_on_prompt`, `mask_history`, `val_size`, `max_samples`, `learning_rate`, `num_train_epochs`, `per_device_train_batch_size`, `gradient_accumulation_steps`, `lr_scheduler_type`, `warmup_steps`, `warmup_ratio`, `lora_rank`, `lora_alpha`, `lora_dropout`, `lora_target`, `additional_target`, `use_rslora`, `use_dora`, `bf16`, `fp16`, `gradient_checkpointing`, `optim`, `logging_steps`, `save_steps`, `seed`, `report_to`, `plot_loss`, `max_grad_norm`, `dataloader_drop_last`, `output_dir`, `logging_dir`, `do_eval`, `eval_strategy`。
