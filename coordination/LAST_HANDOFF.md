# Last Agent Handoff

Updated At: 2026-09-26  
Last Task ID: IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001  
Status: COMPLETE — AWAITING COMMANDER REVIEW（Git 结果见最终回复 / git log）

## Completed

- **WebUI 平台上线**：CookSleep/gpt_image_playground @ `aa2556df`（MIT，npm+Vite6），部署于
  `/home/syy/ai-serving/webui/image-platform/{upstream,dist,config,scripts,README.local.md}`，
  `serve_static.py` 服务 **0.0.0.0:8020**（无 Docker、无账号）；构建链 = `gen-preset-config.py` →
  `VITE_DEFAULT_API_URL=… npm run build`（Node v22.23.3 独立于 ai-serving/env，未动全局）
- **上游 P1–P5 补丁**（build ✓ / test ✓ 34文件576用例全绿）：
  P1 negative_prompt/steps/seed 控件+透传；P2 尺寸 512–2048/64倍数/预设重写；
  P3 n上限10→4；P4 mask 禁用→toast `Mask editing unsupported by current model.`；P5 队列徽标
- **8011 后端改造**：
  - `queue_manager.py`：generations/edits 共享单槽队列（1/8/480s），FIFO 授槽，429 QUEUE_FULL/503 QUEUE_TIMEOUT，
    顺序 queue→gpu.lock→双重复核→推理（flock 不绕开）
  - `temp_output.py`：输出只写 tmp/image-output，TTL 1800s/300s 周期+启动即扫；仅删根下常规文件，symlink 跳过、越界拒绝
  - CORS：`IMAGE_ALLOWED_ORIGINS` 精确白名单（代码零真实 IP），预检/浏览器全链路实测 PASS
  - 双端点 `b64_json`（保留旧 b64/path/width/height）；edits 同时接 `image[]`（上游）与 `image`（旧客户端）、
    `size=auto`→保持原尺寸、显式尺寸 512–2048/16 倍数校验、mask→400 MASK_UNSUPPORTED、多图→400
  - negative_prompt → `true_cfg_scale=4.0`（QwenImage21 管线仅 CFG>1 时生效）
  - edit keep-original：ceil-16 生成后 crop 回精确原尺寸（1920×1080 类输入可用）
  - `/unload` 运行中加推理深度防护位（idle watcher 推理中不卸载）；generation_seconds 计时修复
- **E2E 实测**：队列串行化 PASS（采样 running=1/pending=1、双200）；TTL 60s 实测 PASS（已恢复 1800/300）；
  浏览器 t2i 1024²+1536×1024 PASS、edit keep-original(1536×1024) PASS、edit custom(→1024²) PASS、
  预设 4/4、mask toast 精确文案、徽标"队列 1/0"；IDLE=60 自动卸载 PASS（已恢复 600）；
  `/unload` → false+FREE；回归 8010/8011/8020/11434/3000 PASS、8000 保持 CLOSED
- 报告：`reports/IMAGE_WEBUI_QUEUE_TEMP_STORAGE.md`

## Status Flags

| Flag | Value |
|---|---|
| WEBUI :8020 | RUNNING（dist 含 preset：real IP + apiKey 占位 internal-no-auth） |
| IMAGE_QUEUE_SERIALIZATION | PASS |
| QUEUE_FULL → 429 | PASS |
| IMAGE_TEMP_CLEANUP | PASS（60s 实测，正式 1800/300 已恢复） |
| TTL/清理安全 | PASS（symlink/越界拒绝，单测+远端一致） |
| OLD_API_COMPATIBILITY | PASS（旧 image/width/height curl 实测 200） |
| MASK_EDIT | DISABLED_BY_UI + 400 MASK_UNSUPPORTED（不伪造） |
| GIT | 见最终回复（commit `feat: deploy internal image webui platform` → push） |

## 服务终态

| 端口 | 状态 |
|---|---|
| 8010 Zrald | RUNNING（未动） |
| 8011 Image | RUNNING（queue+CORS+TTL，model unloaded，idle600，锁 FREE） |
| 8020 WebUI | RUNNING（serve_static.py） |
| 11434 Ollama | RUNNING（10 模型，未动） |
| 3000 OWUI | RUNNING（未动） |
| 8000 vLLM | CLOSED |
| GPU | 299 MiB（正常水位），gpu.lock FREE |
| 服务 env | `~/ai-serving/configs/image/service.local.env`（真实 CORS origin，**永不入 Git**） |

## 环境要点（下轮必读）

- **Ollama embedding 周期驻留**：LAN 客户端 CLIENT_IP_REDACTED 周期 `/api/embed` → `qwen3-embedding:8b` 占 ~14.4GB，
  Image 冷加载会被 `_ollama_gpu_busy` 拦成 503。需抓 `/api/ps` 为空的窗口再跑需加载的测试；不绕开该保护。
- **pkill/pgrep 自匹配陷阱**：SSH 单行里 `pkill -f "uvicorn server:app"` 会杀掉含同串的自身 bash 会话；
  用 `pgrep -f "[s]erver:app"` 拿 PID 再 `kill $PID`，启动与杀进程分两次 SSH。
- **IAB 自动化限制**：filechooser/download 事件报 `ambiguous routed session`；图片素材走「生成→编辑输出」，下载验证以客户端字节完整性替代。
- 本机 Mac 代理（127.0.0.1:7897）会拦内网 curl —— 用 `--noproxy '*'`。
- 构建工具链：服务器 `$HOME/ai-serving/env/node-v22.23.3-linux-x64/bin`（PATH 前缀）。

## Exact Next Action

WAIT FOR COMMANDER REVIEW；可选待办见 NEXT_ACTION

## Do Not

- 未授权不重启/升级 Ollama、不动 vLLM YAML、不动 Zrald/llama.cpp/Open WebUI/CUDA/Clash/网络
- `service.local.env`、`config/models.json`、`config/preset-config.json`、`dist/` 含真实 IP —— 永不入 Git
- 禁 git add -A；生成图片/上传图片/tmp/logs/venv/node_modules 不入 Git
