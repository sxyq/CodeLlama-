# Last Agent Handoff

Updated At: 2026-09-26  
Last Task ID: QWEN-IMAGE-MAX-CAPABILITY-AND-UI-PROFILE-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW（Git 结果见最终回复 / git log）

## Completed

- **官方基线核验**（模型卡+pipeline 源码只读）：40 steps 官方推荐、最多10参考图（产品策略封顶 **5**）、
  7 档 2K 预设逐字一致、无 mask/strength/background 参数、RGBA 靠 prompt（profile=false）
- **后端能力改造**：`serving/services/image/capability.py` 单一配置源
  （512-2752 边、≤4,300,800px、宽高比≤1.8、16倍数、5图、quality 4/24/40、8档预设、features）；
  edits 支持 **1-5 张原生 list**（0→400、>5→400 TOO_MANY_REFERENCE_IMAGES，保序，禁止拼图）；
  `/status` 新增 `capability`；quality 表迁入 capability（_resolve_steps 复用）
- **能力实测**（全部串行 + 每档记录 image/total 峰值/耗时/输出尺寸）：
  - STEPS_VRAM_SCALING=MINIMAL：4/24/40 → img 17,316/17,282/17,282
  - 官方 2K 文生图 **7/7 PASS**（img 30,406-33,650；embed 同场总峰值最高 48,455）
  - 参考图 1-5 @1024² **全 PASS**（img 20,578→31,414）
  - 5ref+2048² embed 同场 **CUDA OOM**（decode 需+4.8GB 仅剩1.6GB）→ 触发停止规则，
    杀 runner+中止在途高危档，OOM 计数止于75；空闲窗口看门狗重试 **PASS**（img 41,372）
  - 5ref+2752×1536 空闲 **PASS**（img 45,396，绝对上限）；1536×2752 四次窗口被 embed 抢占
    NOT ESTABLISHED（零 OOM）
  - 显式共存：embed 触发常驻 + t2i2048² → PASS（total 48,505，free 635MiB）
  - 真实场景（1 流程图+4 学术参考图）：24 步与 40 步均 PASS
- **前端 Model Profile**（子 Agent 实现，主线验收）：`src/lib/modelProfile.ts` 注册表机制，
  Qwen 专属 + 通用默认零影响；官方8档预设页签、自定义尺寸逐条中文校验、5图上限
  `x/5`+主图/参考图N 标签+指定拒绝文案、质量 `快速4/标准24/高质量40(官方推荐)`、
  运行时 `/status.capability` 覆盖静态镜像；远端 npm test **35文件/594用例全绿**、build 通过
- **浏览器 E2E**：官方预设8档、尺寸3000逐条报错+禁用、质量40联动、5/5 标签计数、
  满额拒绝文案（按钮 aria + 上限校验）、**refs=5 → POST 200**、旧 `multiple input images` 全程0次；
  磁盘 filechooser 因 IAB `ambiguous routed session` 不可自动化（三轮验证，记录为 harness 限制）
- **回归全 PASS**：queue（0/65.4s 拆分）、unload guard 活体409→200、TTL1800/300、IDLE600、
  8010/8011/8020/11434/3000 正常、8000 CLOSED、旧字段兼容
- 报告：`reports/QWEN_IMAGE_MAX_CAPABILITY.md`

## Status Flags

| Flag | Value |
|---|---|
| MAX_REFERENCE_IMAGES | 5（前端+后端一致，capability 单源） |
| OFFICIAL_RESOLUTIONS | 8 档全 PASS 开放（1024² 快速 + 7 档 2K） |
| CUSTOM_SIZE_LIMIT | 512-2752 / ≤4,300,800px / ≤1.8:1 / 16倍数 |
| ABSOLUTE_TESTED_MAX | 5ref+2752×1536+40（idle）img 45,396 |
| PRODUCTION_SAFE | t2i 7档；edit≤5ref 输出≤1024² 全条件；5ref×2K 仅 idle GPU |
| OOM_COUNT | 75（仅首次失败产生，此后零复犯） |
| BROWSER_5REF_E2E | PASS（编辑输出等价路径；filechooser 不可用见报告§11） |
| GIT | 见最终回复（`feat: enable qwen image full capability profile` → push） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动） |
| 8011 Image | RUNNING（新 capability，model unloaded，锁 FREE，idle600） |
| 8020 WebUI | RUNNING（dist=Model Profile 版） |
| 11434 Ollama | RUNNING（未改；embed 周期驻留仍在） |
| 3000 OWUI | RUNNING（未动） |
| 8000 vLLM | CLOSED |
| GPU | ~15.2GB（embed 常驻水位），gpu.lock FREE |
| 测试素材 | `tmp/capability-inputs/` 已删除；输出走 TTL 目录（1800/300 未改） |

## 环境要点（下轮必读）

- **embed 静默窗口是所有冷加载/空闲压测的前置**：客户端每~2min 续约、静默窗2-3min居多，
  偶发>5min 窗口（本轮2次完整跑完280s）。空闲压测用 `/tmp/idle_ref5.py` 的看门狗模式：
  等窗→跑→embed闯入即中止（SIGTERM→10s→SIGKILL）→重启→换窗，零重复OOM。
- **pkill/pgrep 自匹配**：同条命令行含目标串普通文本（如脚本路径）时括号技巧也失效——
  杀进程、创建脚本、pgrep 必须分三次 SSH；用 PID 直杀最稳。
- **矩阵脚本**：`/tmp/matrix_runner.py <spec.json> <out.jsonl>`（t2i/edit、GPU_BUSY 重试、
  逐档采样 image/total 峰值、OOM 日志标记）；ollama 标志函数必须带 `--format=csv,noheader,nounits`。
- **IAB filechooser**：`waitForEvent("filechooser")` 必报 `ambiguous routed session`；
  浏览器加图用「编辑输出」（IndexedDB 新任务卡 dataUrl 可解析，旧格式卡 dataUrl 为空）；
  number input 清值用 Backspace（fill 无效）。
- 本机 Mac 代理拦内网：curl 用 `--noproxy '*'`；本地 node_modules rollup 签名损坏，
  npm test/build 一律在服务器跑（Node 于 `env/node-v22.23.3-linux-x64/bin`）。
- `service.local.env` / `config/*.json` / `dist/` 含真实 IP，永不入 Git。

## Exact Next Action

WAIT FOR COMMANDER REVIEW

## Do Not

- 未授权不重启/升级 Ollama、不动 vLLM YAML、不动 Zrald/llama.cpp/Open WebUI/CUDA/Clash/网络
- 不在 embed 驻留时做5ref+2K 压测（会复现 OOM）；停止规则：一次 OOM 即停更高压力档
- 生成图片/tmp/logs/模型/node_modules/dist 本地配置/真实 IP 不入 Git；禁 git add -A
