# QWEN-IMAGE MAX CAPABILITY & UI PROFILE REPORT

Task ID: QWEN-IMAGE-MAX-CAPABILITY-AND-UI-PROFILE-001
Date: 2026-09-26
Hardware: RTX A6000 (49,140 MiB), SERVER_IP:8011 (Image API), SERVER_IP:8020 (WebUI)
Model: /data/vllm/ImageModel/Qwen-Image-2.1 (QwenImage21Pipeline, diffusers 0.41.0.dev0)

---

## 1. Official capability baseline

核验源：远端模型卡 `/data/vllm/ImageModel/Qwen-Image-2.1/README.md` + 本机 diffusers
`pipeline_qwenimage21.py` 源码（只读核验，未联网）。

| 项 | 官方 | 本部署 |
|---|---|---|
| 推荐 steps | 40（README 示例3处，`num_inference_steps=40`） | `__call__` 默认 40 ✓ |
| 参考图 | "Support up to **10 reference images**"；`image: PipelineImageInput`，源码单张自动归一为 list（`image if isinstance(image,list) else [image]`），token 级拼接非像素拼接 | 原生 list 支持；产品策略 **MAX_REFERENCE_IMAGES = 5**（≤10，符合要求） |
| 2K aspect presets | README `:119-127`：1:1 (2048,2048)、4:3 (2400,1792)、3:4 (1792,2400)、3:2 (2528,1696)、2:3 (1696,2528)、16:9 (2752,1536)、9:16 (1536,2752) —— 与任务书7项逐一相同 | 7项全部实测（§3） |
| RGBA | 模型卡支持 prompt 引导透明图（无 background 参数） | pipeline 无 alpha 输出参数 → profile `supports_rgba=false`（透明背景控件隐藏） |
| mask / strength | README 提"separate masks"，但当前 `__call__` 签名**无** mask/strength 参数 | `supports_mask=false`、`supports_strength=false`；mask 请求仍 400 MASK_UNSUPPORTED |
| 尺寸 | 签名无 min/max；check_inputs 仅要求 `vae_scale_factor*2` 整除 | 服务端能力包络见 §7 |

`QwenImage21Pipeline.__call__` 关键签名（原样）：

```python
def __call__(self, prompt=None, image=None, negative_prompt=None, true_cfg_scale=1.0,
             height=None, width=None, num_inference_steps=40, ..., output_type="pil",
             output_resolution=1024, use_kv_cache=True)
# 无 mask、无 strength、无 background
```

## 2. Steps vs VRAM（复核）

条件：1024×1024、seed=42、无参考图、n=1。

| steps | inference (s) | image 峰值 (MiB) | GPU 总峰值 (MiB) |
|---|---|---|---|
| 4 | 45.277 | 17,316 | 32,121 |
| 24 | 60.484 | 17,282 | 32,087 |
| 40 | 75.410 | 17,282 | 32,087 |

**STEPS_VRAM_SCALING = MINIMAL**：三档 image 峰值极差 34 MiB（≈0.2%），耗时随步数近似线性（45→60→75s）。
steps 只是时间因子，不作显存预算因子。

## 3. Official 2K resolution matrix（TEXT_TO_IMAGE_2K_MATRIX）

条件：quality=high（effective_steps=40）、seed=42、n=1、统一英文 prompt。串行，每档完成后记录。

| Resolution | Steps | Peak VRAM (image / total, MiB) | Inference (s) | Result |
|---|---|---|---|---|
| 2048×2048 | 40 | 32,058 / 46,863 | 202.854 | PASS（200，输出尺寸精确） |
| 2400×1792 | 40 | 30,496 / 45,301 | 214.136 | PASS |
| 1792×2400 | 40 | 33,650 / 48,455 | 212.955 | PASS |
| 2528×1696 | 40 | 30,406 / 45,211 | 211.983 | PASS |
| 1696×2528 | 40 | 33,268 / 48,075 | 214.743 | PASS |
| 2752×1536 | 40 | 33,526 / 48,333 | 208.142 | PASS |
| 1536×2752 | 40 | 33,526 / 33,830 | 204.829 | PASS（该档 embed 未在场） |

- 全部7档 **PASS**，无 OOM；输出像素与请求逐一一致。
- total−image ≈ 14,805 MiB 的档位 = embed（qwen3-embedding:8b，14,496 MiB）同场；
  image 自身峰值与 embed 在不在场无关（1536×2752 无 embed 与 2752×1536 有 embed 峰值几乎相同）。
- 纵向（高>宽）档位峰值略高于横向（+3.2GB）。

## 4. Reference count VRAM matrix（1024×1024 @40）

条件：edits、size=1024x1024、quality=high、seed=42、真实5张输入素材
（1 张流程图 + 4 张学术风格图，`tmp/capability-inputs/` 专用测试目录）。embed 均同场。

| References | Resolution | Peak VRAM (image / total, MiB) | Inference (s) | Result |
|---|---|---|---|---|
| 1 | 1024×1024 | 20,578 / 35,385 | 78.463 | PASS |
| 2 | 1024×1024 | 21,712 / 36,519 | 87.045 | PASS |
| 3 | 1024×1024 | 24,284 / 39,089 | 93.995 | PASS |
| 4 | 1024×1024 | 28,614 / 43,419 | 96.721 | PASS |
| 5 | 1024×1024 | 31,414 / 46,219 | 102.233 | PASS |

多参考图为 pipeline 原生 list 输入（逐图 encode），每张参考图约 +2~4.4GB 峰值。

## 5. 5-reference 2K tests

| Config | Condition | Result | 关键数据 |
|---|---|---|---|
| 5 ref + 1024×1024 + 40 steps | embed 同场 | **PASS** | img 31,414 / tot 46,219，inference 102.233s |
| 5 ref + 2048×2048 + 40 steps | embed 同场（实测） | **FAIL / CUDA OOM** | 分配 4,833,935,360 B 失败（free 1,634,271,232 B），HTTP 500 EDIT_FAILED，wall 277s（管线末端 VAE decode），img 已达 33,530 |
| 5 ref + 2048×2048 + 40 steps | **空闲 GPU**（看门狗保护） | **PASS**（attempt 3） | status 200，img **41,372** / tot 41,676，inference 268.979s，输出 2048×2048 精确 |
| 5 ref + 2752×1536 + 40 steps | **空闲 GPU**（看门狗保护） | **PASS**（attempt 3） | status 200，img **45,396** / tot 45,700，inference 272.505s，输出 2752×1536 精确 |
| 5 ref + 1536×2752 + 40 steps | 空闲 GPU，4 次窗口重试 | **NOT ESTABLISHED** | attempt1-4 全部 WINDOW_LOST（embed 于 58/266/206/122s 闯入被看门狗中止），**全程无 OOM**；embed 同场不主动复测（按 §12 不重复 OOM，按对称性与 2048² 同风险） |

**停止条件执行**：首次 OOM 后立即杀 runner；在途更高压力档（2752×1536 embed 同场）以 SIGTERM→SIGKILL 中止；
服务日志 OOM 计数全程保持 75 行（全部来自首次失败），后续8次看门狗中止零 OOM。

- LAST_SAFE_CONFIGURATION = **5 refs @ 1024×1024 @ 40 steps（embed 同场）**；空闲条件下 = 5 refs @ 2752×1536 @ 40
- FIRST_UNSAFE_CONFIGURATION = **5 refs @ 2048×2048 @ 40 steps（embed 同场）**

## 6. Idle-window retry & coexistence (§14)

- 空闲窗口重试脚本（`/tmp/idle_ref5.py`）：等 `/api/ps` 空闲 → 发起5ref2K → 运行中每2s 监测
  compute-apps，embed 闯入即中止推理（SIGTERM→10s→SIGKILL）并重启服务换窗重试（每档≤4次），真实 OOM 永不重复。
- 共8次中止（2048²:188/118s；2752×1536:66/20s；1536×2752:58/266/206/122s）+2次完整 PASS；
  最长静默窗口完整跑完278.6s。
- **显式共存测试**（embed 经 `/api/embed` 触发常驻后再生成）：单图 2048×2048/40 → **PASS**，
  img 33,700 / tot **48,505**（free 635 MiB）、inference 197.487s、无 OOM —— 与 §3 embed 同场行互证。
- 结论：embed 同场吃掉14.5GB 是5ref2K decode OOM 的直接原因；单图2K 共存可行但总余量薄（0.6–2.3GB）；
  image 自身峰值不受 embed 在场影响（同配置 img 峰值一致）。

## 7. Absolute tested max / Production safe max

**ABSOLUTE_TESTED_MAX**（实测安全上限）：
- 编辑（决定性上限）：**5 refs + 2752×1536 + 40 steps @ 空闲 GPU** —— image 峰值 **45,396 MiB**、
  GPU 总峰值 45,700（free 3,440 MiB）
- 文生图：7档官方2K @40 全 PASS，峰值上限 33,650 MiB（1792×2400，embed 同场总峰值 48,455）
- 5ref2048² idle PASS：img 41,372；5ref1024² 任意条件 PASS：img 31,414

**PRODUCTION_SAFE_MAX**（生产建议，基于峰值留余量）：
- 文生图：**7档官方预设全部开放**——空闲 GPU 总峰值 ~34GB（余量 ~15GB ≥5GB ✓）
- 编辑：**≤5 refs 且输出 ≤1024×1024** 全条件安全（embed 同场峰值 tot 46.4GB，余量 ~2.8GB）
- 编辑 5ref × 2K 输出：**仅空闲 GPU**（tot 41.7–45.7GB，余量 3.4–7.4GB ≥3GB ✓）；
  embed 同场 OOM 实测 → 生产配合 embed `keep_alive=0` / Gateway 收口（本轮建议，未实施）
- **Safety margin**：最重工况（5ref2752×1536 idle）总余量 **3.4GB**（≥3GB 参考线）；
  t2i 全档 idle 余量 **≥15GB**；embed 同场的2K t2i 余量 0.6–3.9GB 属外部干扰上界
- 1536×2752 + 5ref：空闲窗口未取得 → 生产不预设该组合，取得数据前按8档预设单独控制

**安全包络（后端 capability.py 单一配置源，前端镜像+运行时覆盖）**：
`MAX_EDGE=2752`、`MAX_PIXELS=4,300,800`（2400×1792）、`MAX_ASPECT_RATIO=1.8`、`MIN_EDGE=512`、
`MULTIPLE_OF=16`、`MAX_REFERENCE_IMAGES=5`、quality fast/standard/high=4/24/40。

## 8. UI model profile

前端 `webui/image-platform/upstream/src/lib/modelProfile.ts`：
- `getProfileForModel()` 注册表机制：Qwen-Image-2.1 专属 Profile + 通用默认 Profile（其他模型零变化），
  未来 Model B/C 仅需加条目（§21）。
- Qwen Profile：`max_reference_images=5`、8档官方分辨率、quality 4/24/40（默认标准24、官方高质量标注）、
  自定义尺寸 512–2752/16倍数/≤1.8:1/≤4,300,800px、`supports_rgba/mask/strength=false`。
- 尺寸选择器「官方预设」页签8项 + 「自定义宽高」逐条中文报错；第6张图前端拒绝，文案
  `Qwen-Image-2.1 当前服务器配置最多支持5张参考图。`；主图/参考图N + x/5 计数。
- §22 同步：静态镜像（文件头注明与 capability.py 同步）+ `QueueStatusBadge` 轮询 `/status.capability`
  运行时覆盖（拉取失败用静态值）。
- 验证：服务器 `npm test` **35 文件 / 594 用例全绿**（基线34/576 + 新增18）；`npm run build` 通过；
  对外 dist 已由 `build_webui.sh` 重建。

## 9. Multi-reference E2E（浏览器，SERVER_IP:8020 真实浏览器）

| 项 | 结果 |
|---|---|
| 选择 Qwen-Image-2.1 后参数面板切换 Profile | `上传图片（已选 n / 5）`、`已选 5 / 5 张 · 第 1 张为主图`、`主图`/`参考图 2…5` 标签全量出现 ✓ |
| 官方2K分辨率出现 | 尺寸选择器「官方预设」页签 8 项（1024x1024 快速档 + 7 档 2K）+ 说明文案 ✓ |
| 质量档位 | `快速 · 4 步` / `标准 · 24 步` / `高质量 · 40 步（官方推荐）`；提示 `官方高质量 / 40 steps（快速 4 · 标准 24）`；选高质量 → `生效步数 = 40（按质量档）` ✓ |
| 自定义尺寸限制 | 宽 3000 → 逐条报错（512-2752 范围 / 宽高比 1.8:1 / 16 倍数）+ 确定禁用；限制文案与 capability 完全一致 ✓ |
| 5 图挂载与第6张拒绝 | 通过浏览器「编辑输出」挂满 5 张（计数/标签逐一核对）；满额时上传按钮 aria-label 即指定文案 `Qwen-Image-2.1 当前服务器配置最多支持5张参考图。`，任何加图尝试计数不越过 5/5；满额拒绝 toast 逻辑由 store 测试覆盖。**磁盘文件选择器上传不可自动化**：IAB `waitForEvent("filechooser")` 连续三轮报 `ambiguous routed session`（见 §11） |
| 5 图真实生成 | 浏览器提交 → 后端日志 `[edit] steps=40 explicit=None quality=high target=1024x1024 refs=5` → **POST 200**，输出 edit_1790429196_0.png（1,980,656 B），卡片正常完成、无新失败卡 ✓ |
| `multiple input images are not supported` | 该错误源自旧后端 MULTIPLE_IMAGES，本轮已移除；服务日志全程 0 次命中 ✓ |
| 4 图中间回归 | 浏览器 4-ref 提交 → `refs=4` → 200 ✓ |

## 10. Regression（§25 全量）

| 项 | 结果 |
|---|---|
| 单图文生图 | PASS（steps 矩阵 + 2K 矩阵 + 共存 + guard 复测，全部 200） |
| 单图编辑 | PASS（refs_1，200，输出 1024²） |
| 2 图编辑 | PASS（refs_2，200） |
| 5 图编辑 | PASS（refs_5 @1024² API；浏览器 refs=5 → 200） |
| Queue | PASS（回归复测：首请求 queue_wait=0.000、次 65.436，双 200 串行） |
| GPU lock | PASS（推理中 status 显示 lock held；unload 后 FREE；flock 逻辑未动） |
| unload guard | PASS（活体复测：推理中 /unload → **409 INFERENCE_BUSY** 精确 body，loaded=true/lock held；生成 200 完成后 /unload → 200 + FREE） |
| idle unload | PASS（IDLE=600 进程 env + /status 双确认，未改） |
| TTL | PASS（RETENTION=1800 / CLEANUP=300 未改；专用测试目录 capability-inputs 已删除，输出走 TTL 目录） |
| 8020 / 8011 | PASS（200 / status 含 capability） |
| 8010 不受影响 | PASS（/manager/status 200，backend_alive=false 空闲常态，未动） |
| 11434 / 3000 / 8000 | PASS（200 / 200 / CLOSED） |
| 旧字段兼容 | generation_seconds、b64/b64_json/path/width/height、旧 image/width/height edits 字段全保留 |
| 服务终态 | model unloaded、gpu.lock FREE、GPU 仅 embed 常驻水位 |

## 11. Remaining limitations / risks

1. **embed 周期驻留是 5ref+2K 编辑的绑定风险**（实测 OOM 根因，也是1536×2752 未定论的原因）：
   建议 embed 客户端 `keep_alive=0` 或统一 Gateway 收口（与 IMAGE-OLLAMA-GPU-BUSY-DIAG-001 建议一致）。
2. **IAB filechooser 路由不可用**：`waitForEvent("filechooser")` 三轮均报 `ambiguous routed session`，
   本机 @mimo/sky 不可用、无 Computer Use 通道 → "从磁盘上传5张"无法自动化实证；
   已用「编辑输出」等价路径走完 addInputImage 上限校验→multipart image[]→refs=5→200 全链。
   待 harness 修复后补测字面上传。
3. **1536×2752 + 5ref 空闲窗口未取得**（4 次被抢占，无 OOM）：该组合暂不进生产预设结论。
4. **n≥2 批量文生图显存显著更高**（n=4 实测 img 30,926 / tot 45,735）：与本轮 n=1 上限不同口径，
   未纳入 PRODUCTION 结论，建议后续单独评估 n 与显存关系。
5. 编辑请求中 UI 的 n 字段被后端忽略（edits 恒 1 输出）——浏览器 n=3 编辑实测 200 且 UI 正常，
   属既有行为，记录备查。
6. 2K t2i + embed 同场最高总峰值 48,505（free 635 MiB）：外部干扰上界，非 image 自身超限。

## 12. Git

- 提交范围：`serving/services/image/`、`webui/image-platform/upstream/src/`（不含 dist/config/scripts 的本地真实配置）、`reports/`、`coordination/`
- 禁止：模型、测试图片、tmp、logs、真实 IP、secret、node_modules、dist 本地真实配置
- secret scan PASS 后 commit：`feat: enable qwen image full capability profile` → push main
- 结果见最终回复。
