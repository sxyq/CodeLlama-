# CodeLlama LoRA Project — Current Status

> **Audit ID:** STATUS-AUDIT-001  
> **Generated:** 2026-09-22T15:34 Asia/Shanghai  
> **Mode:** READ-ONLY — no installation, deletion, configuration change, process control, download, or training was performed.

---

## 0. Snapshot

| Item | Value |
|------|-------|
| Audit date | 2026-09-22 |
| Local machine | `[LOCAL-MAC]` macOS |
| Remote machine | `[REMOTE-SERVER]` Ubuntu 24.04.4 LTS, kernel 6.8.0-87-generic x86_64 |
| Designated project | `/Users/sunyiyang/Desktop/Project/路由` (ModelRouter research) |
| Status sync repo | `https://github.com/sxyq/CodeLlama-.git` (`main` branch, no commits yet) |
| CodeLlama model | **FOUND** on `[REMOTE-SERVER]` — CodeLlama-13b-Instruct-hf (~49 GB) |
| Fine-Tuning.json | **NOT FOUND** in the accessible `[LOCAL-MAC]` and `[REMOTE-SERVER]` search scope |
| LLaMA-Factory | **NOT FOUND** on either side |
| `[REMOTE-SERVER]` training running | **NO** |
| `[LOCAL-MAC]` / `[REMOTE-SERVER]` LoRA training can start now | **NO** |

---

## 1. Local Mac

### 1.1 Working Directory & Git

All checks in this section: `[LOCAL-MAC]`.

| Check | Result |
|-------|--------|
| `pwd` | `/Users/sunyiyang/Desktop/Project/路由` |
| Branch | `main` |
| Remote | `origin` → `https://github.com/sxyq/modelrouter.git` |
| HEAD commit | `2557d3f Move deck trio into汇报/PPT, add script and screenshots` |

**Recent commits (git log --oneline -5):**

```
2557d3f Move deck trio into汇报/PPT, add script and screenshots
62a16e2 Add deck player, restore Claude models, revamp P4 interactive component
9bfdfaa Remove obsolete blog integration plan
2a15e4a Add model matrix dashboard and update PPT planning
1de62d8 Add P4 KV cache slide
```

**Working tree (pre-existing user changes — not touched by this audit):**

| Status | File |
|--------|------|
| D | `our-project/papers/unified-ai-gateway.txt` |
| D | `our-project/slides/assets/unified-ai-gateway-concept.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-12.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-14.png` |
| M | `our-project/汇报/PPT/assets/deck-images/page-20.png` |
| ?? | `our-project/汇报/data-readiness-routing-report.html` |

### 1.2 Project Structure & Key Files

| Path | Description |
|------|-------------|
| `README.md` | ModelRouter research project; `our-project/` research material, `external-projects/` source registrations. Explicitly excludes raw server logs and credentials. |
| `our-project/README.md` | Literature, data, papers, and planning directories. |
| `our-project/data/README.md` | Source/cleaned/summary data layers; data is call-level, not task-level billing. |
| `our-project/planning/IMPLEMENTATION_RESEARCH.md` | Routing research design (agent trajectory/cost logging, admission-time prediction, model × effort selection). **LoRA is not the focus of this document.** |
| `our-project/literature/` | Related papers, brief, report. |
| `our-project/汇报/` | PPT planning, deck images, data readiness report. |
| `external-projects/` | Vendored semantic-router, RouterBench, TwinRouterBench, MTRouter, LangGraph, AgentOpt, Best-Route-LLM registrations. |

### 1.3 CodeLlama / LoRA / Fine-Tuning Artifacts on Local Mac

| Artifact | Status |
|----------|--------|
| `Fine-Tuning.json` (or `Fine_Tuning.json`) | **NOT FOUND** — scanned Desktop, Documents, Downloads, and designated project. |
| CodeLlama model directory | **NOT FOUND** locally. |
| LLaMA-Factory checkout | **NOT FOUND** locally. |
| CodeLlama LoRA YAML | **NOT FOUND** locally. |
| CodeLlama training script | **NOT FOUND** locally. |
| CodeLlama benchmark script | **NOT FOUND** locally. |
| CodeLlama training log | **NOT FOUND** locally. |
| `AGENTS.md` / root `CLAUDE.md` | **NOT FOUND** in project root (nested copies belong to vendored external repos). |

> **Note:** The vendored `semantic-router` tree contains unrelated BERT/ModernBERT classifier fine-tuning scripts using PEFT/LoRA and public datasets. Header inspection confirms they are classification examples, **not** CodeLlama-13B instruction tuning. No evidence of execution was found.

### 1.4 Fine-Tuning.json Detail

| Field | Value |
|-------|-------|
| Path | **NOT FOUND** |
| Size | N/A |
| SHA256 | N/A |
| Parsed | N/A |
| Sample count | N/A |

---

## 2. Remote Server

All checks in this section: `[REMOTE-SERVER]`.

### 2.1 System

| Check | Result |
|-------|--------|
| Hostname | `REMOTE-SERVER` (redacted) |
| Date (at check) | `2026-09-22T14:41:28+08:00` |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | Linux 6.8.0-87-generic x86_64 |
| Shell | `/bin/bash` |
| Uptime | 17 weeks 5 days 2 hours 47 minutes |

### 2.2 Storage

| Filesystem | Type | Size | Used | Avail | Use% |
|------------|------|------|------|-------|------|
| Root (`/`) | ext4 | 3.5 T | 2.0 T | 1.4 T | 60% |

No separate model filesystem was reported by `df -hT`.

### 2.3 Memory

| Metric | Value |
|--------|-------|
| RAM total | 376 GiB |
| RAM used | 22 GiB |
| RAM free | 50 GiB |
| RAM available | 354 GiB |
| Swap | 0 B |

### 2.4 GPU / NPU

| Device | Details |
|--------|---------|
| GPU | **NVIDIA RTX A6000** (GA102GL), 49,140 MiB total |
| GPU memory used | 43,966 MiB (vLLM ~43,662 MiB + GNOME remote-desktop ~266 MiB) |
| GPU memory free | 4,574 MiB |
| GPU utilization | 0% at check time |
| NPU (`npu-smi`) | **NOT FOUND** |
| Ascend PCI device | **NOT FOUND** — PCI inventory shows NVIDIA GA102GL only |

### 2.5 Relevant Processes

| Process | Notes |
|---------|-------|
| vLLM engine | Running, serving CodeLlama-13b-Instruct-hf, ~43.7 GiB GPU |
| Ollama | Active service |
| Jupyter | Port 8888 |
| Open WebUI | Port 3000 |
| SSH | Active |
| Docker | Active service (socket permissions denied to audit login) |
| `torchrun` / `deepspeed` / `accelerate launch` / LLaMA-Factory training | **NONE found** |

### 2.6 Relevant Ports

| Port | Service |
|------|---------|
| 8000 | vLLM API |
| 8888 | Jupyter |
| 3000 | Open WebUI |
| 11434 | Ollama |

---

## 3. ML Environment

### 3.1 [REMOTE-SERVER] Python

| Check | Result |
|-------|--------|
| System Python | `/usr/bin/python3` → Python 3.12.3 |
| `python` command | **NOT FOUND** in audit login PATH |
| conda / mamba / micromamba | **NOT FOUND** |
| `llamafactory-cli` | **NOT FOUND** |

### 3.2 [REMOTE-SERVER] System Python Imports (all failed)

`torch`, `torch_npu`, `transformers`, `peft`, `accelerate`, `datasets`, `safetensors`, `llamafactory`, `vllm`, `tokenizers` — all **ModuleNotFoundError** from system Python.

### 3.3 [REMOTE-SERVER] vLLM Virtual Environment

| Field | Value |
|-------|-------|
| Path | `/home/████/vllm/.venv` (owner redacted) |
| Base Python | CPython 3.12.10 (managed by uv) |
| Accessible to audit login | Read metadata only; interpreter not executable |

**Packages found in vLLM venv:**

| Package | Version |
|---------|---------|
| `torch` | 2.11.0+cu128 |
| `transformers` | 5.9.0 |
| `safetensors` | 0.7.0 |
| `tokenizers` | 0.22.2 |
| `vllm` | 0.22.0 |

**Packages NOT present in vLLM venv:**

`torch_npu`, `peft`, `accelerate`, `datasets`, `llamafactory`

### 3.4 [REMOTE-SERVER] CANN / Ascend

| Check | Result |
|-------|--------|
| `torch_npu` | **NOT FOUND** (not installed anywhere) |
| CANN toolkit | **NOT FOUND** |
| Ascend env vars | **NOT FOUND** |
| Ascend directories | **NOT FOUND** under `/usr/local/Ascend`, `/opt` |

> **Conclusion:** The remote server is a **CUDA/NVIDIA** environment (RTX A6000 + CUDA 12.8). It is **not** Ascend-ready and has no NPU hardware.

---

## 4. LLaMA-Factory

| Check | Location | Result |
|-------|----------|--------|
| LLaMA-Factory directory | `[REMOTE-SERVER]` accessible bounded search under `/home`, `/data`, `/opt`, `/workspace`, `/srv` | **NOT FOUND** |
| LLaMA-Factory directory | `[LOCAL-MAC]` designated project | **NOT FOUND** |
| `llamafactory-cli` | `[REMOTE-SERVER]` PATH | **NOT FOUND** |
| LLaMA-Factory git checkout | `[REMOTE-SERVER]` accessible search | **NOT FOUND** |
| LoRA training YAML | `[REMOTE-SERVER]` | **NOT FOUND** |
| Training shell/Python script | `[REMOTE-SERVER]` | **NOT FOUND** |
| Benchmark script | `[REMOTE-SERVER]` | **NOT FOUND** |
| Training log | `[REMOTE-SERVER]` | **NOT FOUND** |

> The remote search was bounded and followed the audit login's readable paths. Owner-private directories under `/home` could not be fully enumerated, so these results mean “not found in the accessible search scope,” not proof that no other copy exists.

---

## 5. CodeLlama Model

### 5.1 [REMOTE-SERVER] Model Files

| Field | Value |
|-------|-------|
| Status | **FOUND** |
| Path | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| Size | ~49 GB |
| `model_type` | `llama` |
| `architectures` | `[LlamaForCausalLM]` |
| `torch_dtype` | `bfloat16` |
| `max_position_embeddings` | 16384 |
| `hidden_size` | 5120 |
| `num_hidden_layers` | 40 |
| `num_attention_heads` | 40 |
| `vocab_size` | 32016 |
| `rope_theta` | 1000000 |

**Tokenizer files:** `tokenizer.json`, `tokenizer.model`, `tokenizer_config.json`, `special_tokens_map.json`, `generation_config.json` — all present.

**Weight files:** 3 × safetensors shards + index; 3 × PyTorch `.bin` shards + index (duplicate formats, consuming extra disk space — no files removed during audit).

### 5.2 [REMOTE-SERVER] Active vLLM Service

| Field | Value |
|-------|-------|
| vLLM version | 0.22.0 |
| Health | HTTP 200 |
| `/v1/models` | HTTP 200 |
| Served model id | `codellama-13b-instruct-hf` |
| Model root | `/data/vllm/CodeLlama-13b-Instruct-hf` |
| `max_model_len` | 16384 |
| `gpu_memory_utilization` | 0.92 |
| Active config file | `/home/████/vllm/qwen3-5.yaml` (filename legacy/misleading; content points to CodeLlama-13B) |
| Fine-tuning permission | `false` (expected for inference endpoint) |

**Metrics at audit time:**

| Metric | Value |
|--------|-------|
| `num_requests_running` | 0 |
| `num_requests_waiting` | 0 |
| `prompt_tokens_total` | 14 |
| `generation_tokens_total` | 3 |
| `request_success_total` (stop) | 1 |

> One prior minimal request; no request in flight.

**Alternate config:** `/home/████/vllm/codellama13b.yaml` also points to the same model, serves `codellama-13b`, with `max_num_batched_tokens=32768`. Not active per process command line.

---

## 6. Dataset

| Check | Location | Result |
|-------|----------|--------|
| `Fine-Tuning.json` | `[LOCAL-MAC]` Desktop, Documents, Downloads, project | **NOT FOUND** |
| `Fine-Tuning.json` | `[REMOTE-SERVER]` accessible bounded search under `/data`, `/home`, `/opt`, `/workspace`, `/srv` | **NOT FOUND** |
| `Fine_Tuning.json` | Accessible `[LOCAL-MAC]` and `[REMOTE-SERVER]` search scope | **NOT FOUND** |
| Any fine-tuning JSON | Accessible `[LOCAL-MAC]` and `[REMOTE-SERVER]` search scope | **NOT FOUND** |
| SHA256 comparison | — | **UNKNOWN** (no dataset file was found to digest) |
| Sample count | — | **N/A** |
| Unique input/output count | — | **N/A** |
| Function count | — | **N/A** |

> The remote search was bounded and followed the audit login's readable paths. Owner-private directories under `/home` could not be fully enumerated, so the dataset result remains **NOT FOUND in the accessible search scope** and the comparison remains **UNKNOWN**.

---

## 7. Current Training State

| Question | Answer |
|----------|--------|
| Is any CodeLlama/LoRA training process running? | **NO** |
| Is any `torchrun` / `deepspeed` / `accelerate launch` running? | **NO** |
| Is any LLaMA-Factory process running? | **NO** |
| Existing GPU workload | vLLM inference (CodeLlama-13b-Instruct-hf) occupying ~43.7 GiB of 49.1 GiB GPU memory |
| Training checkpoints found | **NONE** |
| Training logs found | **NONE** |
| Training output directory found | **NONE** |

---

## 8. Readiness Assessment

| Component | Status | Evidence | Problem |
|-----------|--------|----------|---------|
| Local project | ⚠️ PARTIAL | `[LOCAL-MAC]` Git repo exists (`modelrouter`), research materials present | Project is ModelRouter research, not a CodeLlama LoRA pipeline. No training scripts, dataset, or LoRA config exist locally. |
| SSH | ✅ READY | `[REMOTE-SERVER]` SSH connected successfully via configured key | — |
| Ascend runtime | ❌ NOT READY | `[REMOTE-SERVER]` No NPU hardware, no `npu-smi`, no `torch_npu`, no CANN | Server is NVIDIA CUDA, not Ascend. Requirement mismatch if Ascend is mandatory. |
| LLaMA-Factory | ❌ NOT READY | `[REMOTE-SERVER]` + `[LOCAL-MAC]` Not installed anywhere | Must be installed and configured before training. |
| CodeLlama model | ✅ READY | `[REMOTE-SERVER]` `/data/vllm/CodeLlama-13b-Instruct-hf` (~49 GB), config and tokenizer verified | Model is served by vLLM for inference; usable as base for LoRA training. |
| Dataset | ❌ NOT READY | `[LOCAL-MAC]` + `[REMOTE-SERVER]` No `Fine-Tuning.json` found | Dataset must be created/uploaded before training can begin. |
| NPU resources | ❌ NOT APPLICABLE | `[REMOTE-SERVER]` Hardware is NVIDIA RTX A6000, not Ascend NPU | If Ascend NPU is required, a different server is needed. |
| GPU resources (CUDA) | ⚠️ CONSTRAINED | `[REMOTE-SERVER]` RTX A6000: 4,574 MiB free of 49,140 MiB (vLLM using ~43.7 GiB) | Training cannot share GPU with active vLLM service without stopping it or using a separate resource plan. |
| **LoRA training can start now** | ❌ **NO** | Multiple blockers | See §9 Blocking Issues. |

---

## 9. Blocking Issues

| # | Blocker | Severity | Details |
|---|---------|----------|---------|
| 1 | **No dataset** | CRITICAL | `Fine-Tuning.json` was not found in the accessible `[LOCAL-MAC]` or `[REMOTE-SERVER]` search scope. Training is impossible without data. |
| 2 | **No LLaMA-Factory** | 🔴 CRITICAL | LLaMA-Factory is not installed or checked out on `[REMOTE-SERVER]`. No training framework is available. |
| 3 | **No training pipeline** | 🔴 CRITICAL | No LoRA YAML config, training script, or experiment setup exists on either side. |
| 4 | **GPU capacity constrained** | HIGH | vLLM inference occupies ~89% of GPU memory (43.7/49.1 GiB), leaving about 4.6 GiB free. Training requires either stopping vLLM or provisioning separate GPU resources. |
| 5 | **Missing `peft` / `accelerate` / `datasets`** | 🟠 HIGH | These packages were not found in the accessible environments on `[REMOTE-SERVER]`. Required for LoRA fine-tuning. |
| 6 | **Ascend/NPU mismatch** | 🟡 MEDIUM | If the project plan requires Ascend NPU, the current server (NVIDIA CUDA) cannot satisfy this. Requires re-planning or a different server. |
| 7 | **Local project scope mismatch** | 🟡 MEDIUM | The designated local project (`modelrouter`) is about API routing research, not CodeLlama LoRA fine-tuning. A dedicated project directory or branch may be needed. |

---

## 10. Important Findings

1. **Model is live for inference.** CodeLlama-13b-Instruct-hf is actively served via vLLM v0.22.0 on port 8000 `[REMOTE-SERVER]`. The model files are intact and verified (config, tokenizer, weights). This is a positive asset — the base model is already on-server.

2. **Duplicate weight formats.** `[REMOTE-SERVER]` The model directory contains both safetensors and PyTorch `.bin` shards, duplicating roughly 25 GB of weights. Consider removing one format only after confirming LLaMA-Factory's preference (safetensors recommended).

3. **Misleading config filename.** `[REMOTE-SERVER]` The active vLLM config is `qwen3-5.yaml` but actually serves CodeLlama-13b. This is a naming issue only and does not affect the observed inference endpoint.

4. **No Ascend hardware detected.** `[REMOTE-SERVER]` All hardware checks confirm NVIDIA CUDA only. If the upstream plan mandates Ascend/NPU, the server choice must change.

5. **vLLM venv is not suitable for training.** `[REMOTE-SERVER]` Its readable package metadata lacks `peft`, `accelerate`, and `datasets`. A separate training environment should be created.

6. **Large available RAM.** `[REMOTE-SERVER]` 354 GiB RAM available is more than sufficient for data loading and preprocessing during LoRA training.

7. **No previous training artifacts.** `[REMOTE-SERVER]` No checkpoints, logs, or training output directories were found. This will be a fresh start.

---

## 11. Recommended Next Checks

> These are suggestions only. No action was taken during this audit.

1. **Prepare and upload `Fine-Tuning.json`** — Define the instruction-tuning dataset format (e.g., Alpaca-style `instruction`/`input`/`output`), create or curate the data, compute SHA256, and upload to `[REMOTE-SERVER]`.

2. **Install LLaMA-Factory on `[REMOTE-SERVER]`** — Clone the repository, create a dedicated Python venv with `torch`, `peft`, `accelerate`, `datasets`, `transformers`, and `safetensors`. Verify GPU access from the new environment.

3. **Plan GPU resource allocation** — Decide whether to stop vLLM during training or schedule training during off-hours. LoRA on CodeLlama-13B with 4-bit quantization may fit in ~20 GiB, but the current vLLM occupancy must be addressed.

4. **Create LoRA training configuration** — Write a LLaMA-Factory YAML specifying LoRA rank, alpha, target modules, learning rate, batch size, and output directory for CodeLlama-13b-Instruct-hf.

5. **Clarify Ascend/NPU requirement** — If Ascend is no longer required (server is NVIDIA), update the project plan. If Ascend is mandatory, identify and provision an Ascend-equipped server.

---

## 12. Audit Trail

### [LOCAL-MAC] Commands

| # | Command | Purpose |
|---|---------|---------|
| 1 | `pwd` | Verify working directory |
| 2 | `git status --short --branch` | Check branch and working tree |
| 3 | `git branch --show-current` | Confirm current branch |
| 4 | `git log --oneline -10` | Recent commit history |
| 5 | `git remote -v` | Remote repository URL |
| 6 | `find` (multiple invocations) | Locate project files (MD, YAML, JSON, PY, SH, LOG) |
| 7 | `rg` / `mdfind` | Search for Fine-Tuning.json and CodeLlama artifacts |
| 8 | File reads | README.md, our-project/README.md, our-project/data/README.md, IMPLEMENTATION_RESEARCH.md, vendored script headers |

### [REMOTE-SERVER] Commands (all read-only via SSH)

| # | Command | Purpose |
|---|---------|---------|
| 1 | `hostname` | Server identity (redacted in report) |
| 2 | `date -Is` | Timestamp |
| 3 | `uname -a` | Kernel and architecture |
| 4 | `cat /etc/os-release` | OS version |
| 5 | `uptime` | Server uptime |
| 6 | `free -h` | Memory usage |
| 7 | `df -hT` | Disk usage |
| 8 | `nvidia-smi` | GPU status, memory, processes |
| 9 | `which npu-smi` / `nv-smi` | Check for NPU tools |
| 10 | `lspci` | PCI device inventory |
| 11 | `ps aux` | Running processes |
| 12 | `systemctl list-units` | Active services |
| 13 | `ss -tlnp` | Listening ports |
| 14 | `find` (bounded depth) | Search for LLaMA-Factory, datasets, training artifacts |
| 15 | `python3 -c "import ..."` | Test ML package availability |
| 16 | `cat .venv/pyvenv.cfg` | vLLM venv Python version |
| 17 | Package metadata reads | torch, transformers, etc. version checks |
| 18 | `cat config.json` | Model architecture verification |
| 19 | `ls` model directory | Tokenizer and weight file inventory |
| 20 | `curl` vLLM `/version`, `/health`, `/v1/models`, `/metrics` | API status verification |
| 21 | `cat qwen3-5.yaml`, `codellama13b.yaml` | vLLM config inspection |
| 22 | Environment variable check (filtered) | CANN/Ascend env vars |

### Compliance

- ✅ No SSH password, private key, API key, token, cookie, or secret was written to this report.
- ✅ No server public/private IP address was written to this report.
- ✅ No full username+host combination was written to this report.
- ✅ No environment variable secret was written to this report.
- ✅ Server references use only `REMOTE-SERVER`; local references use only `LOCAL-MAC`.
- ✅ No remote installation, deletion, configuration change, process control, download, or training was performed.

---

*Report generated by STATUS-AUDIT-001 from the read-only command evidence collected during this audit. End of report.*

