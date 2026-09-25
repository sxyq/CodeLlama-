# Zrald llama.cpp & GPU Scheduler Audit/Deploy Report

任务编号：ZRALD-LLAMACPP-AND-GPU-SCHEDULER-001
时间：2026-09-25 22:21 – 23:24 CST
性质：只读调查 + 独立安装 + 服务部署 + 统一 GPU lease（未升级/重启 Ollama，未删除任何 Ollama 模型，未 Git 提交）
服务器：SERVER_IP_REDACTED（用户 syy；密码仅经当次 stdin 提权使用，未落盘）

---

## 1. 保护性基线（22:21:52）

| 项 | 值 |
|---|---|
| GPU | 14,800 / 49,140 MiB（后台 embed:8b 14.5GB 占用 + 桌面 266MiB） |
| ollama ps | qwen3-embedding:8b（size_vram 15,378,904,864，expires 22:26:18） |
| ollama list | 11 个模型 |
| 11434 / 3000 / 8011 | 200 / 200 / 200（image model_loaded=false, idle 600） |
| vLLM | 不存在，8000 监听数 0 |

## 2. Zrald 文件复核（禁止重下）

- `/data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf`
- size = **16,464,440,224**（与上阶段一致）
- SHA256 = **322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482**（与上阶段报告及远端 LFS 一致 → MATCH，继续）

## 3. llama.cpp 安装（独立，不污染任何既有环境）

| 项 | 值 |
|---|---|
| 位置 | /home/syy/ai-serving/runtime/llama.cpp（源码 + build/） |
| 获取方式 | git clone --depth 1 经 Clash 代理（github.com 直连不可达，代理仅用于该次克隆） |
| **revision** | **e85e15cf6d810cd1268498c2e5b657bb3ece47bc**（2026-09-25 main） |
| version | llama-cli: `version: 0.5.0-dev (build 1, commit e85e15c)`，GNU 13.3.0 |
| **build flags** | `-DGGML_CUDA=ON -DGGML_CUDA_ARCHS=86 -DCMAKE_BUILD_TYPE=Release`（CMakeCache 另录 GGML_CUDA_FA=ON） |
| CMake 来源 | pip 安装于独立 venv `runtime/tools/buildenv`（cmake 4.4.3），未动系统 |
| CUDA | **YES**（/usr/local/cuda-13.0 nvcc V13.0.88；libggml-cuda.so 46MB 链入） |
| 产物 | build/bin/llama-cli、llama-server 均存在（动态链接模块化布局） |

未安装到系统路径；未触碰 Ollama / Image venv / 原 vLLM。

## 4. Metadata / loader smoke

- llama-cli 成功读取模型：build b1-e85e15c · **ftype Q4_K - Medium** · modalities text
- llama-server `/v1/models` 返回：id `zrald-qwen3.8-27b-accuracy`，**n_ctx 32768**（-c 参数生效），n_ctx_train 262144，n_params 27,320,697,856，vocab 248,320
- 初始 ctx 即为 **32768，未配置 262144**

## 5. Zrald 最小 CLI 推理（MEASURED）

前置：Qwen-Image unloaded、Ollama ps 无大模型（embed 已 keep_alive:0 卸载）。

| 轮次 | 结果 |
|---|---|
| 首次（交互模式误入，-no-cnv 已废弃） | 模型**成功加载并生成**：Prompt 114.2 t/s · Generation 34.3 t/s；因 stdin EOF 进入空转，420s 超时终止（RC=124，用量大输出，已丢弃） |
| 干净单轮（`-st --single-turn`） | **RC=0，wall 8,857 ms**；Prompt **111.9 t/s**；Generation **34.1 t/s**；推理文本含思考段后正常退出 |

- **Zrald CLI load: PASS**（llama.cpp 完整初始化该 qwen35 GGUF —— 与 Ollama 形成对照）
- **Zrald inference: PASS**
- **Measured decode: 34.1 t/s（CLI，单轮 MEASURED）**；重复轮34.3 t/s；server 侧34.28 t/s（§6）
- **Measured load（端到端）**: CLI wall 8.86s（热页缓存）；server 冷 spawn→ready **7.7 s**
- **Peak VRAM（CLI 轮，0.5s 采样）: 32,157 MiB**；llama-server 稳态 **17,790 MiB**（-c32768 下）
- 全程 `-ngl 999`（全 GPU offload）；stderr 未含分项计时（该版本计时输出在 stdout）

## 6. llama-server（port 8010）

- 架构：`services/zrald/zrald_lease_manager.py`（系统 python3）监听 **0.0.0.0:8010**，反向代理至本机 `127.0.0.1:8012` 的 llama-server（模型仅本机可直达）
- 后端命令：`llama-server -m <accuracy.gguf> --host 127.0.0.1 --port 8012 -c 32768 -ngl 999 --alias zrald-qwen3.8-27b-accuracy`
- **llama-server: RUNNING**（经管理器按需拉起，backend_pid 1818912，spawn_count 2）
- 验证：
  - `GET /health` → 200（管理器本地应答：status ok / backend_alive true / ctx 32768）
  - `GET /v1/models` → 200，模型 id `zrald-qwen3.8-27b-accuracy`
  - `POST /v1/chat/completions` → **200**，953 ms（已加载时），usage prompt57/completion16
- server 日志实测（MEASURED）：**prompt eval 114.46 t/s** · **eval 34.28 t/s**
- 状态观测：`GET /manager/status`（backend_alive / lease_held / inflight / idle_timeout / spawn_count / ctx）

## 7. 文本服务生命周期

- llama.cpp 原生能力调查（源码核实）：**`--sleep-idle-seconds`** 存在——空闲后回调 `handle_sleeping_state → destroy()`（销毁模型释放显存），新请求自动 `load_model()` 唤醒；另见 `--slots`/LoRA 等端点。**原生 idle sleep 可用但不满足"取锁后再加载"的 lease 时序**（请求直达后端时锁窗外）。
- 采用任务指定的管理器方案：
  1. 首个 API 请求 → **flock 统一 lease** → 复查 Ollama/nvidia → 启动 llama-server
  2. lease 在进程存活期间**持续持有**（覆盖全部推理）
  3. 空闲 > `ZRALD_IDLE_TIMEOUT`（默认 **600**）→ **SIGTERM 优雅停止**（15s 宽限，失败才 kill）→ 释放 lease → GPU 归零
- **Idle lifecycle 实测（60s 测试）**: spawn（lease 持有，18GB）→ 80s 后 `backend_alive=false`、进程 GONE、**lease_held=false**、flock 探针 **ACQUIRED（空闲）**、日志 `backend stopped (pid …)`；随后已按默认 **600** 重启管理器
- `/health` 与 `/manager/status` 为本地应答，不触碰后端、不刷新 idle

## 8. 统一 GPU Lease（原子锁）

- 路径：`/home/syy/ai-serving/state/gpu.lock`
- 机制：**`flock(LOCK_EX | LOCK_NB)`（OS 级原子）**，文件常驻不 unlink（inode 稳定）；写入 `{pid} {role} {ts}` 供持有者展示
- **GPU atomic lock: PASS**
  - 探针验证：空闲时外部进程可立即 flock 成功；持有时失败并报告持有者
  - 持有方：Image(8011) 与 Zrald manager(8010) 各自进程内持 fd，覆盖"获取 lease → 复查 → 加载 → 推理 → 卸载 → 释放"全周期
- 取代了原 Image 的 O_EXCL"先查再建"实现（该实现存在竞争窗口，且失败路径曾泄漏锁）

## 9. Image 锁改造与重测

model_manager.py / server.py 变更：

1. O_EXCL 文件锁 → **flock 原子 lease**（不 unlink）
2. **取锁后二次复查**：Ollama /api/ps（>1GB 即忙）+ `nvidia-smi` 其他进程 >1GiB（排除自身）→ 冲突则放锁返回 503
3. 加载异常路径放锁（既有 try/except 保留）；status 展示以**实时 fd 状态**为准（不再读陈旧文件内容）

**Image lock: PASS / Image retest: PASS**

| 场景 | 结果 |
|---|---|
| C. Ollama embed 14.5GB 驻留 → 图像生成 | **503** `{"code":"GPU_BUSY","message":"ollama has a large model in VRAM"}`，image lock=null |
| A. Zrald 持 lease → 图像生成 | **503** `gpu lease held by [1816337 zrald-manager …]`（原子互斥，锁未被抢） |
| B. 图像生成持锁中 → Zrald 调用 | **503** `lease held by [1813048 image-service …]`（反向互斥） |
| D. 正常生成 | **200**（load 6.25 s + gen 63.3 s，steps=4，图已生成）；期间 status 显示 lease 持有 |
| 卸载 | `{"unloaded":true}` → lock=null → **flock 探针 FREE** |

（取锁后的二次复查逻辑已实现；"复查后毫秒级窗口内 Ollama 突入"的确定性触发测试未强造——该窗口已从"预检后直接加载"缩小为"持锁期间复查"。）

## 10. Ollama 后台 runner 调用源（只读定位，成功）

方法（全部只读）：/api/ps 时序、进程树、run_eval 排查（user lc，6 月起空闲，排除）、6 分钟静默观测（证明存在与本方轮询无关的真实请求）、**sudo journalctl -u ollama**。

决定性证据（GIN 访问日志）：

```
[GIN] POST "/api/embed" 200  4.6s   from 10.16.x.x   23:17:34
[GIN] POST "/api/embed" 200  388ms  from 10.16.x.x   23:18:29
[GIN] POST "/api/embed" 200  434ms  from 10.16.x.x   23:23:03
[GIN] POST "/api/embed" 200  377ms  from 10.16.x.x   23:23:51
（本机 127.0.0.1 的记录只有我们自己的 GET /api/ps）
```

- **Ollama background runner source = 局域网外部主机 CLIENT_IP_REDACTED 的 `POST /api/embed`**（Ollama 监听 0.0.0.0:11434 暴露于局域网）
- 频率：不规则，约每 1–6 分钟一次；首次 4.6s（含加载），后续 ~400ms
- **本机 Open WebUI 已排除**（其请求会显示 127.0.0.1；journal 中无本机 embed 调用）
- 无法在本机进一步定位该远端主机上的进程（无该主机访问权）

## 11. 分类与剩余竞争

```
LOCKED BACKENDS（受统一 flock lease 约束，互斥已实测 PASS）:
  - Image Service (8011)
  - Zrald llama.cpp (8010/8012)

UNCOORDINATED BACKEND:
  - Ollama direct clients（尤其局域网 CLIENT_IP_REDACTED 的 POST /api/embed，
    以及任何直连 11434 的调用）——不遵守 gpu.lock
```

**Remaining Ollama race: YES** —— Ollama 不感知 lease，LAN 客户端可在 Zrald/Image 推理中途抢占显存（embed 14.5GB 级）。本轮已在两侧做"取锁后复查"缓解，并明确不宣称完全解决。

**方案（仅提出，本轮不实施）：**
1. 将 Ollama 绑到 127.0.0.1，由统一 Gateway（实现 lease 语义）反代 —— 需与 CLIENT_IP_REDACTED 使用方协调（改端口会破坏其现有直连）
2. Gateway 聚合 Ollama/Zrald/Image 三者（请求级排队），Open WebUI 一并改走 Gateway（不破坏现有功能，仅改 base URL——本轮不修改 Open WebUI）
3. 与 CLIENT_IP_REDACTED 属主沟通调用时段/迁移至 Gateway
4. （可选）llama.cpp 原生 `--sleep-idle-seconds` 作为 Zrald 后端的第二层空闲保护

## 12. Ollama 中的 Zrald 重复项

- **Ollama Zrald duplicate: PRESENT**（`qwen3.8-27b-zrald-accuracy`，16GB，`ollama show` 正常但初始化失败 → **UNUSABLE_DUPLICATE**）
- **Deleted: NO**（本轮明确不 ollama rm；回收 ~16GB 待 Commander 决策）

## 13. 终态服务表（23:24:32）

| 服务 | 状态 |
|---|---|
| vLLM | **STOPPED**，8000 无监听 |
| Ollama 11434 | **HEALTHY**（ps 空；11+1 模型） |
| Open WebUI 3000 | **HEALTHY** |
| Image 8011 | **HEALTHY**（model_loaded=false, idle 600, lock=null） |
| Zrald 8010 | **HEALTHY**（backend_alive=true, ctx 32768, lease_held=true, idle 600） |
| llama-server 8012 | **RUNNING**（pid 1818912，-ngl 999，17,790 MiB） |
| GPU | 18,445 used / 30,095 free（Zrald 17,790 + Image python context 346 + 桌面 266；embed 已卸载） |

> 说明：Image 服务进程保留 346 MiB CUDA context 属常驻进程残余（无权重）；Zrald 的 17.8GB 在 idle 600 秒无请求后由管理器自动释放。

## 14. 文件变更

**REMOTE**：新增 `runtime/llama.cpp`（源码+构建）、`runtime/tools/buildenv`（cmake）、`services/zrald/{zrald_lease_manager.py,README.md}`、`logs/zrald/*`；修订 `services/image/{model_manager.py,server.py}`；重启 8011、启动 8010 管理器；Ollama/既有模型/网络配置零改动
**LOCAL**：`serving/` 同步（services/scripts/state，排除 runtime/env/logs）、`reports/ZRALD_LLAMACPP_AND_GPU_SCHEDULER.md`、coordination 四文件更新
**Git**：仅 status/diff，**未 commit、未 push**

## 15. 明确未做

未升级/重启 Ollama；未删除/修改任何 Ollama 模型；未改 Open WebUI；未重下载/重量化 Zrald；未动 CUDA/driver/Clash/防火墙；未 kill -9（优雅路径均成功）；未污染 Image venv/系统 Python/原 vLLM。
