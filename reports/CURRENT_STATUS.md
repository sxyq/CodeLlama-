# CodeLlama LoRA 微调项目——当前状态

任务编号：FINAL-PROJECT-CLOSEOUT-001  
更新时间：2026-09-23

| 项目 | 事实 |
|---|---|
| Current Phase | **EXPERIMENT COMPLETED / ARCHIVED** |
| EXPERIMENT_COMPLETED | YES |
| TRAINING_STATUS | SUCCESS |
| Epochs / Global Steps | 3.0 · 273 / 273 |
| Total Training Tokens | 5,024,709 |
| Wall / Trainer Runtime | 8,989 s / 8,905 s |
| ARTIFACT_INVENTORY_COMPLETE | YES |
| LOCAL_ARCHIVE_COMPLETE | YES |
| GITHUB_ARCHIVE_COMPLETE | YES |
| ADAPTER_INTEGRITY | PASS |
| Git LFS | PASS / AVAILABLE / USED |
| VLLM_RESTORED | YES |
| VLLM_OPERATIONAL | YES |
| VLLM_HEALTH | 200 |
| VLLM_MODELS_OK | YES |
| Served model | codellama-13b-instruct-hf |
| BLOCKING_ISSUE | NONE |

归档与服务：

| 项 | 值 |
|---|---|
| Total artifact files | 54 |
| Total artifact size | 510,850,913 bytes（487.2 MiB） |
| Adapter SHA256 | 191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9 |
| Local archive | `artifacts/DEFAULT-LORA-001/` |
| Manifest | `reports/ARTIFACT_MANIFEST.md` / `.json` |
| Adapter / Checkpoint GitHub | GIT-LFS |
| Archive commit | `0ff433d` |
| Train commit | `c5afce6` |
| Docs commits | `04bd8f6` · `d268820` |
| vLLM port 8000 | LISTENING · health=200 · models=OK |
| vLLM models root | `/data/vllm/CodeLlama-13b-Instruct-hf/` |

## vLLM owner NOTE

当前恢复成功的 vLLM 实例由 `syy` 启动，使用 yuyong venv 的 PATH/PYTHONPATH，配置仍为 `qwen3-5.yaml`；模型、served name、port 未改变。当前 health=200、models=OK，因此 `VLLM_OPERATIONAL = YES`。

若以后服务器要求恢复原 yuyong Unix owner，那是独立运维任务，不属于 DEFAULT-LORA-001 微调实验 blocker。本轮不重启服务。

Next Action: NONE — WAIT FOR USER REQUEST
