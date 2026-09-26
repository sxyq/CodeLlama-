# Qwen-Image-2.1 Service（RUNNING：queue + CORS + TTL）

- model: /data/vllm/ImageModel/Qwen-Image-2.1（local_files_only）
- port: 8011
- env: /home/syy/ai-serving/env/image/
- 启动: `bash $HOME/ai-serving/scripts/image/start_image_service.sh`
  （source `configs/image/service.local.env` → uvicorn；真实 CORS origin 只存在于该 local env，永不入 Git）

## 行为设计

| 要求 | 实现 |
|---|---|
| 启动 != 加载 | server.py 导入不触 GPU；MODEL_LOADED 初始 false |
| Lazy load | 首个排队成功的请求才 `DiffusionPipeline.from_pretrained` |
| BF16 + CPU offload | torch_dtype=bfloat16 + enable_model_cpu_offload() |
| GPU lock | state/gpu.lock（flock LOCK_EX\|LOCK_NB，文件常驻不 unlink），跨服务互斥 |
| Ollama 冲突 | 加载前 GET 11434/api/ps，size_vram>1GB → HTTP 503 GPU_BUSY（绝不 kill Ollama runner） |
| Idle unload | `IMAGE_IDLE_TIMEOUT`（600s）无请求自动卸载；推理进行中不卸载（_inference_depth 防护） |
| 手工卸载 | POST /unload |
| 统一队列 | `queue_manager.py`：generations+edits 共享单槽，max_concurrent=1 / max_pending=8 / timeout=480s |
| 队列顺序 | request → queue slot → gpu.lock（ensure_loaded 内）→ Ollama/nvidia 复核 → 推理 → 释放 slot |
| 临时输出 | `temp_output.py` → `$HOME/ai-serving/tmp/image-output/`，TTL `IMAGE_OUTPUT_RETENTION_SECONDS`（1800s），`IMAGE_CLEANUP_INTERVAL_SECONDS`（300s）周期 + 启动即扫；仅删根下常规文件，symlink/越界拒绝 |
| CORS | `IMAGE_ALLOWED_ORIGINS` 精确 origin 白名单（代码零真实 IP，无 `*`） |
| negative_prompt | QwenImage21 仅当 true_cfg_scale>1 才生效 → 提供 negative_prompt 时传 `true_cfg_scale=4.0` |
| 输出格式 | 管线 PNG；`output_format=jpeg/webp` 时服务端转码（JPEG 白底合成） |

## API

- GET  /health
- GET  /status → 含 `queue:{running,pending,max_pending}`（旧字段保留）
- POST /v1/images/generations → `data[].b64`（旧）+ `data[].b64_json`（上游）
- POST /v1/images/edits（multipart）→ `data[].b64_json/path/width/height`
- POST /unload

## 本轮状态（IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001）

- RUNNING：queue + CORS + TTL cleaner 已上线；E2E（串行化/TTL/浏览器/回归）全 PASS
- 详见 `reports/IMAGE_WEBUI_QUEUE_TEMP_STORAGE.md`

## API Usage（统一 SERVER_IP，禁止写真实 IP）

### 文生图

```bash
curl -X POST http://SERVER_IP:8011/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A red apple on a wooden table","n":1,"size":"2048x2048","num_inference_steps":4}'
# 可选：negative_prompt / seed / output_format(png|jpeg|webp)
# size="auto" → 1024x1024；512–2048 且 16 倍数，越界 400 INVALID_SIZE
```

### 图生图（edits，multipart）

```bash
curl -X POST http://SERVER_IP:8011/v1/images/edits \
  -F "image=@input.png" \        # 亦接受上游字段名 image[]（单张）
  -F "prompt=Change the red apple to a green apple" \
  -F "size=auto" \               # auto/缺省=保持原尺寸；"WxH"=显式尺寸
  -F "num_inference_steps=4"     # 可选
  # -F "seed=42" / -F "negative_prompt=..." / -F "output_format=jpeg"
  # 旧客户端仍可用：-F "width=..." -F "height=..."（优先于 size）
```

响应（generation 与 edit 统一风格）：

```json
{"created":...,"model":"Qwen-Image-2.1",
 "data":[{"b64_json":"...","path":"...","width":...,"height":...}],
 "load_seconds":...,"inference_seconds":...,"queue":{"running":0,"pending":0,"max_pending":8}}
```

错误码：缺字段/空 prompt/非图片/超限/尺寸越界 → 400（INVALID_REQUEST/INVALID_IMAGE/INVALID_SIZE/INVALID_FORMAT/
MASK_UNSUPPORTED/MULTIPLE_IMAGES）；队列满 → 429 QUEUE_FULL；排队超时 → 503 QUEUE_TIMEOUT；
GPU 租约冲突 → 503 GPU_BUSY；管线失败 → 500。

约束（以官方 QwenImage21Pipeline 真实签名为准）：
- 支持字段：image(或 image[]) / prompt / negative_prompt / num_inference_steps / seed / size（或 width/height）/ output_format
- **mask 不支持** → UI 已禁用并提示，后端 400 MASK_UNSUPPORTED
- **strength 不支持**；多图输入不支持 → 400 MULTIPLE_IMAGES
- 输入：PNG / JPEG / WEBP，≤20MB，RGB/RGBA（RGBA 保留 alpha 透传）；上传仅内存读取，不落盘
- keep-original：ceil 到 16 倍数生成后 crop 回精确原尺寸；>2048 边等比缩到 2048
- lazy load + flock 租约 + idle 自动卸载 + 统一队列 与 generation 完全共用
