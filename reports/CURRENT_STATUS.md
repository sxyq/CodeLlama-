# CodeLlama LoRA 微调项目——当前状态

任务编号：TRAIN-CONFIG-001 完成后更新  
更新时间：2026-09-22

## 0. 当前总览

| 项目 | 事实 |
|---|---|
| Current Phase | **TRAINING CONFIGURATION** |
| Experiment ID | DEFAULT-LORA-001 |
| TRAIN_CONFIG_READY | **YES** |
| TRAINING_STARTED | **NO** |
| BENCHMARK_REQUIRED | **NO** |
| TEST_REQUIRED | **NO** |
| GPU_READY | **NO** |
| 训练样本 | 1455 |
| 验证样本 | 0 |
| 测试样本 | 0 |
| Base model | READ ONLY，未修改 |
| Dataset | 未修改 |
| vLLM | 未受影响 |
| 当前第一阻塞项 | GPU 显存被 vLLM 占用；MEMORY FIT = UNVERIFIED |

## 1. 实验目标（已更新）

1. 使用全部 1455 条数据完成 LoRA 微调（LLaMA-Factory）。
2. 尽量保持 LLaMA-Factory 默认配置基线。
3. 精确记录训练 Token / 时间 / Loss / Steps / Throughput / 显存 / adapter。

不做：效果测试、Base vs LoRA 对比、benchmark、测试集。

## 2. LOCAL-MAC 同步内容

```text
reports/CURRENT_STATUS.md
reports/TRAIN_PLAN.md
reports/DEFAULT_CONFIG_MANIFEST.md
configs/training/default_baseline_lora.yaml
configs/datasets/dataset_info.json
scripts/run_training.sh
scripts/collect_training_metrics.py
scripts/validate_train_config.py
```

不提交：Fine-Tuning.json、模型、venv、cache、checkpoint、大型 log、secret。

## 3. REMOTE 工作区

`$HOME/codellama-lora`  
唯一写入范围保持不变。

| 对象 | 状态 |
|---|---|
| `configs/training/default_baseline_lora.yaml` | 已创建 |
| `configs/datasets/dataset_info.json` | 已创建 |
| `configs/datasets/Fine-Tuning.json` | symlink → `data/Fine-Tuning.json` |
| `data/Fine-Tuning.json` | 只读，SHA256 不变 |
| `scripts/run_training.sh` | 已创建，**未运行** |
| `scripts/collect_training_metrics.py` | 已创建 |
| `scripts/validate_train_config.py` | 已创建并执行 |
| `reports/train_token_accounting.json` | 静态验证 PASS |

## 4. Token 口径（cutoff_len=2048）

| 口径 | Input | Output | Total |
|---|---:|---:|---:|
| Raw Dataset | 1,444,375 | 262,395 | 1,706,770 |
| Effective Dataset | 1,456,015 | 263,850 | 1,719,865 |
| Train / epoch（2048 后） | 1,411,053 | 263,850 | 1,674,903 |
| Train presentations / 3E | 4,233,159 | 791,550 | 5,024,709 |

LOSS_BEARING / epoch = 263,850  
LOSS_BEARING / 3E = 791,550

## 5. Batch / Steps

micro batch=2；grad accum=8；effective batch=16  
micro steps/epoch=728；optimizer steps/epoch=91；**total optimizer steps=273**

## 6. 训练状态

```text
TRAINING_STARTED = NO
GPU_MODEL_LOADED = NO
TRAINING SAMPLES = 1455
VALIDATION SAMPLES = 0
TEST SAMPLES = 0
BENCHMARK = NONE
BASE VS LORA COMPARISON = NONE
DATASET MODIFIED = NO
BASE MODEL MODIFIED = NO
VLLM AFFECTED = NO
CONFIG STATIC VALIDATION = PASS
```

## 7. Blocking Issues

1. 单卡显存被 vLLM 占用（空闲约 4574 MiB）→ GPU_READY = NO。
2. MEMORY FIT = UNVERIFIED（配置阶段禁止加载 13B 权重实测）。

## 8. 下一步（待命令）

1. 处理 GPU 占用后由 Commander 触发 `run_training.sh`。
2. 训练结束后运行指标汇总，产出 `reports/TRAINING_METRICS.json`。
