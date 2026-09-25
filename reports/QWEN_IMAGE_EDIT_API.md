# Qwen-Image Edit API Report

任务编号：QWEN-IMAGE-EDIT-API-001
时间：2026-09-26 01:15 – 01:40 CST
性质：在现有 :8011 服务上实现 `POST /v1/images/edits`（未动 :8010 / Ollama / vLLM / CUDA / 网络 / Open WebUI，未下载任何模型）
服务器：SERVER_IP_REDACTED（用户 syy）

---

## 1. Pipeline inspection

环境（未变）：Python 3.12.3 · Torch 2.14.0+cu130 · **Diffusers 0.41.0.dev0** · `QwenImage21Pipeline import PASS`

修改前文生图 smoke：HTTP **200**（load 1.31 s / gen 60.0 s）→ 卸载 ✓（原文生图基线完好）

模型卡（本地 README，官方示例）编辑入口即：

```python
from diffusers import QwenImage21Pipeline
pipe(image=input_image, prompt="Change the background to a sunset beach", num_inference_steps=40, ...)
```

## 2. Actual edit pipeline class

```
EDIT_PIPELINE_CLASS = QwenImage21Pipeline   （同一类、同一套已加载权重，不引入第二模型/第二管线）
```

同版本存在的其他候选（**未采用**，避免新权重）：
- `QwenImageEditPipeline` / `QwenImageEditPlusPipeline`（面向独立 Qwen-Image-Edit 模型权重）
- `QwenImageEditInpaintPipeline`（mask + strength，需对应 inpaint 权重）
- `QwenImageImg2ImgPipeline`（有 strength，但非模型卡官方 2.1 编辑入口）

## 3. Supported parameters（`inspect.signature(QwenImage21Pipeline.__call__)` 实测）

```
SUPPORTED_EDIT_ARGUMENTS = prompt, image, negative_prompt, true_cfg_scale,
  height, width, num_inference_steps, sigmas, num_images_per_prompt, generator,
  latents, prompt_embeds*, output_type, output_resolution, use_kv_cache, ...
```

| 请求字段 | 支持 | 说明 |
|---|---|---|
| image | ✅ | 官方编辑示例同款 |
| prompt | ✅ | 必填 |
| negative_prompt | ✅ | 可选 |
| num_inference_steps | ✅ | 可选 |
| seed | ✅（经 generator） | 可选 |
| width / height | ✅ | 默认取输入图尺寸（实现时补上：未显式传则跟随输入，避免掉到1024默认画布） |
| **mask** | ❌ | **MASK_EDIT = UNSUPPORTED_BY_CURRENT_PIPELINE**（无该参数，不伪造 inpaint） |
| **strength** | ❌ | 当前类无此参数，不传 |

## 4. API implementation

- `server.py`：`POST /v1/images/edits`（multipart：`image` File + `prompt/negative_prompt/num_inference_steps/seed/width/height` Form）；`RequestValidationError→400` 统一错误风格；响应 `EditResponse{created, model, data[{path,width,height}], load_seconds, inference_seconds}`（与 generation 风格一致）
- `model_manager.py`：新增 `edit()`，**复用** `ensure_loaded()`（flock 租约 + Ollama/nvidia 双重复查 + lazy load + 失败放锁）与 idle watcher；只传官方真实参数
- `schemas.py`：`EditImage / EditResponse`
- 仅改上述3文件 + README（未重写 server，未动其他服务）
- 依赖：`python-multipart 0.0.32`（装入**现有** env/image，未建第二 venv）

## 5. Input validation

| 规则 | 实现 |
|---|---|
| 格式 | PIL 打开，PNG/JPEG/WEBP（Pillow 通吃）；损坏/非图 → **400 INVALID_IMAGE** |
| 大小 | **MAX_UPLOAD_MB = 20**，超限 → 400 IMAGE_TOO_LARGE；空文件 → 400 |
| 模式 | RGB/RGBA 直接透传（**保留 alpha**）；其他模式转 RGB |
| 缺字段/空 prompt | 400 INVALID_REQUEST |

## 6. Lazy load

- 服务启动 `model_loaded=false`（每轮重启后确认）
- 顺序：**EDIT REQUEST → acquire flock → Ollama/nvidia 复查 → lazy load → edit → response**
- 实测：冷编辑 `load_seconds=1.31–6.98`（页缓存状态）；热编辑 `load_seconds=0.0`（连续两次编辑）

## 7. GPU lock

- 编辑全程走既有 `state/gpu.lock` **flock** 租约；取锁后复查 Ollama `/api/ps` + nvidia 大占用 → 冲突503
- 编辑期间 `/status.gpu_lock` 显示 `"<pid> image-service ..."`（实测持有）；idle/unload 释放
- 与 generation 完全同一条生命周期，无旁路

## 8. First edit test（架构图）

- 输入：`logs/image/e2e-validation/model-serving-architecture.png`（2048² RGBA）
- prompt：`Change the diagram title to "Unified AI Model Server". Keep the overall layout...`
- 结果：HTTP **200**
  - 4-step 轮：load1.49/infer52.4 → 输出有效但偏淡（std 5.43→1.61，信息变少）
  - **24-step 轮（采用）**：load 0（热）/ **infer 149.5 s**，输出2048²，**std 5.43→13.81**（版式保留且内容更清晰），mean_abs_diff **2.29**
- **Architecture edit = PASS**（输出 `edit-validation/architecture-edited.png`，2,586,890 B）

## 9. Apple color edit test

- 输入：`edit-validation/source-apple.png`（由现有 generations 生成，mean R/G/B = 205.7/127.8/100.0，红占优）
- prompt：`Change the red apple to a green apple. Keep the wooden table, composition, lighting...`（4-step）
- 结果：HTTP **200**，infer **59.4 s**，2048²
- 颜色量化：**RED 205.7→169.5（−36）**，**GREEN 127.8→165.8（+38）**；G−R 从 **−77.9 → −3.8**（明显转绿）
- **IMG2IMG_EDIT = PASS**（输出 `edit-validation/edited-green-apple.png`，3,671,890 B，PIL 有效）

## 10. Performance（MEASURED，非沿用文生图数据）

| 项 | 值 |
|---|---|
| cold edit load | **1.31 – 6.98 s**（页缓存） |
| edit inference（4-step, 2048²） | **52.4 / 59.4 / 67.3 / 79.7 s**（多次实测区间） |
| edit inference（24-step, 2048²） | **149.5 s** |
| input → output dims | 2048×2048 → 2048×2048 |
| peak VRAM（编辑期间采样） | **≈34.7 GB 区间**（与文生图同量级；卸载后回落） |

## 11. Unload

- `POST /unload` → `{"unloaded":true,"model_loaded":false}`，`gpu_lock=null`，flock 探针 FREE
- VRAM_BEFORE（加载后）≈3.7–34.7 GB 视阶段 → **VRAM_AFTER_UNLOAD ≈650–682 MiB**（服务 context+桌面，如实记录非零）

## 12. Idle unload

- 以 `IMAGE_IDLE_TIMEOUT=60` 重启 → 发起一次 edits（实测 `load 6.976 / infer 67.254`，`last_used` 被刷新）
- 85 s 后 `/status`：`model_loaded=false` → **edits 触发的 idle 自动卸载 PASS**
- 恢复：无 env 重启 → `/status.idle_timeout_seconds = 600` ✅

## 13. Error cases（6/6）

| # | 场景 | HTTP | code |
|---|---|---|---|
| 1 | 无任何字段 | **400** | INVALID_REQUEST |
| 2 | 有 image 无 prompt | **400** | INVALID_REQUEST |
| 3 | prompt 为空 | **400** | INVALID_REQUEST |
| 4 | 非图片文件（README.md） | **400** | INVALID_IMAGE |
| 5 | 超大图（50.4MB 噪声 PNG） | **400** | IMAGE_TOO_LARGE（20MB 限） |
| 6 | 空文件 | **400** | INVALID_IMAGE |

- 全程无 stack trace、无敏感路径外泄；校验发生在 lazy load **之前**（错误请求不加载模型，实测 status 仍 false）
- 503（GPU_BUSY）见 §锁测试；500 路径已实现（`EDIT_FAILED`，本轮未强造管线异常）

## 14. 互斥测试（与 Zrald）

| 方向 | 结果 |
|---|---|
| Zrald 持租约 → POST edits | **503** `GPU_BUSY: gpu lease held by [zrald-manager …]`（image 锁未被抢）→ **Zrald blocks Image edit = PASS** |
| edits 进行中 → Zrald chat | **503** `GPU_BUSY: lease held by [image-service …]`；edits 正常完成 200 → **Image edit blocks Zrald = PASS** |
| 测试后 | zrald 后端优雅停止（watchdog 放锁）；image 卸载放锁；GPU 回落 |

（全程未让两个大模型同时驻留 GPU）

## 15. Regression test

最终顺序（恢复600 后）：`/health` ok → `/status` idle600 → **generations 200**（load6.13/gen64.3）→ **edits 200**（infer79.7，2048²）→ `/unload` 释放锁 → GPU 682 MiB

```
TEXT_TO_IMAGE_REGRESSION = PASS
IMAGE_TO_IMAGE           = PASS
```

## 16. API usage（摘要，完整见服务 README）

```bash
curl -X POST http://SERVER_IP:8011/v1/images/edits \
  -F "image=@input.png" \
  -F "prompt=Change the red apple to a green apple" \
  -F "num_inference_steps=4"
```

输出保存：`logs/image/edit-validation/{architecture-source,architecture-edited,source-apple,edited-green-apple}.png`（**禁止入 Git**）

## 17. Remaining limitations / observations

1. **mask 编辑不支持**（官方当前类无参数）；如需 inpaint 需 QwenImageEditInpaint 对应权重（新模型，未授权不下）。
2. **strength 不支持**（同上，仅用真实签名字段）。
3. 低步数（4-step）编辑偏保守/偏淡：架构图需 ≥24 步才能清晰保留版式；苹果4-step 变色已足够明显。
4. 观察：两轮特殊条件下（一次伴随历史 OOM 事件、一次 idle60 重启后）出现过"编辑成功但 status 短暂显示 model_loaded=false"的瞬时读数异常；**受控复现 4/4 全部正常**（loaded=true、锁持有、卸载干净），未复现根因，记录为观察项，不阻塞功能。
5. 500（管线异常）路径已实现但未强造触发用例。
6. 图片编辑无 WebUI（按要求纯 API）。

## 18. Changes made

- 远端：`services/image/{server.py, model_manager.py, schemas.py, README.md}` 修改；env/image 增 python-multipart；`logs/image/{edit-validation,generated}` 新增样例（不入 Git）
- LOCAL：`serving/services/image/*` 同步；本报告；coordination 四文件更新
- Git：见最终回复（secret scan → commit → push）
