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

## API Usage（统一 SERVER_IP，禁止写真实 IP）

### 文生图

```bash
curl -X POST http://SERVER_IP:8011/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A red apple on a wooden table","n":1,"size":"2048x2048","num_inference_steps":4}'
```

### 图生图（edits，multipart）

```bash
curl -X POST http://SERVER_IP:8011/v1/images/edits \
  -F "image=@input.png" \
  -F "prompt=Change the red apple to a green apple" \
  -F "num_inference_steps=4"          # 可选
  # -F "seed=42"                       # 可选
  # -F "negative_prompt=..."           # 可选
  # -F "width=2048" -F "height=2048"   # 可选，默认=输入图尺寸
```

响应（与 generation 统一风格）：

```json
{"created":...,"model":"Qwen-Image-2.1",
 "data":[{"path":"...","width":2048,"height":2048}],
 "load_seconds":...,"inference_seconds":...}
```

约束（以官方 QwenImage21Pipeline 真实签名为准）：
- 支持字段：image / prompt / negative_prompt / num_inference_steps / seed / width / height
- **mask 不支持**（当前 pipeline 无该参数 → MASK_EDIT = UNSUPPORTED_BY_CURRENT_PIPELINE）
- **strength 不支持**（当前 pipeline 无该参数）
- 输入：PNG / JPEG / WEBP，≤20MB，RGB/RGBA（RGBA 保留 alpha 透传）
- 错误：缺字段/空 prompt/非图片/超限 → 400；GPU 租约冲突 → 503 GPU_BUSY；管线失败 → 500
- lazy load + flock 租约 + idle600 自动卸载 与 generation 完全共用
