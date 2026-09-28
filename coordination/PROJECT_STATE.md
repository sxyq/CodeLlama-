# PROJECT_STATE

更新时间：2026-09-28  
Task: LOCAL-MODEL-UNIFIED-DYNAMIC-SERVING-001

| 项 | 值 |
|---|---|
| Experiment ID | DEFAULT-LORA-001 |
| 当前阶段 | 三级 Serving 策略落地完成（待 Commander 审阅） |
| VLLM_RUNNING | NO（8000 CLOSED；**VLLM_DYNAMIC = NOT_NEEDED**，无模型需要 vLLM） |
| ZRALD :8010 | **泛化为通用 llama.cpp Model Manager**（原 zrald_lease_manager.py 单模型 → registry 驱动），8010 API 向后兼容全过 |
| OLLAMA | :11434 网关 → 127.0.0.1:11435；**14 模型** = 原 10（完好）+ 新 4 local |
| OLLAMA 新增 | `qwen3.5:9b-local`（completion+vision，图片实测准确）、`gemma3:12b-it-local`（同）、`deepseek-coder:6.7b-instruct-local`（code smoke ✓）、`codellama:7b-instruct-local`（code smoke ✓） |
| OLLAMA 导入失败 | Qwen3-14B / Mistral / StarCoder2（`unsupported architecture`）+ gemma2 ×2（daemon Go panic，systemd 自恢复）→ 全部转 LEVEL 2 |
| LLAMA.CPP 动态 | `~/ai-serving/services/llama-manager/llama_manager.py` + `configs/llama-manager/models.yaml`（6 模型：zrald default + qwen3-14b / mistral-7b / gemma2-9b-it / gemma2-9b / starcoder2） |
| GGUF 转换 | 5×Q4_K_M 落 `/data/vllm/ConvertedGGUF/`（共 28G）；F16 中间文件已清理（回收 89G）；llama-cli 5/5 PASS |
| 转换环境 | `env/image` venv（torch2.14/tf5.17）+ 离线 wheel 装 sentencepiece；**未动全局 Python/CUDA/driver**；服务器 PyPI 直连不通（执行机下载 wheel scp 安装） |
| 统一 GPU 调度 | 网关新增 `LlamaGate`（`GATEWAY_LLAMA_STATUS` → 8010 `lease_held`）；等待条件 = Image busy ∨ llama lease |
| 互斥闭环实测 | A：llama 持锁→网关扣 embed 12s→释放自动 200；B：llama 持锁→Image `waiting_for_gpu`→释放→自动 200/84.9s；C：Image 运行→llama 503 GPU_BUSY + embed 扣 63.8s→完成自动 200 |
| 模型切换 | switch_count 实测；A 长任务推理中 B 请求**排队 14.8s 后 200**（不 kill 在跑任务）；租约跨切换保持 |
| 回归 | Image 1024×1024 200×2；Ollama `qwen3:8b`+`embed0.6b` 200；Zrald 兼容（无 model 字段/未知 model 回退 default）；8010/8011/8020/3000/11434 端点全 200 |
| Qwen3.5-9B | 权重保留原位（19G safetensors 未动）+ Ollama `qwen3.5:9b-local` 全能力（文本+视觉） |
| 磁盘 | 开始可用 2.0T → 峰值 1.1T → 当前 1.2T（红线 500GB 全程未触） |
| OOM | 本轮 0 次；峰值 VRAM 33,469 MiB < 47,000 HIGH_VRAM 线 |
| 本轮改动 | serving/（llama-manager 新增 + 网关 LlamaGate）+ reports/ + coordination/；**原权重、/home/yuyong/vllm、systemd、Image、Zrald 源码均未改** |
| Git | 见 LAST_HANDOFF |
| Next Action | WAIT FOR COMMANDER REVIEW |
