# CodeLlama Token Audit
任务编号：TOKEN-AUDIT-001
平台：REMOTE-SERVER（CPU tokenizer，不加载 13B 权重）
时间：2026-09-22T18:18:31.040237+08:00

## 0. Summary
| Item | Value |
|---|---|
| Samples | 1455 |
| Dataset SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| Tokenizer | CodeLlamaTokenizer / len=32017 |
| Template | `llama2` |
| Raw Input Tokens | 1,444,375 |
| Raw Output Tokens | 262,395 |
| Raw Total Tokens | 1,706,770 |
| Effective Total Tokens | 1,719,865 |
| Loss-bearing Tokens | 263,850 |
| 2048 Truncation Rate | 8.11% |
| 4096 Truncation Rate | 0.00% |
| 8192 Truncation Rate | 0.00% |
| Target Groups | 51 |
| Random Split Leakage Risk | YES |
| AUDIT_VALIDATION_OK | YES |

## 1. Dataset Integrity
| Check | Result |
|---|---|
| JSON parse | OK (list) |
| sample count | 1455 |
| conversations | 1455 / malformed 0 |
| human / gpt | 1455 / 1455 |
| empty human / gpt | 0 / 0 |
| unique inputs | 1406 |
| unique outputs | 51 |
| duplicate full pairs | 49 |
| SHA256 | `28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6` |
| SHA256 match expected | YES |

## 2. Tokenizer
| Field | Value |
|---|---|
| path | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| class | `CodeLlamaTokenizer` |
| vocab_size | `32016` |
| len | `32017` |
| bos_token | `<s>` |
| bos_token_id | `1` |
| eos_token | `</s>` |
| eos_token_id | `2` |
| pad_token | `</s>` |
| pad_token_id | `2` |
| unk_token | `<unk>` |
| unk_token_id | `0` |
| model_max_length | `1000000000000000019884624838656` |
| padding_side | `left` |
| truncation_side | `right` |
| add_bos_token | `True` |
| add_eos_token | `False` |
| chat_template_present | `True` |

chat/template 有关配置：tokenizer 自带 `chat_template`（Llama-2 `<<SYS>>` + `[INST] ... [/INST]` + `</s>`）。
`TOKENIZER_READY = YES`

## 3. LLaMA-Factory Template
- template name: `llama2`
- template 定义源码：`src/llamafactory/data/template.py`（`register_template(name="llama2", ...)`，`template_class=Llama2Template`）
- 附近源码要点：`format_user=[bos_token]+[INST] {{content}} [/INST]`；`format_assistant` 默认 `{{content}}`+eos；system 融入首轮 user（`Llama2Template`）
- BOS/EOS：user 槽位含 `{bos_token}`；assistant 默认槽位含 `{eos_token}`；`efficient_eos=false`
- user/assistant 格式：`[INST] ... [/INST]` / `... </s>`
- system prompt：无自定义 system 时 `default_system` 为空；有 system 时写成 `<<SYS>>\n...\n<</SYS>>\n\n` 融入首轮 user
- 证据：模型 `tokenizer_config.json` 的 `chat_template` 与 `llama2` 同构（`bos+[INST] ... [/INST]`，assistant ` content + eos`）
- 说明：pinned 源码中无 `codellama` 专用 template；WebUI `DEFAULT_TEMPLATE` 无 CodeLlama 条目（未知名会落到 `default`，格式不匹配）。本审计采用与 tokenizer chat_template 一致的 `llama2`，并调用 pinned `TEMPLATE.encode_oneturn` + `infer_seqlen` + supervised labeling。
- `TEMPLATE_UNRESOLVED` / `TEMPLATE_AMBIGUOUS`：**否**（已解析为 `llama2`）

## 4. Raw Token Statistics
| dim | min | mean | median | P50 | P75 | P90 | P95 | P99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| input | 87 | 992.7 | 915.0 | 915.0 | 1254.0 | 1669.0 | 1941.0 | 2657.5 | 3075 |
| output | 11 | 180.3 | 154.0 | 154.0 | 231.0 | 300.0 | 300.0 | 625.0 | 801 |
| combined | 98 | 1173.0 | 1103.0 | 1103.0 | 1507.0 | 1963.0 | 2181.5 | 2977.3 | 3680 |

阈值样本数：

| dim | >=512 | >=1024 | >=2048 | >=4096 | >=8192 | >=16384 |
|---|---:|---:|---:|---:|---:|---:|
| input | 1204 | 605 | 55 | 0 | 0 | 0 |
| output | 31 | 0 | 0 | 0 | 0 | 0 |
| combined | 1254 | 838 | 117 | 0 | 0 | 0 |

RAW_INPUT_TOKENS = 1,444,375

RAW_OUTPUT_TOKENS = 262,395

RAW_TOTAL_TOKENS = 1,706,770

## 5. Effective SFT Token Statistics
复用 pinned LLaMA-Factory：`TEMPLATES['llama2'].encode_oneturn` + `processor_utils.infer_seqlen` + `SupervisedDatasetProcessor` 标注逻辑（`train_on_prompt=False`）。
| Field | Tokens |
|---|---:|
| EFFECTIVE_CONTEXT_TOKENS（prompt/source） | 1,456,015 |
| EFFECTIVE_RESPONSE_TOKENS（assistant） | 263,850 |
| EFFECTIVE_TOTAL_TOKENS | 1,719,865 |
| LOSS_BEARING_TOKENS | 263,850 |
| IGNORED/MASKED_TOKENS | 1,456,015 |

`train_on_prompt` 默认 False：prompt 不参与 loss。

## 6. Cutoff Simulation
使用同一 `infer_seqlen`（pinned `processor_utils.py`）。

| cutoff | total | truncated | rate | tokens removed | removed ratio | response truncated |
|---:|---:|---:|---:|---:|---:|---:|
| 512 | 1455 | 1259 | 86.53% | 1,010,318 | 58.74% | 234 |
| 1024 | 1455 | 854 | 58.69% | 445,206 | 25.89% | 31 |
| 2048 | 1455 | 118 | 8.11% | 44,962 | 2.61% | 0 |
| 4096 | 1455 | 0 | 0.00% | 0 | 0.00% | 0 |
| 8192 | 1455 | 0 | 0.00% | 0 | 0.00% | 0 |
| 16384 | 1455 | 0 | 0.00% | 0 | 0.00% | 0 |

截断位置（tokens removed 拆分）：

| cutoff | prompt_tokens_removed | response_tokens_removed |
|---:|---:|---:|
| 512 | 952,841 | 57,477 |
| 1024 | 436,287 | 8,919 |
| 2048 | 44,962 | 0 |
| 4096 | 0 | 0 |
| 8192 | 0 | 0 |
| 16384 | 0 | 0 |

## 7. Target Group Analysis
- TARGET_GROUP_COUNT = 51
- unique human = 1406
- unique gpt = 51
- duplicate full pair = 49
- group size min/max/mean/median/P90 = 1/124/28.53/30.0/44.0
- unique function names = 17
- unknown function-name groups = 34

Top 20 largest target groups（不含完整源码）：

| rank | SHA256 | sample_count | function_name |
|---:|---|---:|---|
| 1 | `61b82e1e63a7bf07…` | 124 | UNKNOWN |
| 2 | `25b6f5a86b77a054…` | 53 | UNKNOWN |
| 3 | `2ed1db6adb7ff53d…` | 49 | gh_heap_remove |
| 4 | `be34db7357af2888…` | 45 | delegation |
| 5 | `2ba22bea7b681c3e…` | 44 | check_protocol |
| 6 | `8f693cfb5a5b7326…` | 44 | ftpfilemethod |
| 7 | `49fe8d05ce28078e…` | 42 | UNKNOWN |
| 8 | `7f6f97c5a989c23d…` | 42 | ftpcccmethod |
| 9 | `2552add26af313f0…` | 40 | Curl_multi_max_total_connections |
| 10 | `46e12dac25fdd18d…` | 40 | UNKNOWN |
| 11 | `a15b2bb584aaa510…` | 40 | UNKNOWN |
| 12 | `a8dda86bea1e5e61…` | 39 | UNKNOWN |
| 13 | `7761640fd4b6c9bc…` | 38 | UNKNOWN |
| 14 | `c373ba0042cc3bb6…` | 38 | UNKNOWN |
| 15 | `f86ad308a9871e1e…` | 38 | UNKNOWN |
| 16 | `07ec6b9fa1023776…` | 37 | Curl_multi_max_host_connections |
| 17 | `499d3571635139b7…` | 36 | UNKNOWN |
| 18 | `ca3983d5acb1f872…` | 36 | UNKNOWN |
| 19 | `d183e189a3de4d54…` | 36 | UNKNOWN |
| 20 | `1ea084b9c400da47…` | 35 | http_header_next |

## 8. Leakage Risk
- 多样本 target group 数量 = 49
- 落入多样本 target group 的样本数 = 1453
- independent target groups（按 output SHA256） = 51

RANDOM_SAMPLE_SPLIT_HAS_LEAKAGE_RISK = YES

本轮不决定 80/10/10 或 90/5/5 等划分比例。

## 9. LLaMA-Factory Defaults
| Parameter | WebUI Default | Parser/Dataclass Default | Example YAML | Evidence |
|---|---|---|---|---|
| learning_rate | 5e-5 | 5e-05 (HF) | 1.0e-4 | webui/components/train.py:52; HF TrainingArguments; examples/train_lora/qwen3_lora_sft.yaml |
| num_train_epochs | 3.0 | 3.0 (HF) | 3.0 | train.py:53; HF; yaml |
| cutoff_len | 2048 | 2048 | 2048 | train.py:72; data_args.py:46; yaml |
| batch_size | 2 | 8 (HF per_device) | 1 | train.py:73; HF; yaml |
| gradient_accumulation_steps | 8 | 1 (HF) | 8 | train.py:74; HF; yaml |
| packing | false (Checkbox unchecked) | None → SFT false | not set | train.py:99; data_args.py:108; parser.py:645 |
| neat_packing | false | false | not set | train.py:100; data_args.py:112 |
| train_on_prompt | false | false | not set | train.py:103; data_args.py:50 |
| lora_rank | 8 | 8 | 8 | train.py:193; finetuning_args.py:77; yaml |
| lora_alpha | 16 | None → rank*2=16 | not set | train.py:194; finetuning_args.py:69,610 |
| lora_dropout | 0 | 0.0 | not set | train.py:195; finetuning_args.py:73 |
| lora_target | empty Textbox | all | all | train.py:200; finetuning_args.py:83; yaml |
| lr_scheduler_type | cosine | linear (HF) | cosine | train.py:75; HF; yaml |
| warmup_steps / warmup_ratio | 0 / n/a | 0 / None | warmup_ratio 0.1 | train.py:92; HF; yaml |
| bf16 / fp16 | bf16 via compute_type | False / False | bf16: true | train.py:58; HF; yaml |
| gradient_checkpointing | not in primary UI row | False (HF) | not set | HF TrainingArguments |
| logging_steps | 5 | 500 (HF) | 10 | train.py:89; HF; yaml |
| save_steps | 100 | 500 (HF) | 500 | train.py:90; HF; yaml |
| val_size | 0 | 0.0 | commented 0.1 | train.py:74; data_args.py:100; yaml comments |
| seed | 42 (train_seed) | 42 (HF) | not set | train.py:56; HF |
| max_samples | 100000 | None | 1000 | train.py:57; data_args.py:84; yaml |
| report_to | none | none (HF) | none | train.py:120; HF; yaml |
| optim | extra_args adamw_torch | adamw_torch_fused (HF) | not set | train.py:93; HF |

特别字段：

| Field | Value |
|---|---|
| WebUI num_train_epochs default | 3.0 |
| Parser/dataclass num_train_epochs default | 3.0 (HF TrainingArguments) |
| Example YAML epoch | 3.0 |
| WebUI packing default | false（未勾选） |
| Parser/dataclass packing default | None；SFT 时解析为 false |
| packing 是否默认开启 | 否 |
| WebUI lora_rank default | 8 |
| dataclass lora_rank default | 8 |
| example YAML lora_rank | 8 |
| lora_alpha | WebUI 16；dataclass None→rank*2 |
| lora_dropout | 0 |
| lora_target | dataclass `all`；WebUI 空字符串；YAML `all`。`all` 表示所有 linear 模块（finetuning_args.py） |

## 10. Key Findings
- 数据 1455 条全部可解析；SHA256 与预期一致。
- 原始 human 内容显著长于 gpt 内容（input 均值 992.7 vs output 均值 180.3）。
- unique output 仅 51，对应 51 个 target group；多样本共享同一 source target 的 group 共 49 个。
- 2048/4096/8192 截断率分别为 8.11% / 0.00% / 0.00%。
- 截断主要发生在：prompt_tokens_removed@2048=44962，response_tokens_removed@2048=0。
- `train_on_prompt=False` 时 loss 只落在 assistant 响应 token（含模板 eos）。
- RANDOM_SAMPLE_SPLIT_HAS_LEAKAGE_RISK = YES。
- WebUI / dataclass / example YAML 的 epoch 均为 3.0；packing 默认关闭。

## 11. Inputs For Training Configuration
供 Commander 后续决策的事实输入（本报告不选定最终参数）：

1. Raw 与 Effective token 分布、P50/P90/P99。
2. 各 cutoff_len 截断率、移除 token 量，以及 prompt/response 截断拆分。
3. target group 规模与随机划分泄漏风险。
4. 框架默认值（含 epoch、packing、lora_rank/alpha/target、lr、batch、accum）。
5. 单卡显存现状（vLLM 占用）与 13B LoRA 需求之间的差距。

禁止项遵守：未做 train/val/test split，未选 LoRA 最终超参，未 YAML finalization，未训练。

## Sanity Checks
| Check | OK |
|---|---|
| input_total + output_total == raw_total | YES |
| samples == 1455 | YES |
| cutoff↑ => truncated samples non-increasing | YES |
| cutoff↑ => tokens removed non-increasing | YES |
| input percentiles ordered | YES |
| output percentiles ordered | YES |
| total percentiles ordered | YES |
| target_group_count == unique outputs | YES |
| dataset sha256 matches expected | YES |
