# DEFAULT-LORA-001 训练后产物归档与 vLLM 恢复计划

更新时间：2026-09-23  
实验：`DEFAULT-LORA-001`  
状态：计划已执行完毕（历史计划文档；最终状态见 `reports/CURRENT_STATUS.md` 与 `coordination/LAST_HANDOFF.md`）

## 1. 计划制定时的状态（历史记录）

正式 LoRA 微调已经完成：

- Training status: **SUCCESS**
- Epochs: **3.0**
- Global steps: **273 / 273**
- Total training tokens: **5,024,709**
- Wall-clock: **8,989 s**
- Train runtime: **8,905 s**
- Adapter path: `$HOME/codellama-lora/outputs/default_baseline_lora`
- Checkpoint: `checkpoint-273`
- Adapter SHA256: `191d6e982ad91a8750c5b2f51a42ca36b9f94a74dec1d3155dd0b2c2ab1f9ac9`
- vLLM: **当时停止（历史）**；现已恢复并运行中（health=200）
- Port 8000: **当时未监听（历史）**；现已 LISTENING

计划制定时用户要求的顺序：

1. 先把训练相关产物完整盘点清楚；
2. 校验大小、SHA256、文件数量和用途；
3. 将需要保留的产物同步到 LOCAL；
4. 将适合进入 GitHub 的产物推送到仓库；
5. 对大文件优先检查 Git LFS 能力，不允许因 GitHub 100 MB 普通文件限制而直接失败或丢失；
6. 产物归档确认后恢复原 vLLM；
7. 验证 `8000/health` 与 `/v1/models`；
8. 更新最终状态文档。

## 2. REMOTE / LOCAL / GitHub

REMOTE workspace：

`$HOME/codellama-lora`

LOCAL project：

`/Users/sunyiyang/Desktop/Project/微调/`

GitHub：

`sxyq/CodeLlama-` / branch `main`

Base model：

`/data/vllm/CodeLlama-13b-Instruct-hf`

Base model 必须保持 READ ONLY，不属于需要复制/上传的训练产物。

## 3. 需要盘点的产物范围

至少检查并统计以下范围，不要只检查当前已知的两个文件：

### A. 正式模型产物

`$HOME/codellama-lora/outputs/default_baseline_lora/**`

重点：

- `adapter_model.safetensors`
- `adapter_config.json`
- `checkpoint-273/**`
- `trainer_state.json`（若存在）
- `trainer_log.jsonl`
- `train_results.json`
- 其他 tokenizer / metadata / README / training args / state 文件

### B. 正式报告

`$HOME/codellama-lora/reports/**`

重点：

- `TRAINING_METRICS.json`
- `FORMAL_TRAINING_RESULT.md`
- `TOKEN_AUDIT.md`
- `token_stats.json`
- `TRAIN_PLAN.md`
- `DEFAULT_CONFIG_MANIFEST.md`
- `CONFIG_DIFF.md`
- `CURRENT_STATUS.md`
- `SERVER_PRETRAIN_AUDIT.md`
- 其他本实验直接相关报告

### C. 可复现配置

- `configs/training/default_baseline_lora.yaml`
- 本项目 dataset registration
- `configs/project_env.sh`（必须先检查是否含敏感信息）

### D. 可复现脚本

- `scripts/run_training.sh`
- `scripts/monitor_gpu.sh`
- `scripts/collect_training_metrics.py`
- `scripts/token_audit.py`
- 其他本实验使用的脚本

### E. 日志与原始 telemetry

检查：

`$HOME/codellama-lora/logs/training/default_baseline_lora/**`

注意：

已知训练结束后发生过 `run_training.sh` 重拉起，部分根目录 metrics/logs 曾被覆盖。日志必须先盘点、区分“首次正式运行证据”和“后续异常重拉起产物”，不得混为一谈。

## 4. 产物清单要求

生成一个完整 Manifest，至少包含：

| 字段 | 含义 |
|---|---|
| relative_path | 相对 REMOTE workspace 的路径 |
| type | adapter / checkpoint / report / config / script / log / metadata |
| size_bytes | 文件大小 |
| sha256 | SHA256；目录则对关键文件逐个计算 |
| source_status | original / reconstructed / restored-from-checkpoint |
| required_for_reproduction | YES / NO |
| required_for_archive | YES / NO |
| github_method | normal-git / git-lfs / local-only / excluded |
| notes | 异常或来源说明 |

同时输出：

- 总文件数
- 总大小
- adapter 相关文件数/大小
- checkpoint 文件数/大小
- report 文件数/大小
- log 文件数/大小
- 计划同步到 LOCAL 的总大小
- 计划进入 GitHub 的总大小

## 5. LOCAL 归档目录

建议在 LOCAL 创建：

`/Users/sunyiyang/Desktop/Project/微调/artifacts/DEFAULT-LORA-001/`

推荐结构：

```text
artifacts/DEFAULT-LORA-001/
├── adapter/
├── checkpoint-273/
├── reports/
├── configs/
├── scripts/
├── logs/
└── manifest/
```

REMOTE → LOCAL 同步完成后，必须重新计算关键文件 SHA256，与 REMOTE 对比。

至少要求：

`adapter_model.safetensors` SHA256 与 REMOTE 一致。

## 6. GitHub 上传规则

### 普通 Git

适合：

- Markdown
- JSON
- YAML
- 小型脚本
- 小型 metadata

### 大文件

`adapter_model.safetensors` 已知约 125 MB，超过 GitHub 普通 Git 单文件 100 MB 限制。

因此不能直接普通 `git add/push`。

必须先检查：

```bash
git lfs version
git lfs env
git lfs track
```

如果当前仓库已具备并允许 Git LFS：

- 使用 Git LFS 管理 `*.safetensors` 及其他超限训练二进制；
- 提交 `.gitattributes`；
- 验证 LFS 对象实际上传成功。

如果 Git LFS 不可用、配额不足或 push 失败：

- 不得删除本地/远程产物；
- 不得把大文件硬塞进普通 Git；
- 将大文件保留在 LOCAL 归档；
- Manifest 中明确 `github_method=local-only` 和具体原因；
- 其余可入库产物正常提交。

Checkpoint 是否整体入 GitHub，必须根据实际体积、LFS 可用性与仓库限制决定，不得在未统计大小前直接假设。

## 7. 安全边界

禁止提交 GitHub：

- SSH 密码 / key 内容
- `coordination/*.local.md`
- sudo 密码
- token / secret / cookie
- 原始私有凭据

Dataset `Fine-Tuning.json` 是否推送，继续遵守现有仓库策略；本任务重点是训练产物，不要擅自改变数据集公开策略。

Base model 13B 权重不上传。

## 8. vLLM 恢复

只有在以下条件满足后恢复 vLLM：

- REMOTE 产物盘点完成；
- LOCAL 关键产物同步完成；
- Adapter SHA256 校验通过；
- GitHub 可提交产物已经 push；
- Manifest 已落库；
- 不再需要占用 GPU 读取/复制训练产物。

恢复方式以 LOCAL PRIVATE：

`coordination/VLLM_RUNBOOK.local.md`

为唯一可信来源。

已知恢复身份需要：

`sudo -u yuyong`

恢复后必须确认：

- vLLM process exists
- EngineCore exists
- port 8000 LISTENING
- `/health` → 200
- `/v1/models` 包含 `codellama-13b-instruct-hf`
- `nvidia-smi` 显示模型重新加载 GPU

不要自动加载本次 LoRA adapter；恢复原基础模型托管服务即可。

## 9. 最终需要新增/更新的文档

至少生成/更新：

- `reports/ARTIFACT_MANIFEST.md`
- `reports/ARTIFACT_MANIFEST.json`
- `reports/CURRENT_STATUS.md`
- `coordination/PROJECT_STATE.md`
- `coordination/LAST_HANDOFF.md`
- `coordination/NEXT_ACTION.md`

最终状态应体现：

- TRAINING_STATUS = SUCCESS
- ARTIFACT_INVENTORY_COMPLETE = YES
- LOCAL_ARCHIVE_COMPLETE = YES
- GITHUB_ARCHIVE_COMPLETE = YES / PARTIAL（若大文件因 LFS 限制未入库）
- ADAPTER_INTEGRITY = PASS
- VLLM_RESTORED = YES
- VLLM_HEALTH = 200
- EXPERIMENT_COMPLETED = YES

## 10. 不需要做的事情

- 不继续训练
- 不做第二次 LoRA
- 不做 benchmark
- 不做 Base vs LoRA 比较
- 不修改 adapter
- 不删除 checkpoint
- 不清理 REMOTE 原始训练产物，除非用户以后明确要求
