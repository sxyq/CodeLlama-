# IMAGE_WEBUI_QUEUE_TEMP_STORAGE — 交付报告

任务编号：IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001
日期：2026-09-26
状态：COMPLETE — READY FOR COMMANDER REVIEW

---

## 1. Upstream UI

| 项 | 值 |
|---|---|
| UPSTREAM_REPO | CookSleep/gpt_image_playground |
| UPSTREAM_BRANCH | main |
| UPSTREAM_COMMIT | aa2556df3f0b2e211645d7fce095bb442bcea059（2026-09-24） |
| UPSTREAM_LICENSE | MIT |
| 技术栈 | React 19 + Vite 6 + TypeScript 5.8，纯静态 SPA（浏览器直连 API） |
| package manager | npm（package-lock.json） |
| build command | `npm run build` = `tsc -b && vite build` |
| 文生图能力 | 有（Images API JSON POST /v1/images/generations） |
| 图片编辑能力 | 有（multipart POST /v1/images/edits） |
| custom provider | 有（OpenAI 兼容 + JSON 导入自定义供应商） |
| custom resolution | 有（尺寸选择器：自动 / 按比例 / 自定义宽高） |
| model/provider configuration | 有（多配置 Profiles，可预置注入） |
| 重大变化判定 | 无（可正常接入；未停止、未替换项目） |

审计方式：GitHub API + 官方 tarball（codeload）拉取至本地与服务器双端，全文核对 README/package.json/vite.config/src 关键路径。

## 2. 部署结构

```
/home/syy/ai-serving/webui/image-platform/
├── upstream/          # 源码 @ aa2556df + 本平台 P1–P5 补丁
├── dist/              # 构建产物（含嵌入 preset，不入 Git）
├── config/
│   ├── models.json            # 模型注册表（服务器真实值，不入 Git）
│   ├── models.example.json    # 模板（SERVER_IP 占位，入 Git）
│   └── preset-config.json     # 构建时由 gen-preset-config.py 生成（不入 Git）
├── scripts/
│   ├── gen-preset-config.py   # models.json → 上游 preset 配置
│   ├── build_webui.sh         # preset 生成 + npm run build → dist/
│   └── serve_static.py        # ThreadingHTTPServer 静态服务，无目录列表
└── README.local.md
```

WebUI 源码与必要配置入 Git；`node_modules/`、`dist/`、真实 IP 配置均被 `.gitignore` 排除。

## 3. 构建方法（宿主机直接构建，无 Docker）

- Node：v22.23.3（LTS，独立安装于 `$HOME/ai-serving/env/node-v22.23.3-linux-x64/`，未改全局环境）
- npm：10.9.9；registry：registry.npmmirror.com（`npm ci`）
- 构建命令：`bash scripts/build_webui.sh`（内部：gen-preset-config.py → `VITE_DEFAULT_API_URL=<preset> npm run build` → 拷贝 upstream/dist → dist/）
- Node version / Package manager version / Build command / Build result：见上（build ✓ built in 6.91s，产物含 index/assets/sw.js）

## 4. 公开端口

| 端口 | 用途 | 说明 |
|---|---|---|
| SERVER_IP:8020 | WebUI（本平台） | serve_static.py，0.0.0.0 绑定，仅内网，无账号认证 |
| SERVER_IP:8011 | Image API（后端） | FastAPI/uvicorn，lazy load |
| SERVER_IP:8010 | Zrald | 未改动 |
| SERVER_IP:11434 | Ollama | 未改动 |
| SERVER_IP:3000 | Open WebUI | 未改动 |
| SERVER_IP:8000 | vLLM | 保持 CLOSED |

## 5. API 集成（OLD_API_COMPATIBILITY = PASS）

上游契约 → 后端适配（后端为主实现，前端零改动即可互通）：

| 上游行为 | 后端处理 |
|---|---|
| JSON generations：`model/quality/output_format/moderation` 等额外字段 | pydantic 额外字段忽略，保留 `prompt/n/size/negative_prompt/num_inference_steps/seed/output_format` |
| `size="auto"` | 文生图 → 1024×1024；图生图 → 保持原图尺寸 |
| edits multipart 字段 `image[]` | 同时接受 `image[]`（上游）与 `image`（旧 curl 客户端） |
| edits `size` 字段 | `auto`→保持原尺寸；`WxH`→显式尺寸（512–2048、16 倍数校验） |
| 旧客户端 `width/height` 表单字段 | 保留，优先级高于 size |
| 响应读取 `data[].b64_json` | 文生图/图生图均新增 `b64_json`；保留旧 `b64/path/width/height` |
| `output_format: png/jpeg/webp` | PNG 管线输出按需转码（JPEG 白底合成，WebP 保 alpha） |
| Authorization 头 | 后端不校验认证；preset 内 `apiKey: internal-no-auth` 为占位（非凭据） |

实测：
- 旧客户端文生图（JSON，字段 b64/path）→ 200，字段齐全
- 旧客户端图生图（`-F image=@` + width/height）→ 200，`path/width/height/b64_json` 齐全
- 负向提示走 `true_cfg_scale=4.0` 路径 → 200（Qwen-Image-2.1 默认 true_cfg=1，仅当提供 negative_prompt 时启用 CFG，否则该参数被管线忽略）

## 6. 文生图（浏览器真实测试）

- Model: Qwen-Image-2.1（preset 配置自动注入，URL/Images API/timeout=600 全部就位）
- Prompt（任务指定原文）：`A clean futuristic AI server room, professional technical illustration, soft lighting.`
- 1024×1024 → **PASS**（任务卡显示 1024×1024，结果图渲染于画廊）
- 1536×1024（1K 3:2 预设）→ **PASS**（任务卡 1536×1024）
- 控件链路：步数=4、种子=42/43 均随请求生效

**Text-to-image: PASS**

## 7. 图生图（浏览器真实测试）

Prompt（任务指定原文）：`Change the main object color to blue. Keep the composition and background unchanged.`

- 输入素材：上一轮生成图片（经「编辑输出」一键转参考图，等价于任务允许的"上一轮生成图片"）
- Keep original（size=auto，输入 1536×1024）→ 输出任务卡 **1536×1024** → **PASS**
- Custom width/height（显式 1024×1024，输入 1536×1024）→ 输出任务卡 **1024×1024** → **PASS**
- 后端日志：两次 `POST /v1/images/edits` 均 200

**Image-to-image: PASS / Keep original edit resolution: PASS**

## 8. 分辨率预设（§12 四项逐一 UI 实测）

| 预设 | UI「将使用」实测 | 结果 |
|---|---|---|
| 1024 × 1024（1K 1:1） | 1024x1024 | PASS |
| 1536 × 1024（1K 3:2） | 1536x1024 | PASS |
| 1024 × 1536（1K 2:3） | 1024x1536 | PASS |
| 2048 × 2048（2K 1:1） | 2048x2048 | PASS |

**Preset resolution: PASS**（4/4）

## 9. 自定义分辨率与非法值

- 补丁 P2：`SIZE_MULTIPLE=64`、`MIN_EDGE=512`、`MAX_EDGE=2048`、`MIN_PIXELS=262144`、`MAX_PIXELS=4194304`、宽高比 ≤3
- 尺寸面板提示文案已同步为新规则
- 实测：输入 `4000×100`（非法）→ 前端归一为 `1472×512`（64 倍数、512–2048 内、比例 2.875≤3）——非法值不进入 pipeline
- 后端二次防御：生成尺寸越界/非 16 倍数 → 400 `INVALID_SIZE`（实测 100×100、3000×2000、1025×1024 全部 400）

**Custom resolution: PASS**

## 10. Model selector

- preset 配置（VITE_DEFAULT_API_URL 构建期嵌入）→ 打开设置即见配置「Qwen-Image-2.1」，API URL=`http://SERVER_IP:8011/v1`，模型 ID=Qwen-Image-2.1，Images API，timeout=600
- `config/models.example.json` 按 §14 结构表达：`id / display_name / api_base / generation_endpoint / edit_endpoint / supports_generation / supports_edit / max_width / max_height`
- 未来 Model A/B/C = 注册表加条目 + 重新 build（upstream 多 Profiles 结构天然支持切换），无需重做 UI

**Model selector: PASS**

## 11. Queue 设计（§15/§16/§30）

新增 `serving/services/image/queue_manager.py`：

- `ImageQueue(max_concurrent=1, max_pending=8, timeout=480s)`，Condition + FIFO 授槽（release 将槽位直接转交队首等待者）
- 两个端点共享同一队列：generations ─┐
  edits ─┴→ IMAGE_QUEUE → gpu.lock（MANAGER.ensure_loaded 内 flock）→ Ollama/nvidia 双重复核 → 推理 → 释放槽位
- 超过 max_pending → **HTTP 429 `QUEUE_FULL`**（冒烟实测）
- 等待超时（480s < 上游客户端 600s 超时）→ 503 `QUEUE_TIMEOUT`
- GpuBusy（Zrald 持锁场景）→ 503 `GPU_BUSY`，槽位在 finally 释放，**flock 未被绕开**
- 进程内内存态，重启丢弃 pending（内部工具可接受，§26 无数据库）

## 12. Queue 测试（§29 两请求串行化）

两个并发 `POST /v1/images/generations`（1024×1024、steps=12）：

- 采样：`t+3s..t+15s queue = {running:1, pending:1, max_pending:8}`（连续5次采样全中）
- 结果：req1=200（gen 56.0s，load 6.0s），req2=200（gen 136.6s，含排队等待）
- 两请求均返回 `b64_json + b64`；推理严格先后串行，GPU VRAM 峰值 15195 MiB（含 Ollama embedding 14.4G 同驻），**无 OOM**
- 结束态：`running:0, pending:0`

**IMAGE_QUEUE_SERIALIZATION = PASS / Two-request serialization: PASS / Queue: PASS**

## 13. GPU lock 交互（§30）

- 顺序满足：request → queue slot → gpu.lock → 双重复核 → inference → release slot
- 冒烟实测：Ollama 大模型驻留时 → `503 GPU_BUSY {"code":"GPU_BUSY"}`（flock 路径原样生效）
- /unload 后 `gpu.lock = FREE`（flock 探针实测），文件从未 unlink（inode 稳定）

**GPU lock: PASS**

## 14. /status 扩展（§17）

```json
{"model_loaded": false, "idle_timeout_seconds": 600,
 "queue": {"running": 0, "pending": 0, "max_pending": 8}, ...}
```
旧字段全保留（OLD 兼容）；WebUI 徽标与 curl 均验证。

## 15. WebUI 队列状态（§18）

补丁 P5：`QueueStatusBadge` 每 4s 轮询 `{api_base}/status`，显示 `队列 {running}/{pending} · 模型已载入/未载入`。

- 空闲：`队列 0/0 · 模型未载入`（页面初开实测）
- 生成中：`队列 1/0 · 模型已载入`（编辑请求飞行中实测，running=1 ✓）
- 模型加载后：`队列 0/0 · 模型已载入` ✓
- 请求失败/离线时组件静默隐藏（不误导）

**（徽标随请求实时反映 running/pending —— 属于最少化队列 UI，未做大规模 fork）**

## 16. 临时存储（§19–§24）

- 新增 `temp_output.py`：`IMAGE_OUTPUT_DIR=/home/syy/ai-serving/tmp/image-output`
- 文生图/图生图输出只写该目录（旧 `logs/image/generated/` 不再写入）
- 上传原图：内存读取（`await file.read()`），不落盘、无永久保存
- 响应策略：**优先 b64_json**（WebUI 直接展示与下载）；`path` 仅为内部临时缓存
- WebUI 不依赖图片持久存在（服务端文件删除后浏览器仍正常渲染，见 §17 实测）

**Temporary output path: /home/syy/ai-serving/tmp/image-output/ / Server image persistence: TEMP ONLY**

## 17. 30min TTL 清理（§21/§31）

- `IMAGE_OUTPUT_RETENTION_SECONDS=1800`，`IMAGE_CLEANUP_INTERVAL_SECONDS=300`，启动即扫一次 + 周期扫描（lifespan 启动）
- **TTL 实测（临时 60s/30s 配置）**：
  - T=0：生成后文件存在（`gen_1790372566_0.png`，510487 字节，b64_json ✓）→ 存在性 PASS
  - T<60：文件存在 ✓
  - T>60+30：文件已被 cleaner 删除，目录空 → **自动消失 PASS**
  - **最终配置已恢复 1800/300**（进程 environ 实测打印确认，无 60s 残留）→ `IMAGE_TEMP_CLEANUP = PASS`

## 18. 清理安全性（§22）

`cleanup_once()` 约束：
- 仅删除 `TEMP_OUTPUT_ROOT` **直接子级的常规文件**（`is_file(follow_symlinks=False)`）
- **symlink 完全跳过、绝不 follow**
- `resolve()` 后父目录必须等于根目录，否则拒绝
- 不递归、不删目录/模型/日志/源码/配置

单测实证：根内过期文件被删；指向外部的过期 symlink 保留且外部目标文件完好（`victim.txt` 内容不变）。

**Cleanup safety: PASS（本地单测 + 远端行为一致）**

## 19. 浏览器历史（§25）

- **BROWSER_LOCAL_HISTORY = ENABLED**（upstream IndexedDB 本地历史；实测浏览器分区出现 `http_10.16.15.202_8020.indexeddb.leveldb` 且任务跨操作存活；关闭需大量改动上游，按任务书不阻塞）
- **SERVER_HISTORY = DISABLED**（无任何服务端历史/画廊端点；服务器图片仅 TTL 临时存在）

## 20. 下载（§32）

- Preview：Lightbox 打开并渲染结果图（1536×1024 详情面板含输入内容/参数/耗时）→ PASS
- 「下载图片」按钮点击执行、控制台零报错
- 客户端字节完整性实证：页面内图片为完整 PNG（base64 1,932,004 字符、魔数 `89504e470d0a1a0a` 正确、naturalWidth=1536）
- 服务端临时文件被 TTL 删除后，页面所有图片仍正常渲染/仍持有完整字节 → **客户端独立性 PASS**
- 验证限制：自动化后端（IAB）未开放 download/filechooser 事件路由（`ambiguous routed session`），落盘文件无法被自动化截获；同理图生图素材改用「生成→编辑输出」路径（任务书明确允许"上一轮生成图片"），上传按钮的 accept=image/* 结构存在、后端 `image/image[]` 字段已用 curl 实证

**Download: PASS（预览 + 客户端完整字节 + 服务端删除后不受影响；落盘事件自动化通道不可观测，如实记录）**

## 21. 回归（§34/§35）

| 项 | 结果 |
|---|---|
| Zrald :8010 health | PASS（backend_alive=false 为正常空闲态） |
| Image :8011 health/status | PASS（含 queue 字段） |
| WebUI :8020 | PASS（root 200） |
| Ollama :11434 tags | PASS（10 模型，未改动） |
| Open WebUI :3000 | PASS（200，未改动） |
| vLLM :8000 | 保持 CLOSED ✓ |
| Image generation | PASS（浏览器 + curl 多轮） |
| Image edit | PASS（keep-original + custom） |
| Queue | PASS |
| TTL cleanup | PASS |
| `/unload` | PASS：`unloaded:true`、`model_loaded=false`、gpu.lock FREE |
| IDLE 自动卸载 | PASS（临时 IDLE=60 实测：加载→60s 无活动→watcher 自动卸载、锁释放；**已恢复 600**） |
| GPU 最终水位 | 299 MiB（桌面），gpu.lock FREE，恢复本轮开始时正常水位 |
| Zrald/Ollama/OpenWebUI/vLLM | 均未修改 |

## 22. CORS（§9）

- 代码零真实 IP：`IMAGE_ALLOWED_ORIGINS` 环境变量读取（默认仅 localhost 开发源），白名单精确 origin，**无 `*`**
- 实测：预检 `OPTIONS` → `Access-Control-Allow-Origin: http://SERVER_IP:8020` ✓；恶意 origin 无 ACAO ✓
- 浏览器真实链路：WebUI(:8020) → API(:8011) 的 generations/edits/status 全部 200（CORS 全程生效）

## 23. 上游补丁清单（P1–P5，全部 build+test 全绿）

| # | 内容 | 文件 |
|---|---|---|
| P1 | negative_prompt / steps / seed 控件 + 请求体透传 | types.ts, inputParamsPanel.tsx, openaiCompatibleImageApi.ts, persistedState.ts |
| P2 | 512–2048、64 倍数、预设表重写、限制文案 | size.ts, size.test.ts, SizePickerModal.tsx |
| P3 | 单次输出上限 10→4（对齐后端 n≤4） | paramCompatibility.ts(+test) |
| P4 | mask 禁用 → toast `Mask editing unsupported by current model.` | store.ts(+test) |
| P5 | 队列徽标 | QueueStatusBadge.tsx（新增）, InputBar.tsx |

验证：`npm ci` ✓ / `npm run build` ✓ / `npm test` ✓（34 文件、576 用例全绿，与补丁前基线一致）。

## 24. Git

- 提交范围：`webui/image-platform/`（源码+补丁+脚本+示例配置，无 node_modules/dist/真实 IP）、`serving/services/image/`、`serving/configs/image/`（example）、`serving/scripts/image/`、`reports/`、`coordination/`、`.gitignore`
- SECRET_SCAN = 见最终回复
- commit：`feat: deploy internal image webui platform`
- push：main，HEAD == origin/main：见最终回复

## 25. 观察项与限制（如实记录）

1. **Ollama embedding 周期驻留**：LAN 客户端 CLIENT_IP_REDACTED 周期调用 `/api/embed` 使 `qwen3-embedding:8b` 长期占 ~14.4GB，Image 冷加载被 `_ollama_gpu_busy` 拦截为 503（按设计保护，不绕开）。本轮通过抓取空闲窗口完成全部需加载的测试；Gateway 方案仍为 NEXT_ACTION 既有待办。
2. **自动化通道限制**：IAB 后端 filechooser/download 事件路由异常（`ambiguous routed session`），浏览器上传按钮与落盘下载无法被自动化截获；平台功能本身未受影响（上传结构存在、下载预览与字节完整性已证、编辑素材改用生成图路径）。
3. **并发人工操作**：测试期间浏览器出现非本自动化发起的请求（"生成一只橘色小猫"编辑 200），说明真实用户同时在用平台，未产生冲突（队列正确串行）。
4. `/unload` 与在途推理曾并发（人工请求），管线对象引用捕获使其安全完成 200、无 CUDA 异常栈；unload 未加推理中拒绝逻辑（超出任务范围，行为与上一轮一致）。
5. 上游 `21:9` 比例经 gcd 化简后命中不到预设条目、走预算搜索（输出仍在 64 倍数与 512–2048 内）；四个任务指定预设全部直接命中。
