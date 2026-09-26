# Last Agent Handoff

Updated At: 2026-09-27  
Last Task ID: IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW（Git 结果见最终回复 / git log）

## Completed

- **GPU 等待队列（功能A）**：`model_manager.py` 重写 GPU 准入：
  - `estimate_gpu_budget_mib(w,h,refs,n)` 实测标定预算（锚点误差≤1.7GB）
  - `_gpu_admission`：free_for_us（总显存−其他进程）≥ budget + `IMAGE_GPU_SAFETY_MARGIN_MIB=3072`；
    **不再要求 Ollama 为空**（embed 驻留但预算够 → 直接放行）
  - `ensure_loaded_waiting`：admission→flock→二次 admission；失败进入 WAITING_FOR_GPU
    （每3s重试、**不持 gpu.lock**）；`IMAGE_GPU_WAIT_TIMEOUT_SECONDS=900` 超时 → 503
    `GPU_WAIT_TIMEOUT`（消息「等待 GPU 超时（Ns）」）
  - `GET /status.queue` 新增 `waiting_for_gpu`；`[gpu-wait]` 日志记录进入/放行/超时
  - env 三件套已入 `service.env.example` 与服务器 local env（900/3/3072）
- **E2E 四项全 PASS**：
  - A Zrald 持锁：等待原因=`gpu lease held by zrald-manager`、image 锁 null、Zrald idle 释放后
    `admitted after 600.9s` → 同请求200（无需重提）
  - B embed 驻留 t2i1024：**直接200**（零 gpu-wait 日志，旧版必503）
  - C embed 驻留 5ref2K：2.1s 进入等待（budget42676>free34384）、等待期 image VRAM 恒564MiB、
    资源变化后同请求自动200
  - 超时：临时30s → 503 `GPU_WAIT_TIMEOUT` 32.8s，日志 TIMEOUT after30.6s；已恢复900
- **Steps 24-200 矩阵（5refs/1024²/seed42 串行）**：八档全200；img 峰值31,386–31,528（差0.45%）
  → `STEPS_VRAM_SCALING = MINIMAL`；推理79.8→301.3s；8张图逐张人工查看（10维度，报告§9）
- **档位结论**：`QUALITY_PLATEAU_STEP=120`、`RECOMMENDED_HIGH_STEP=120`（Ultra）、
  `MAX_TESTED_STEP=200`；构图随步数**非单调**（24表格 / 40·60·100·160稀疏列 / 80·120·200红提纲）已如实记录
- **Ultra 2K 复核**：5ref+2048²+120 首次因 embed 中途载入 OOM（=外部竞态实证）；
  测试环境防御重跑 **200**（715.7s，img45,988，成图为完整分子式图）
- **Profile/UI（功能B + §22-26）**：
  - 后端 `capability.py`：`QUALITY_STEPS["max"]=120`、`/status.capability.steps={official:40,
    recommended_high:120, max_custom:200}`
  - 前端 `modelProfile.ts` `RECOMMENDED_HIGH_STEPS=120`（仅 Qwen；通用 Profile 保持40不开 Ultra——
    修复过常量泄漏导致 generic 也开 Ultra 的回归，测试596全绿）
  - 质量下拉新增 `超高质量 · 120 步`（>40 才显示）；步数 = number+slider 1–200 钳制；
    `生效步数=N`、`步数（自定义）`、>40 高计算成本提示、>100 实验性、`预计耗时 ~Ns（近似）`
  - 等待徽标：`队列 1/0 · 等待GPU中`（真实等待窗口抓拍）
- **浏览器 E2E**：挂5图 → 自定义80 → 生效80 → 后端 `[edit] steps=80 explicit=80 refs=5` → **200**
- **回归全 PASS**：映射5/5（4/24/40/显式覆盖/默认）、单图编辑200、queue（0/65.4s）、
  unload 活体409→200、idle600、TTL1800/300、steps201→400、8020/8011/8010/11434/3000、8000 CLOSED
- 报告：`reports/IMAGE_GPU_WAIT_QUEUE_AND_MAX_STEPS.md`

## Status Flags

| Flag | Value |
|---|---|
| GPU_WAIT_QUEUE | PASS（A/B/C + timeout 四项） |
| waiting_for_gpu 字段 | queue.waiting_for_gpu 上线，UI 徽标实时显示 |
| STEPS_VRAM_SCALING | MINIMAL（24→200 img 差0.45%） |
| QUALITY_PLATEAU / ULTRA | 120 / 120（官方40 不变，max 测试200） |
| OLLAMA_EXTERNAL_RACE | STILL_PRESENT（首次2K复核 OOM 实证；生产路径不碰 Ollama） |
| CANCEL_WAITING | 未实现（需 job id，按§7 记录） |
| OOM 事件 | 本轮1次（外部竞态，2K@120首次）；防御重跑后零新增；非人为制造 |
| GIT | 见最终回复（`feat: add gpu wait queue and extended image quality steps` → push） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动，spawn_count=3 为测试触发，idle 正常） |
| 8011 Image | RUNNING（**单 uvicorn 实例**，timeout900，unloaded，锁 FREE，idle600） |
| 8020 WebUI | RUNNING（dist=wait-queue+Ultra 版） |
| 11434 Ollama | RUNNING（未改，embed 周期驻留仍在） |
| 3000 OWUI | RUNNING（未动） |
| 8000 vLLM | CLOSED |
| GPU | ~15.2GB（embed 水位），gpu.lock FREE |
| env | IDLE=600 / TTL=1800/300 / QUEUE=1/8/480 / **GPU_WAIT=900s, poll=3s, margin=3072MiB** |

## 环境要点（下轮必读）

- **测试期临时脚本必须收尾**：本轮 defender/unblocker 忘关导致请求被提前放行——用完立即杀；
  杀脚本进程同样注意 pgrep 自匹配（括号技巧 + 命令行不得含明文模式）。
- **SIGTERM 在 CUDA 推理中可能延迟生效**：杀服务后必须 `pgrep` 确认进程数=1，必要时 SIGKILL；
  出现双 uvicorn 时先等在途任务自然结束再收敛单实例。
- **embed 竞态**：admission 只保护起跑前；高预算请求（5ref×2K）在 embed 活跃期可能中途 OOM——
  测试高预算组合时用"运行中即时安全释放"防御（仅测试手段，生产代码不碰 Ollama）。
- 其余沿用前轮：pkill 自匹配、IAB filechooser 不可用、本机 rollup 坏、curl --noproxy、
  服务器 Node 于 `env/node-v22.23.3-linux-x64/bin`、真实 IP 永不入 Git。

## Exact Next Action

WAIT FOR COMMANDER REVIEW

## Do Not

- 未授权不重启/升级 Ollama、不动 vLLM YAML、不动 Zrald/llama.cpp/Open WebUI/CUDA/Clash/网络
- 不在 embed 活跃期跑 5ref×2K 高预算组合（除非有防御/空闲窗）
- 测试图片/tmp/logs/模型/node_modules/dist 本地配置/真实 IP 不入 Git；禁 git add -A
