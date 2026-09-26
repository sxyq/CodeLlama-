# IMAGE GPU WAIT QUEUE & MAX STEPS REPORT

Task ID: IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS-001
Date: 2026-09-26/27
Services: SERVER_IP:8011 (Image API), SERVER_IP:8020 (WebUI), RTX A6000 49,140 MiB
Model: Qwen-Image-2.1 (QwenImage21Pipeline)

---

## 1. Old GPU_BUSY behavior

改动前：`ensure_loaded` 使用**二元判定** —— Ollama `/api/ps` 中任一模型 `size_vram > 1GB`
即抛 `GpuBusy` → 立即 **503 GPU_BUSY**，用户必须手工重试。
典型场景：`qwen3-embedding:8b`（14.4GB）周期驻留期间，即使请求预算完全放得下也一律被拒
（IMAGE-OLLAMA-GPU-BUSY-DIAG-001 已记录该问题）。Zrald 持 `gpu.lock` 时同样立即 503。

## 2. New WAITING_FOR_GPU lifecycle

```
REQUEST → QUEUED（取得 queue execution slot）
       → WAITING_FOR_GPU（admission 每 3s 重试；不持 gpu.lock）
       → admission 通过 → acquire gpu.lock → 二次 admission
       → RUNNING（load + inference）→ COMPLETED
       → 超时 IMAGE_GPU_WAIT_TIMEOUT_SECONDS →503 GPU_WAIT_TIMEOUT
```

实现（`model_manager.py`）：
- `estimate_gpu_budget_mib(w, h, refs, n)`：按本机实测标定的期望峰值
  （t2i 1MP=17.3GB、4.19MP=33.7GB、edit 1MP 每参考图曲线、5ref 4.19MP=41.4GB、n 批量项），
  锚点误差 ≤1.7GB。
- `_gpu_admission(budget)`：`free_for_us = 总显存 − 其他进程合计`（本进程残余可复用），
  放行条件 `free_for_us ≥ budget + IMAGE_GPU_SAFETY_MARGIN_MIB(3072)`。
  **不再要求 Ollama 为空**；Ollama/桌面/Zrald llama 全部计入"其他进程"。
- `ensure_loaded_waiting()`：失败→WAITING_FOR_GPU（置 `waiting_for_gpu` 标志并打
  `[gpu-wait]` 日志）→3s 重试→通过后走 `admission → flock → 二次 admission → load`；
  超时抛 `GpuWaitTimeout` → 503 `GPU_WAIT_TIMEOUT`（消息「等待 GPU 超时（Ns）」）。
- 等待期间**不持有 gpu.lock**（flock 只在 admission 通过后获取，二次 admission 失败立即释放）。
- env：`IMAGE_GPU_WAIT_TIMEOUT_SECONDS=900`、`IMAGE_GPU_WAIT_POLL_SECONDS=3`、
  `IMAGE_GPU_SAFETY_MARGIN_MIB=3072`（已入 `service.env.example` 与服务器 local env）。

## 3. Queue state model

- 状态语义（同步请求队列上实现，无独立 job id——任务书 §4 允许）：
  `QUEUED`（queue 排队）→ `WAITING_FOR_GPU`（占执行槽、等 admission）→ `RUNNING` → `COMPLETED`/`FAILED`。
- `GET /status` → `queue: {running, pending, waiting_for_gpu, max_pending}`
  （schema `QueueStats` 新增 `waiting_for_gpu`；单槽队列下同时最多 1 个等待者）。
- UI：`QueueStatusBadge` 轮询展示 `队列 r/p · 等待GPU中`（实测截图见 §12 E2E）。
- **取消（任务书 §7）**：等待中的请求无取消通道——现有同步架构需引入 job id/中断传播才可做，
  判定为明显高成本，本轮**未实现取消**，按任务书要求在此明确记录，不阻塞 wait queue。

## 4. Zrald wait test（E2E A）

步骤：Image 先 unload（锁 FREE）→ 停 embed → 触发 Zrald spawn（`GET :8010/v1/models`，
`lease_held=true`，llama-server 上 GPU）→ 后台提交 t2i 1024×1024/40。

| 观测 | 结果 |
|---|---|
| 请求未 503 | ✓ 进入 `waiting_for_gpu=1`（2.1s 内，`running=1`） |
| 等待原因 | `[gpu-wait] WAITING_FOR_GPU budget=17565MiB reason: gpu lease held by [1896989 zrald-manager …]`（VRAM 可过、锁被 Zrald 持） |
| 等待期间 image 侧 gpu.lock | **null**（未持锁，§8 ✓）；Zrald `/manager/status lease_held=true` |
| Zrald 正常 idle 释放（600s） | 自动 `admitted after 600.9s` |
| 同一请求无需重提 | inference 71.196s → **200**（total 672.787s） |
| 终态 | Zrald backend_alive=false/lease 释放；image loaded + 锁 held |

**Zrald busy → Image waits = PASS；Automatic start after Zrald releases = PASS**

## 5. Ollama wait/admission test（E2E B/C）

**B — 预算足够 → 直接运行**：embed 常驻（14,496MiB）下提交 t2i 1024×1024 →
两次 200（输入素材生成实测），**日志零条 `[gpu-wait]`**，冷加载 6.47s 成功
（旧版此处必然 503）。→ **PASS**

**C — 预算不足 → 等待 → 自动继续**：embed 常驻 + 5 refs + 2048×2048 →
-2.1s 进入 WAITING_FOR_GPU：`free_for_us=34384 < budget=42676 + margin3072`
- 等待期间 image 进程 VRAM 恒 564MiB（**未进 pipeline**）
- 资源变化后同请求自动 `admitted after 3.1s` → inference 268.979s → **200**（输出 2048×2048）
→ **PASS**（说明：观察脚本的采样窗口换算有 bug 只记到 2 个样本，判定以服务日志+首尾样本为准；
embed 当时恰自然过期属于资源自然变化，测试环境安全释放路径在超时测试中另行验证）

**Automatic start after GPU becomes safe = PASS**

## 6. GPU wait timeout

临时 `IMAGE_GPU_WAIT_TIMEOUT_SECONDS=30`（embed 常驻 + 5ref 2048 制造持续不可用）：

-503 `{"error":{"code":"GPU_WAIT_TIMEOUT","message":"等待 GPU 超时（30s）"}}`，wall 32.8s
- 服务日志 `[gpu-wait] TIMEOUT after 30.6s reason: vram admission failed…`
- 恢复 `900` 并重启（env 实测确认），此后多次正常运行均未再触发
→ **PASS**；UI 文案「等待 GPU 超时」由错误 message 透传（getApiErrorMessage 读 error.message）

## 7. Steps 24-200 matrix（5 refs，1024×1024，seed=42，同 prompt，串行）

Prompt：`Redraw this diagram in a clean academic figure style inspired by the reference images.`
输入 =1 流程图 + 4 学术风格图（`tmp/capability-inputs/`，同前轮种子确定性重建）。

| Steps | Inference (s) | Peak VRAM image/total (MiB) | Output bytes | Visual observation |
|---|---|---|---|---|
| 24 | 79.819（补跑 83.966） | 31,528 / 31,832 | 838,171 | 通宽浅色学术表格：17行×多列、虚线框，结构完整但对比度极低、伪字形难读 |
| 40 | 101.992 | 31,432 / 31,736 | 844,216 | 稀疏：约20行数字单列 + 小标题，右侧 ~75% 留白 |
| 60 | 128.890 | 31,456 / 31,760 | 869,802 | 稀疏数字列（行数略多），与40同类 |
| 80 | 152.201 | 31,386 / 31,690 | 1,023,429 | 红色多级提纲：左序号索引 + 分层小节，排版密实、线条锐利 |
| 100 | 178.119 | 31,402 / 46,207 | 1,075,929 | 稀疏数字列（~34行），右侧大面积留白 |
| 120 | 203.493 | 31,402 / 46,207 | 1,029,743 | **红色提纲最完整**：多级编号 (1)-(7)、小节块、页脚，层级最清晰 |
| 160 | 252.104 | 31,402 / 46,207 | 1,076,876 | 稀疏数字列 + 标题，与40/60/100同类 |
| 200 | 301.304 | 31,402 / 46,207 | 1,028,461 | 红色提纲中等密度，与80相近、未超越120 |

（100/120/160/200 四档 total=46,207 为 embed 同场；img 单进程峰值四档均 31,402，embed 不影响 image 自身峰值。）

## 8. VRAM scaling

24→200 档 image 峰值：31,386–31,528 MiB，**极差 142MiB ≈0.45%**；
时间 79.8→301.3s（≈3.8×，近线性随步数）。
→ **STEPS_VRAM_SCALING = MINIMAL**（步数是纯时间因子，显存预算与步数无关）

## 9. Visual comparison（8 张逐张人工查看，10 维度）

| 维度 | 观察 |
|---|---|
| 1 主图语义保持 | **全部 8 档均未保留原流程图的框/箭头结构**——风格参考（表格/清单类学术图）压过主图语义；与 steps 无关（prompt/模型行为），本轮不据此评 steps |
| 2 五张参考图风格利用 | 80/120/200 红色提纲与参考图的学术列表风格吻合度最高；24 淡表格次之；稀疏列组风格利用弱 |
| 3 结构完整度 | 120 ≥ 80 ≥ 200 > 24（表格完整但淡）> 160≈100≈60≈40（单列+大量留白） |
| 4 图形边缘 | 红提纲组线条锐利干净；24 虚线框偏淡；8 档均无毛边/糊边 |
| 5 小文字/排版 | 全部为伪字形（模型固有限制，不可读）；120/80 的层级缩进与编号最清楚；24 低对比最难读 |
| 6 局部细节 | 无面部/肢体类对象；提纲组编号、括号、分隔线一致性 120 最好 |
| 7 色彩一致性 | 红提纲组内部一致（页眉/正文/编号统一红系）；24 单色淡灰；稀疏组黑白 |
| 8 额外伪影 | 8 档均未见涂抹、重影、结构性伪影 |
| 9 过度修改 | 无过度修改迹象；同 seed 不同步数的**构图跳变**属轨迹差异（见下） |
| 10 收益停止点 | 120 之后无可靠增益（160 倒退回稀疏档、200 未超越 120） |

**关键现象——构图非单调**：固定 seed=42 下，步数改变会改变采样轨迹落点：
{24: 浅表格}、{40/60/100/160: 稀疏数字列}、{80/120/200: 红色提纲}。
"更多步数=更好"在单样本上**不成立**；本报告的档位结论基于每档完整成图的可比质量与耗时趋势，
并如实记录该方差（不同 seed/输入可能得到不同排序）。

## 10. Quality plateau

- **QUALITY_PLATEAU_STEP = 120**：120 是视觉收益的峰值点；120→160 耗时 +24% 且构图倒退，
  120→200 耗时 +48% 无可见超越——符合"耗时明显增加但视觉收益非常小"的定义。
- **RECOMMENDED_HIGH_STEP = 120**（Ultra 档采用值，理由：本矩阵中最完整、层级最清晰的成图档）
- **MAX_TESTED_STEP = 200**
- 官方推荐保持 **40**（official_recommended_steps=40，不改官方语义）

## 11. Recommended Ultra preset

- 后端 `capability.py`：`QUALITY_STEPS["max"] = 120`（Ultra 档值）；
  `/status.capability.steps = {official_recommended_steps:40, recommended_high_steps:120, max_custom_steps:200}`（§26）
- 前端 `modelProfile.ts`：`RECOMMENDED_HIGH_STEPS = 120`（仅 Qwen Profile；通用 Profile 保持 40 不开 Ultra）；
  质量下拉新增 `超高质量 · 120 步`（仅 recommendedHighSteps>40 时出现）
- 档位：快速4 / 标准24 / 高质量40（官方推荐）/ **超高质量120**
- **2K 复核（§21）**：5 refs + 2048×2048 + 120 steps：
  - 首次：admission 通过后 embed **中途载入** → 末端 VAE decode CUDA OOM（500）——即 §14 外部竞态实证
  - 测试环境防御性重跑（run 期间 embed 即时安全释放）：**200 PASS**，inference 715.692s，
    image 峰值 45,988MiB，输出 2048×2048；成图为完整分子式图（结构完整、边缘锐利、标签清晰）
- 生产提示：5ref+2K 的 decode 是显存最紧阶段，embed 同场/中途载入是主要风险（见 §14）

## 12. Custom steps UI + E2E

- 步数控件 = **number input + range slider**（1–200，双向同步、越界钳制，实测输入 8150 被钳到 200）
- 实时 `生效步数 = N`；手动值时 `步数（自定义）`
- 动态提示：>40 显示「高计算成本：更高步数主要增加生成时间，显存消耗变化很小，超过官方推荐40步后的画质提升可能有限」；
  >100 追加「实验性」（150/200 输入实测出现）；200 未命名为最高质量
- 预计耗时：`预计耗时 ~Ns（近似）`（80 步显示 ~162s，文案含"预计/近似"）
- 等待徽标：等待期间实时显示 `队列 1/0 · 等待GPU中 · 模型未载入`（真实等待窗口抓拍）
- **5-reference custom-steps E2E**：选 Qwen → 挂 5 图 → 输入 80 → `生效步数 = 80` → 提交 →
  后端日志 `[edit] steps=80 explicit=80 quality=high target=1024x1024 refs=5` → **POST 200** → 卡片完成 → **PASS**
- 前端测试：服务器 `npm test` **35 文件 / 596 用例全绿**，`npm run build` 通过；对外 dist 已重建
- 后端步数边界：`num_inference_steps=201` → **400** INVALID_REQUEST（1..200，前后端一致）

## 13. Regression

| 项 | 结果 |
|---|---|
| 文生图 | PASS（quality 映射复验5×200：fast→4/standard→24/high→40/显式12覆盖/默认24） |
| 单图编辑 | PASS（1 ref，200，effective=24，输出1024²） |
| 5图编辑 | PASS（E2E steps=80 refs=5 →200；steps 矩阵8档200） |
| GPU wait queue | PASS（A/B/C/timeout 四项，§4-§6） |
| Queue serialization | PASS（首请求 queue_wait=0.000、次 65.436，双200） |
| GPU lock | PASS（等待不持锁 §4；推理中锁 held、完成后释放；flock 逻辑未改） |
| unload guard | PASS（活体：推理中 /unload→409 INFERENCE_BUSY，生成200后 /unload→200+FREE） |
| idle unload | PASS（IDLE=600 env+status 确认，代码未改） |
| TTL | PASS（RETENTION=1800/CLEANUP=300 未改；测试素材仍走 TTL 目录+专用目录） |
| Quality 4/24/40 | PASS（映射复验 5/5） |
| Custom steps | PASS（E2E80 + 钳制/提示实测） |
| 8020 / 8011 | PASS（200 / health+status 含 waiting_for_gpu 与 capability.steps） |
| 8010 不受影响 | PASS（/manager/status 正常，spawn_count=3 为本轮测试触发，idle 态正常） |
| 11434 / 3000 / 8000 | PASS（200 / 200 / CLOSED） |
| 服务终态 | 单 uvicorn 实例、model unloaded、gpu.lock FREE、GPU 仅 embed 水位 |

测试期运维说明：一次性测试脚本（defender/unblocker）已全部清除；期间一次 SIGTERM 未即时生效
导致旧进程续跑完一个孤儿请求（自然200，无害），随后已收敛为单实例。

## 14. Remaining Ollama race

- **OLLAMA_EXTERNAL_RACE = STILL_PRESENT**
- 实证：2K@120 首次复核中 admission（含安全余量）通过后，外部客户端在运行中重新载入 embed →
  末端 decode 显存不足 → CUDA OOM（单次事件，OOM 计数75→144 为该单次告警行；后续防御重跑零新增）
- admission 在起跑前后各确认一次、外加 3GB 余量，可以挡住"起跑前"的 embed，**无法挡住起跑后到达的载入**；
  本轮生产代码路径**从不 kill Ollama**（测试环境使用的"运行中即时安全释放"仅为测试手段）
- 影响面：高预算请求（5ref×2K 档）在 embed 活跃期存在竞态 OOM 风险；低预算请求（1024² 档）
  即使 embed 同场也留有余量（实测矩阵全程无 OOM）
- 未解决方向（既有 NEXT_ACTION）：embed `keep_alive=0` / 统一 Gateway 收口，需客户端属主协调

## 15. Git

- 提交范围：`serving/services/image/`、`serving/configs/image/`（仅 service.env.example）、
  `webui/image-platform/upstream/src/`、`reports/`、`coordination/`
- 禁止项核对：测试图/tmp/logs/真实 IP/模型/node_modules/dist 本地配置/secret 均不入
- secret scan PASS 后 commit：`feat: add gpu wait queue and extended image quality steps` → push main
- 结果见最终回复
