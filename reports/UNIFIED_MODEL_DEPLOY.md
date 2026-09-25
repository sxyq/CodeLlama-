# Unified Model Deploy Report

任务编号：UNIFIED-MODEL-DEPLOY-001
时间：2026-09-25 20:25 – 21:03 CST
性质：正式部署（停 vLLM · 导入 Zrald · 建 Image runtime · 启动 8011 · 全链路验证）
服务器：SERVER_IP_REDACTED（用户 syy；密码仅经当次 stdin 提权使用，未落盘）

---

## 1. Pre-deploy 基线（2026-09-25 20:25:35，修改前）

| 项 | 值 |
|---|---|
| vLLM main PID / EngineCore PID | 3068143 / 3068373（+ resource_tracker 3068372，tmux session 3068126） |
| vLLM command | `/usr/bin/python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml` |
| port 8000 health | 200 |
| Ollama PID | 3561；port 11434 health 200 |
| Open WebUI port 3000 | 监听中 |
| GPU | 43,812 / 49,140 MiB（vLLM 43,508 + gnome-remote-desktop 266 + Xorg 4） |

## 2. vLLM shutdown

- 方式：`kill -TERM 3068143`（单发 SIGTERM，未用 sudo）
- **ALL_EXITED after 3s**：main / EngineCore / resource_tracker 全部退出，**未使用 SIGKILL**
- 未触碰 Ollama / Open WebUI / Xorg / 桌面进程
- port 8000：`ss` 无监听 → **CLOSED**；health curl → connection refused（000）
- `pgrep vllm.entrypoints` → 无进程

## 3. VRAM release

| 项 | 值 |
|---|---|
| GPU_USED_AFTER_VLLM_STOP | **299 MiB** |
| GPU_FREE_AFTER_VLLM_STOP | **48,242 MiB** |
| 释放量 | ≈43.5 GB（43,812 → 299） |

## 4. Ollama import

- 前置健康：`systemctl is-active ollama` = active；`/api/tags` = 200；模型数 10 → 导入后 11
- 执行：`ollama create qwen3.8-27b-zrald-accuracy -f .../Modelfile.zrald-qwen3.8-27b-accuracy`
- 用时 **2m15s**；复制 16.46GB 时 Ollama 侧重算了 sha（= 322e194f…，与源一致）→ 生成内部 blob（预期存储）
- `ollama list`：**qwen3.8-27b-zrald-accuracy:latest e69fdd4abba4 16 GB**
- `ollama show`：architecture qwen35 · 27.3B · context 262144 · Q4_K_M · num_ctx 32768（Modelfile 参数生效）
- **未手工触碰** `/usr/share/ollama/.ollama` 的 blobs/manifests（全部由 Ollama 自管）

## 5. Zrald cold benchmark — **FAIL（引擎不兼容，非文件问题）**

- cold 请求（/api/chat，"Reply with exactly: OK"）返回：

```
{"error":"failed to initialize model: qwen3next: layer 64 missing attn_qkv/attn_gate projections"}
```

- cold_total 1,230 ms（错误往返）；GPU 全程 299 MiB（**未加载任何权重**）；load/timings 字段不存在
- warm 请求同样错误（1,143 ms）
- 判定：**Ollama 0.20.7 的 qwen35→qwen3next 加载器与该 GGUF 张量布局不兼容**（文件 SHA256 与远端 LFS 完全一致，排除损坏）
- 佐证：仓库 README 标题为 "How to Serve with **llama.cpp** (Verified & Tested)"，官方验证路径是 `llama-server`，非 Ollama

## 6. Zrald warm benchmark — **FAIL（同上，warm 不成立）**

## 7. Zrald measured decode — **NOT AVAILABLE**

- MEASURED tok/s 无法产出（模型从未进入解码阶段）
- 仓库自报 5.99 t/s（MI300X 实测，仅作参考，非本机 MEASURED）

## 8. Zrald unload

- `POST /api/generate keep_alive:0` → `done_reason:"unload"` → **PASS**
- `/api/ps` 中 zrald 不存在（其从未成功加载）；GPU 299 MiB

## 9. Image environment

| 项 | 值 |
|---|---|
| venv | /home/syy/ai-serving/env/image（独立，未污染 vLLM/系统/LLaMA-Factory） |
| Python | 3.12.3 |
| Torch | **2.14.0+cu130**（CUDA build 13.0，cuda_available True，A6000） |
| torchvision | 0.29.0（运行期发现 Qwen3VLVideoProcessor 需要它，已补装） |
| Transformers | 5.17.0（满足官方 ≥5.17） |
| Accelerate | 1.15.0 |
| Diffusers | **0.41.0.dev0（git revision）** |
| fastapi / uvicorn | 0.141.1 / 0.54.0 |
| 其他 | safetensors 0.8.0 · pillow 12.3.0 · numpy 2.5.3 |

## 10. Diffusers version

- PyPI stable **0.40.0 不含 `QwenImage21Pipeline`**（仅有 QwenImage* 一代类）
- 模型卡官方要求：`pip install git+https://github.com/huggingface/diffusers`
- 已按官方安装 **0.41.0.dev0**（`--force-reinstall --no-deps`，未动其他包）

## 11. Image service

- 启动：`env/image/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8011`（cwd=services/image）
- 终态 PID **1687787**；日志 `ai-serving/logs/image/service.log`
- `GET /health` → ok / model_loaded=false；`GET /status` → idle_timeout_seconds=**600**、gpu_lock=null

## 12. Lazy-load verification — **PASS**

- 服务启动后立即核查：`model_loaded=false`，GPU 无新增计算进程（启动本身不加载 33GB 模型）
- 首次 `/v1/images/generations` 才触发 `from_pretrained`（日志 `[model_manager] loaded in 6.55s`）
- 期间修复 2 个骨架问题：
  1. 缺 torchvision → 安装
  2. **加载失败会泄漏 gpu.lock** → 已在 `ensure_loaded` 加 try/except 释放锁（否则一次失败后永久误报 503）

## 13. GPU_BUSY verification — **PASS**

- 场景：后台客户端（Open WebUI embedding 任务）将 `qwen3-embedding:8b` 载入 GPU（size_vram 15,378,904,864 B）
- 调用 `POST /v1/images/generations` → **HTTP 503** `{"detail":{"code":"GPU_BUSY","message":"ollama has a large model in VRAM"}}`
- Ollama runner 进程（PID 1672525）**存活未被杀**；Image model_loaded=false、gpu_lock=null（503 发生在取锁之前）

## 14. Image generation benchmark — **PASS**

| 项 | 值 |
|---|---|
| Prompt | A red apple on a wooden table, studio photography |
| Size / steps | **2048×2048 / 40**（模型卡官方示例参数） |
| HTTP | 200 |
| **lazy model load** | **6.22 s** |
| **generation** | **205.54 s**（40 步） |
| client total | 212.0 s |
| **peak VRAM** | **34,660 MiB** |
| 输出 | /home/syy/ai-serving/logs/image/generated/gen_1790340850_0.png |
| 图片校验 | PNG · RGBA · 2048×2048 · 6,808,019 B · mean 136.4 / std 85.2 → 有效非黑非损坏 **PASS** |

补充（步数=4 快速轮）：load 6.55s / gen 79.3s；load 3.48s / gen 71.2s，图片均有效。

## 15. Image unload — **PASS**

- `POST /unload` → `{"unloaded":true,"model_loaded":false}`，gpu_lock 释放
- **VRAM_AFTER_IMAGE_UNLOAD = 650 MiB**（真实残留 = 服务进程 CUDA context 346 MiB + gnome-remote-desktop 266 MiB + Xorg 4 MiB；权重大头已还回。未伪造为 0）

## 16. Idle unload — **PASS**

- 以 `IMAGE_IDLE_TIMEOUT=60` 重启服务 → `/status.idle_timeout_seconds=60`（测试用）
- 触发加载 → `model_loaded=true`、锁持有 → 静置
- **121 s 后**：`model_loaded=false`、`gpu_lock=null`、图像权重释放（watcher 60s + 15s 轮询）
- 随后**无 env 重启**，终态 `/status.idle_timeout_seconds=600` → **默认 600 已恢复**

## 17. Final service status（21:03:41）

| 服务 | 状态 |
|---|---|
| vLLM | **STOPPED**（无进程） |
| Port 8000 | **CLOSED**（conn refused） |
| Ollama | **RUNNING**（PID 3561），11434 `/api/tags`=200，`/api/ps` 空 |
| Zrald alias | 在列（16 GB），推理受引擎限制（见 §18） |
| Open WebUI | **RUNNING**（3000 `/health`=200） |
| Image Service | **RUNNING**（PID 1687787），8011 LISTEN，health ok，model_loaded=false，idle 600 |
| Image Model | **UNLOADED at idle** |
| Ollama large model | **UNLOADED at idle**（终态快照前主动卸载了后台 embed；其后台客户端后续可能再触发，属既有行为） |
| Final GPU | **299 MiB used / 48,242 MiB free**（0% util，仅桌面小占用） |

## 18. Remaining issues

1. **[BLOCKING · Zrald] Ollama 0.20.7 无法初始化 qwen35 GGUF**（错误见 §5）。文件完好、导入成功，但推理被引擎拒绝。恢复选项（待 Commander 决策，本轮未执行任何一项）：
   - 升级 Ollama 到支持该张量布局的版本（需重启 ollama.service）
   - 安装 llama.cpp `llama-server`（仓库 README 官方验证路径；`-ngl 99 -c 32768`）
   - 评估其他推理栈对 qwen35 GGUF 的支持
2. **[RACE] 后台 embedding 任务可在 Image 生成中途抢占显存**：预检通过后、VAE 阶段 embed 上 GPU → 观察到一次 CUDA OOM 警告（该次请求仍返回 200 且图片有效）。建议后续：生成全程持有 gpu.lock 且 Ollama 侧感知，或统一 scheduler。
3. **[观察] OOM 同时段出现过一次 status 瞬时读数异常**（生成后 2s 报 model_loaded=false），干净环境复测未复现；已记录，未定位到根因。
4. Image `/v1/images/edits` = **501 NOT IMPLEMENTED**（按计划不阻塞本轮）。
5. 后台 Open WebUI embedding 任务在显存空闲时会自动把 embed 模型载入 GPU（本轮反复观察到），属服务端既有行为，未干预。

## 19. Changes made

**REMOTE**
- vLLM：SIGTERM 停止（进程退出，配置文件未动）
- Ollama：新增模型 `qwen3.8-27b-zrald-accuracy`（内部 blob +16.46GB，Ollama 自管）；服务未重启；既有 10 模型未动
- `/home/syy/ai-serving/`：env/image venv 创建；services/image 三文件修补（锁释放、idle 环境变量、响应耗时字段）；logs/image 新增 pip/service/生成图（gen ×3）
- 新常驻服务：8011 Image Service（PID 1687787）

**LOCAL**
- `serving/` 同步（代码修订 + 下载器脚本）
- `reports/UNIFIED_MODEL_DEPLOY.md`（本文件）
- `coordination/PROJECT_STATE.md`、`LAST_HANDOFF.md`、`NEXT_ACTION.md`、`REMOTE_RUNBOOK.md` 更新
- **未 git commit / 未 git push**

## 20. Explicitly NOT performed

- 未删除/移动 `/data/vllm` 任何原模型；未改 `/home/yuyong/vllm` 任何 YAML；未删除 Ollama 原有 10 模型
- 未改 Open WebUI 数据库、CUDA/driver、Clash、全局网络、系统 Python
- 未 kill 任何 Ollama runner / 桌面进程；未使用 SIGKILL
- 未升级/重启 ollama.service；未安装 llama.cpp（Zrald 恢复路径待批）
- 未重新下载任何模型；未做长文本/benchmark 推理
