# IMAGE WEBUI QUALITY & INFERENCE SAFETY REPORT

Task ID: IMAGE-WEBUI-QUALITY-SAFETY-001
Date: 2026-09-26
Services: SERVER_IP:8020（WebUI） → SERVER_IP:8011（Image API） → Qwen-Image-2.1 → RTX A6000

---

## 1. Quality mapping before / after

### QUALITY_BEFORE_MAPPING（改动前真实调用链）

| 环节 | 实际行为 | 证据 |
|---|---|---|
| WebUI 默认参数 | `quality='auto'`，`num_inference_steps=null`（types.ts DEFAULT_PARAMS） | 源码 types.ts:156-163 |
| WebUI 质量选项 | 下拉提供 auto / low / medium / high（英文），无 steps 联动 | InputBar.tsx qualityOptions |
| 请求体 | generations JSON 始终带 `body.quality`；edits multipart 始终带 `quality` 字段；`num_inference_steps` 仅在用户手填时发送 | openaiCompatibleImageApi.ts:518/596 |
| 后端 GenerationRequest | **没有 quality 字段** → pydantic v2 默认忽略额外字段，quality 被静默丢弃 | schemas.py（改动前） |
| 后端 edits | 从不读取 `form.get("quality")` | server.py（改动前） |
| 实际步数 | 用户显式 steps 有则用之；否则管线默认 | `QwenImage21Pipeline.__call__` 签名 `num_inference_steps=40`（diffusers 0.41.0.dev0，服务器实测签名） |
| `num_inference_steps=4` 代码路径 | **不存在**：全链路（前端源码、部署 dist bundle、后端）没有任何位置把 quality 映射为 4 或自动发送 4 | dist/assets/index-*.js 仅有 `num_inference_steps:null` 默认与透传逻辑 |

结论：改动前 quality 是一个发出去就被丢掉的字段——无论选 low/medium/high，效果都等于管线默认 40 步（或用户手填值）。"quality=high 却只跑 4 步"不会由代码自动产生，但 quality 失效使 UI 档位与真实步数完全脱节。

### 之后

- 后端 `schemas.GenerationRequest` 新增正式字段 `quality: str | None`
- 单一 helper `server._resolve_steps(explicit, quality)`，generations 与 edits 两个端点共用，不散落
- 前端质量下拉改为三档中文：快速=low / 标准=medium / 高质量=high；默认 quality 从 auto 改为 medium（标准）
- 每次请求后端日志打印 `[gen] steps=N explicit=... quality=...`，响应带 `effective_steps`

## 2. Effective step rules（生效步数规则）

优先级（严格按任务书）：

```
explicit num_inference_steps  >  quality preset  >  24 default
```

映射表（`QUALITY_STEPS`，与前端 `qualityStepMap` 一致）：

| quality | steps |
|---|---|
| fast / low | 4 |
| standard / medium / auto | 24 |
| high / xhigh / max | 40 |
| 未提供 / 其他值 | 24（default） |

- 文生图与图生图行为一致（同一 helper）
- 显式 steps 优先于 quality：`quality=high + num_inference_steps=12 → 12`（实测 PASS）

## 3. 4 / 24 / 40 实测（同一 Prompt 真实生成）

统一条件：Prompt `生成一只橙色小猫`，1024×1024，seed=42，n=1，输出至 `/home/syy/ai-serving/tmp/image-output/`（TTL 目录，不入 Git）。

| 案例 | steps | 输出文件 | 大小 | 像素 | 结果 |
|---|---|---|---|---|---|
| A | 4（quality=fast 映射验证后显式 4） | gen_1790401550_0.png | 1,454,121 B | 1024×1024 | 200 PASS |
| B | 24 | gen_1790401610_0.png | 1,835,621 B | 1024×1024 | 200 PASS |
| C | 40 | gen_1790403863_0.png | 1,825,415 B | 1024×1024 | 200 PASS |

同 seed 同 prompt 复跑字节数一致（C 两次跑均为 1,825,415 B），生成路径确定性正常。

补充：quality 映射冒烟 5/5 PASS（512×512）——fast→4、standard→24、high→40、显式 12 压过 high→12、无 quality→24。

## 4. Measured timings（实测计时）

响应新增字段：`queue_wait_seconds` / `load_seconds` / `inference_seconds` / `total_seconds`；
旧字段 `generation_seconds` 保留且等于 `inference_seconds`（兼容定义，实测各案例两值逐条一致）。

| 案例 | load | queue_wait | inference | total | 峰值 VRAM |
|---|---|---|---|---|---|
| A（4 步，1024²） | null（已载入） | 0.000 | 47.128 | 47.813 | 32,069 MiB |
| B（24 步，1024²） | null | 0.000 | 58.729 | 59.320 | 32,069 MiB |
| C（40 步，1024²） | null | 0.000 | 75.039 | 75.610 | 32,101 MiB |
| 映射首例（fast，512²，冷载） | 6.416 | 0.000 | 46.342 | 54.724 | — |

（峰值 VRAM 含 Ollama embedding 常驻 ~14.4GB；本轮未触碰 Ollama。）

## 5. Inference guard（推理保护）

`ModelManager._inference_lock`（threading.Lock）：

- `generate()` 与 `edit()` 全程持有：`ensure_loaded`（含 gpu.lock 获取与管线加载）→ pipeline 调用 → 结果编码（PNG/crop 完成）才释放
- `unload()` 非阻塞抢该锁：抢不到 → 抛 `InferenceBusy`，**不**执行 `_pipeline=None`、**不**执行 `torch.cuda.empty_cache()`、**不**释放 gpu.lock
- 锁顺序统一为 inference_lock → _lock，无反序路径
- idle watcher 调用同一 `unload()`，捕获 `InferenceBusy` 后跳过本轮，15s 后重试
- 手工 `POST /unload` 捕获 `InferenceBusy` → **HTTP 409**：

```json
{"error": {"code": "INFERENCE_BUSY", "message": "image inference is currently running"}}
```

Queue 与 inference guard 职责分离（保留原 Image Queue）：
`request → queue slot → inference guard → gpu.lock → load → inference → return → release`。

## 6. Unload-during-inference test

40 步 1024×1024 生成进行中（queue.running=1）：

| 探针 | 结果 |
|---|---|
| `POST /unload`（推理中） | **409** `INFERENCE_BUSY` — `UNLOAD_DURING_INFERENCE = SAFE` |
| 此时 `/status` | `model_loaded=true`，`gpu_lock="2401887 image-service ..."`（仍 held） |
| 生成请求 | 正常完成 **200**，effective_steps=40，inference 75.039s，无 CUDA 错误 |
| 生成完成后 `POST /unload` | **200** `{"unloaded":true,"model_loaded":false}` |
| 终态 | `model_loaded=false`，`gpu_lock=null`（FREE） |

GPU lease remained held: **YES**（推理全程 + 409 响应期间锁未释放）。

## 7. Zrald lease safety test

同一 40 步推理窗口内对 SERVER_IP:8010 非 health 路径（触发 lease 获取）：

| 时点 | 结果 |
|---|---|
| 推理中 probe #1 | 503 `GPU_BUSY`，message=`lease held by [2401887 image-service 1790403138.66789]` |
| 中间 `POST /unload` | 409 `INFERENCE_BUSY`（未释放 lease） |
| 推理中 probe #2 | 503 `GPU_BUSY`，message=`lease held by [2401887 image-service ...]`（仍是 image 持有） |
| Image 推理结束并 unload 后 | image 侧 `gpu_lock=null`、FREE；Zrald `/manager/status` 200 `lease_held=false`、`backend_alive=false`（空闲常态） |

Zrald blocked throughout Image inference: **PASS**。message 显示持有者是 image-service（Zrald 的 lease 获取先于对 Ollama 占用的判定，证据可区分持有者），证明 manual unload 没有提前释放 lease。
（注：unload 后 Zrald 是否能立即拉起还受 Ollama embedding 常驻影响，属既有环境行为，本轮未改 Ollama。）

## 8. Queue timing metrics

两并发 `POST /v1/images/generations`（1024×1024，24 步，间隔 1.5s）：

| 请求 | status | queue_wait_seconds | inference | total |
|---|---|---|---|---|
| #1 | 200 | **0.000** | 59.340 | 61.177 |
| #2 | 200 | **59.698** | 63.616 | 123.927 |

- 串行化 PASS（#2 的推理在 #1 释放槽位后才开始）
- 第二请求 queue_wait_seconds > 0，第一请求 ≈ 0：**PASS**
- queue wait 不再计入 inference（#2 inference=63.6s，total=123.9s，差值即排队）

## 9. Browser E2E（SERVER_IP:8020 真实浏览器）

1. 打开 WebUI，初始状态含上一轮持久化的自定义 steps=4 → UI 显示 **「步数（自定义）· 生效步数 = 4」**，矛盾状态被明确标注为自定义
2. 清空 steps 字段，选择质量 **高质量** → UI 显示 **「生效步数 = 40（按质量档）」**
3. 发起生成（中文 prompt `生成一只橘色小猫`，1024×1024）→ 后端日志：
   `[gen] steps=40 explicit=None quality=high size=1024x1024 n=1`
   → 请求体/日志确认 num_inference_steps 解析为 40：**PASS**
4. 生成完成后画廊最新卡片渲染出缩略图（`data:image/webp`，720×720），队列回 0/0：**图片正常显示 PASS**
5. 切换质量为 **快速** → UI 显示 **「生效步数 = 4（按质量档）」**：**PASS**

## 10. Regressions

| 项 | 结果 |
|---|---|
| Generation 回归 | PASS（映射 5/5、A/B/C、浏览器生成均 200） |
| Edit 回归 | PASS：`quality=high`（无显式 steps）→ effective_steps=**40**，输出 1024×1024；`num_inference_steps=12 + quality=high` → effective_steps=**12**（显式覆盖） |
| Queue 回归 | PASS（见 §8） |
| TTL 配置 | `IMAGE_OUTPUT_RETENTION_SECONDS=1800` / `IMAGE_CLEANUP_INTERVAL_SECONDS=300`（service.local.env + 进程 environ 实测均未改动，未重做 60s 压测） |
| Idle 安全（IDLE=20 临时实测后恢复 600） | PASS：推理中 age 跨过 20s（t=30 时 age=22.2 一直到 t=50）`model_loaded` 始终 true、锁始终 held、生成 200；生成结束后 36.2s watcher 完成卸载（loaded→false→FREE） |
| 最终配置恢复 | 进程 environ：IDLE=600、RETENTION=1800、CLEANUP=300、QUEUE 1/8/480 全部正确 |
| 端口 | 8010 200（/manager/status，backend_alive=false 空闲常态）/ 8011 200 / 8020 200 / 11434 200 / 3000 200 / 8000 CLOSED |
| GPU | 299 MiB 正常水位，gpu.lock FREE |
| 错误响应信封 | 统一为 `{"error":{"code","message"}}`（HTTPException 处理器新增；400 INVALID_SIZE 实测；错误 code 不变，WebUI getApiErrorMessage 优先读 error.message，兼容改善） |
| 旧客户端字段 | generations 仍返回 b64/b64_json/path/seed；edits 仍返回 width/height/path（edit 实测 out 1024×1024）；`generation_seconds` 保留 |
| 前端测试 | 服务器 `npm test`：34 文件 / **576 用例全绿**；`npm run build` 成功，dist 已重建 |
| 上轮能力 | 文生图 / 图生图 / Queue / TTL / GPU lock 均未破坏（本轮全部复测 PASS） |

未触碰：Zrald、Ollama、vLLM、CUDA、driver、网络、Open WebUI、8020 端口、模型权重、Docker、数据库。

## 11. Git

- 改动文件（白名单暂存，禁 add -A）：
  - `serving/services/image/{server.py,model_manager.py,schemas.py,README.md}`
  - `webui/image-platform/upstream/src/{types.ts,components/InputBar.tsx,components/input/inputParamsPanel.tsx}`
  - `reports/IMAGE_WEBUI_QUALITY_SAFETY.md` + `coordination/*`
- 排除：生成图片、tmp、logs、dist、node_modules、模型、venv、含真实 IP 的本地配置（均 gitignore 或未暂存）
- secret scan：真实 IP / 私钥 / 凭据扫描 → 见最终回复（PASS 才提交）
- commit：`fix: align image quality presets and inference lifecycle` → push main

## 12. 人工视觉观察（不打分，只描述差异）

素材：A/B/C 三张 1024×1024（同 prompt、同 seed）。

- **4-step（FAST_PREVIEW）**：橙色毛团与坐姿轮廓可辨，背景为灰绿色块；**猫脸未形成**——看不到清晰的眼睛、鼻子、耳内结构；整体严重模糊，毛发糊成片，轮廓与地面边界融合。符合"快速预览"定位。
- **24-step（STANDARD）**：猫脸完整清晰——双眼（虹膜、瞳孔、眼神光）、鼻、嘴线、双耳、胡须齐全；条纹毛发、胸毛、爪部纹理可辨；坐姿轮廓完整，背景为自然虚化的土路。照片级。
- **40-step（HIGH_QUALITY）**：与 24 步同构图（同 seed），上述细节全部成立；胸部绒毛、耳缘、爪垫周边的毛流更扎实，背景过渡更平滑，无背景噪声斑块；与 24 步差异细微。文件大小（1.83MB vs 1.83MB）与画质无关，仅作记录。

观察结论与档位预期一致：4 步=草稿级快速预览，24 步=可用标准质量，40 步=细节再上一档。

## 13. 遗留与风险

- Ollama embedding 周期驻留仍决定 Image **冷加载**窗口（既有问题，本轮未改；模型载入后不受影响）；Gateway 方案仍为 NEXT_ACTION 待办
- 浏览器持久化的旧自定义 steps 会让存量用户看到"自定义"标注（预期行为，清空后回归质量档）
- 上游 xhigh/max 两档被映射到 40（与 high 同级），仅在 gpt-image-2.5 模型下可选，本部署模型不会出现
