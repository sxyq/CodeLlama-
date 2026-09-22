# ARTIFACT_MANIFEST — DEFAULT-LORA-001

Generated At: 2026-09-23T01:10:00+08:00

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| Remote root | `/home/syy/codellama-lora` |
| Local archive root | `artifacts/DEFAULT-LORA-001/` |
| GitHub repo | `sxyq/CodeLlama-` branch `main` |
| Adapter integrity | **PASS** |
| Local archive | **COMPLETE** |
| Git LFS | **AVAILABLE** (git-lfs/3.8.0) |
| Adapter GitHub method | **GIT-LFS** |
| Checkpoint GitHub method | **GIT-LFS** |
| GitHub archive | see final flag in JSON / LAST_HANDOFF |

## Totals

| Metric | Value |
|---|---:|
| TOTAL_ARTIFACT_FILE_COUNT | 54 |
| TOTAL_ARTIFACT_SIZE_BYTES | 510,850,913 |
| TOTAL_ARTIFACT_SIZE | 487.2 MiB |
| ADAPTER_FILE_COUNT | 11 |
| ADAPTER_SIZE_BYTES | 128,881,560 |
| ADAPTER_SIZE | 122.9 MiB |
| CHECKPOINT_FILE_COUNT | 11 |
| CHECKPOINT_SIZE_BYTES | 379,727,050 |
| CHECKPOINT_SIZE | 362.2 MiB |
| REPORT_FILE_COUNT | 11 |
| REPORT_SIZE_BYTES | 2,103,608 |
| LOG_FILE_COUNT | 5 |
| LOG_SIZE_BYTES | 70,569 |
| CONFIG_FILE_COUNT | 3 |
| SCRIPT_FILE_COUNT | 8 |

## SHA256 (three-way)

| Source | SHA256 |
|---|---|
| REMOTE adapter | `191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9` |
| LOCAL adapter | `191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9` |
| checkpoint-273 adapter | `191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9` |

ADAPTER_INTEGRITY = **PASS**

## Summary table

| Category | Files | Size | REMOTE | LOCAL | GitHub |
|---|---:|---:|---|---|---|
| Adapter | 11 | 128,881,560 (122.9 MiB) | YES | YES | GIT-LFS + ordinary |
| Checkpoint | 11 | 379,727,050 (362.2 MiB) | YES | YES | GIT-LFS |
| Reports | 11 | 2,103,608 (2.0 MiB) | YES | YES | ORDINARY |
| Configs | 3 | 2,072 | YES | YES | ORDINARY |
| Scripts | 8 | 63,686 | YES | YES | ORDINARY |
| Logs | 5 | 70,569 | YES | YES | ORDINARY |
| Metadata/Coord | 5 | 2,368 | YES | YES | ORDINARY |

## Source status (anomaly marks)

| Artifact | source_status |
|---|---|
| `adapter/adapter_model.safetensors` | restored-from-checkpoint（首轮真实权重；根目录曾被重拉起覆盖后恢复） |
| `checkpoint-273/**` | original |
| `reports/TRAINING_METRICS.json` | reconstructed |
| `reports/FORMAL_TRAINING_RESULT.md` | reconstructed |
| `logs/**/gpu_monitor.csv` | reconstructed；GPU 峰值等来自 live-observation |
| `logs/**/train_*.log` | reconstructed-relaunch-overwrite |
| `adapter/train_results.json` 等根 state | reconstructed |
| `adapter/trainer_log.jsonl` | first line original；tail 为重拉起噪声 |
| configs / scripts / token audit | original |

**不要把 reconstructed 数据描述成原始 telemetry。** 完整逐文件记录见 `reports/ARTIFACT_MANIFEST.json`。

## Destination matrix

- **REMOTE + LOCAL + GitHub**: 全部 54 个归档文件（大二进制走 Git LFS）
- **LOCAL only**: base model / venv / HF cache / `Fine-Tuning*.json` / `*.local.md` / SSH 凭据 —— 按策略不进 Git

## Large binary LFS tracks

```
*.safetensors
*.pt
```

> 注：`optimizer.pt` / `rng_state.pth` / `scheduler.pt` 中超过普通 Git 限制的用 LFS；小 `.pt` 可随 LFS 或 ordinary，以 `.gitattributes` 为准。
