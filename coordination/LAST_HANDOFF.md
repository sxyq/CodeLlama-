# Last Agent Handoff

Updated At: 2026-09-26  
Last Task ID: IMAGE-WEBUI-QUALITY-SAFETY-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW（Git 结果见最终回复 / git log）

## Completed

- **Quality 真实映射上线**（双端点统一，单一 helper `_resolve_steps`）：
  fast/low=4，standard/medium/auto=24，high/xhigh/max=40；优先级 = 显式 num_inference_steps > quality > 24 默认；
  `schemas.GenerationRequest` 新增 `quality` 字段（改动前 pydantic 忽略该字段，UI 档位完全失效，实际一直是管线默认 40 步）
- **WebUI**：质量三档中文（快速/标准/高质量→4/24/40），默认 quality=medium（标准 24）；
  步数框显示「生效步数 = N（按质量档）」，手填时标注「步数（自定义）」——消除 Quality=High Steps=4 类矛盾显示；
  服务器 `npm test` 34 文件 576 用例全绿，dist 已重建
- **Inference guard**：`ModelManager._inference_lock` 全程持有（ensure_loaded+pipeline+结果编码）；
  推理中 `POST /unload` → **409 INFERENCE_BUSY**（不置空管线、不 empty_cache、不释放 gpu.lock）；
  idle watcher 同一路径，抢不到锁跳过本轮；queue 与 guard 职责分离不变
- **计时拆分**：响应新增 queue_wait_seconds / load_seconds / inference_seconds / total_seconds；
  `generation_seconds` 保留且 = inference_seconds（旧客户端兼容）；每次请求日志 `[gen]/[edit] steps=...`
- **实测全 PASS**：
  - 映射 5/5（fast4/standard24/high40/显式12压high/默认24）
  - A/B/C 4·24·40 步真实生成（seed=42，1024²，同 prompt `生成一只橙色小猫`，计时+峰值 VRAM+文件已记录）
  - 推理中 unload：409 + 锁 held + 生成 200 无 CUDA 错误 + 完成后 unload 200 FREE（UNLOAD_DURING_INFERENCE=SAFE）
  - Zrald lease：推理中两 probe 均 503 GPU_BUSY，message=lease held by [image-service]，unload 未提前释放
  - Queue：串行 PASS，首请求 queue_wait=0.000、次请求 59.698
  - Edit：quality=high→40，显式 12→12；输出 1024²
  - 浏览器 E2E：高质量→生效步数 40→日志 `steps=40 quality=high`→出图；快速→4
  - Idle：IDLE=20 临时实测（推理中 age>20 仍 loaded，结束后 36.2s 卸载），已恢复 600
  - TTL 1800/300 未改动（env+environ 双确认）；端口 8010/8011/8020/11434/3000 正常、8000 CLOSED
- 报告：`reports/IMAGE_WEBUI_QUALITY_SAFETY.md`

## Status Flags

| Flag | Value |
|---|---|
| QUALITY_MAPPING | fast4 / medium24 / high40，显式优先，generations+edits 统一 |
| EXPLICIT_STEPS_OVERRIDE | PASS（quality=high + steps=12 → 12） |
| UNLOAD_DURING_INFERENCE | 409 INFERENCE_BUSY，lease 保持，SAFE |
| ZRALD_LEASE_SAFETY | PASS（holder=image-service 全程） |
| QUEUE_TIMING | PASS（0.000 / 59.698） |
| ERROR_ENVELOPE | 统一 `{"error":{code,message}}`（HTTPException 处理器） |
| GIT | 见最终回复（commit `fix: align image quality presets and inference lifecycle` → push） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动，/manager/status 正常） |
| 8011 Image | RUNNING（新代码，idle600，model unloaded，锁 FREE，queue 0/0） |
| 8020 WebUI | RUNNING（dist 重建：中文质量三档+生效步数） |
| 11434 Ollama | RUNNING（10 模型，未动） |
| 3000 OWUI | RUNNING（未动） |
| 8000 vLLM | CLOSED |
| GPU | 299 MiB（正常水位），gpu.lock FREE |
| 服务 env | `~/ai-serving/configs/image/service.local.env`（IDLE=600/RETENTION=1800/CLEANUP=300/QUEUE 1/8/480，真实 CORS origin，**永不入 Git**） |

## 环境要点（下轮必读）

- **Ollama embedding 周期驻留**：LAN 客户端 CLIENT_IP_REDACTED 周期 `/api/embed` → 冷加载前需抓 `/api/ps` 空闲窗口；
  模型载入后不受影响。不绕开 `_ollama_gpu_busy` 保护。
- **pkill/pgrep 自匹配陷阱（本轮又踩一次）**：远端命令串里含被搜模式会自杀；
  一律 `pgrep -f "[s]erver:app"` / `[r]un_xxx` 括号写法，杀进程与启动分两次 SSH。
- **HTTPError body**：urllib 的 `HTTPError` 没有 `.body` 属性，用 `e.read()`（本轮测试脚本踩过）。
- **IAB 自动化限制**：受控 number input `fill("")` 清不掉 → 三击全选 + Backspace；
  截图偶发 compositor 超时 → 改 DOM 只读查询验证；filechooser/download 路由不可用。
- 本机 Mac 代理（127.0.0.1:7897）拦内网 curl —— `--noproxy '*'`。
- 构建工具链：服务器 `$HOME/ai-serving/env/node-v22.23.3-linux-x64/bin`；本地 rollup 原生模块签名损坏，测试在服务器跑。

## Exact Next Action

WAIT FOR COMMANDER REVIEW；可选待办见 NEXT_ACTION

## Do Not

- 未授权不重启/升级 Ollama、不动 vLLM YAML、不动 Zrald/llama.cpp/Open WebUI/CUDA/Clash/网络
- `service.local.env`、`config/models.json`、`config/preset-config.json`、`dist/` 含真实 IP —— 永不入 Git
- 禁 git add -A；生成图片/上传图片/tmp/logs/venv/node_modules 不入 Git
