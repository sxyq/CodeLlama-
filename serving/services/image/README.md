# Qwen-Image-2.1 Service (STAGED — NOT STARTED)

- config: /home/syy/ai-serving/configs/image/qwen-image-2.1.yaml
- model: /data/vllm/ImageModel/Qwen-Image-2.1（local_files_only）
- port: 8011
- env（deployment 阶段创建）: /home/syy/ai-serving/env/image/

## 行为设计

| 要求 | 实现 |
|---|---|
| 启动 != 加载 | server.py 导入不触 GPU；MODEL_LOADED 初始 false |
| Lazy load | 首个 POST /v1/images/generations 才 `DiffusionPipeline.from_pretrained` |
| BF16 + CPU offload | torch_dtype=bfloat16 + enable_model_cpu_offload() |
| GPU lock | state/gpu.lock（O_EXCL + 存活 PID 检查），跨服务互斥 |
| Ollama 冲突 | 加载前 GET 11434/api/ps，size_vram>1GB → HTTP 503 GPU_BUSY（绝不 kill Ollama runner） |
| Idle unload | 600s 无请求自动 del + gc + torch.cuda.empty_cache |
| 手工卸载 | POST /unload |

## API

- GET  /health
- GET  /status
- POST /v1/images/generations
- POST /v1/images/edits → 501 NOT IMPLEMENTED（本轮明确未实现）
- POST /unload

## 本轮状态

- code STAGED；服务未启动；模型未加载；venv 未安装
- 启动命令（仅部署阶段）: env/image/bin/uvicorn server:app --host 0.0.0.0 --port 8011
