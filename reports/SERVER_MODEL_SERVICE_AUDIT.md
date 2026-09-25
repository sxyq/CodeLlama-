# Server Model Service Full Audit

任务编号：SERVER-MODEL-SERVICE-FULL-AUDIT-001
时间：2026-09-25 13:49–14:15 CST
性质：只读诊断（未停止/重启/修改任何服务）
服务器：SERVER_IP_REDACTED（主机名 SERVER_HOSTNAME_REDACTED，下文称 REMOTE）

---

## 1. Current Resources

### CPU

| 项 | 值 |
|---|---|
| CPU logical cores | 80 |
| load average (1/5/15) | 0.27 / 0.43 / 0.41 |

### RAM

| 项 | 值 |
|---|---|
| total | 376 GiB |
| used | 20 GiB |
| free | 48 GiB |
| available | 355 GiB |
| swap | 0 B（无 swap） |

### Disk

根分区唯一挂载盘 `/dev/nvme0n1p2` → `/`（3.5T）。`/home` 与 `/data` **不是**独立挂载点，都是根分区上的目录。

| 挂载点 | total | used | available | use% |
|---|---|---|---|---|
| `/` | 3.5T | 2.0T | 1.4T | 60% |
| inode 使用 | — | 8,941,543 / 234,356,736 | — | 4% |

| 目录 | 体积 |
|---|---|
| `/data` | 431G |
| `/home` | 14G |

### GPU

| 项 | 值 |
|---|---|
| GPU model | NVIDIA RTX A6000（单卡） |
| Driver / CUDA | 580.159.03 / CUDA 13.0 |
| total VRAM | 49,140 MiB |
| used VRAM（审计前基线） | 43,812 MiB |
| free VRAM（基线） | ≈ 5,328 MiB |
| GPU utilization | 0%（审计期间多数时间 idle） |
| Temperature | 27–38 °C |
| Power | 9W / 300W |

### GPU processes（基线）

| PID | Process | Owner | VRAM |
|---|---|---|---|
| 221641 | /usr/lib/xorg/Xorg | yuyong | 4 MiB |
| 222398 | gnome-remote-desktop-daemon | yuyong | 266 MiB |
| 3068373 | VLLM::EngineCore | syy | 43,508 MiB |

`ps -fp` 确认：EngineCore 归属 syy，父进程链 = syy tmux session `vllm` → `/usr/bin/python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml`（PID 3068143，2026-09-23 01:29 启动）。

---

## 2. Model Storage

### 2.1 `/data/vllm` 目录级盘点（未加载、未做内容摘要计算）

| # | name | path | disk size |
|---|---|---|---|
| 1 | CodeLlama-13b-Instruct-hf | /data/vllm/CodeLlama-13b-Instruct-hf | 49G |
| 2 | codellama-7b-instruct-hf | /data/vllm/codellama-7b-instruct-hf | 26G |
| 3 | deepseek-coder-6.7b-instruct | /data/vllm/deepseek-coder-6.7b-instruct | 26G |
| 4 | gemma-2-9b | /data/vllm/gemma-2-9b | 35G |
| 5 | gemma-2-9b-it | /data/vllm/gemma-2-9b-it | 18G |
| 6 | gemma-3-12b-it | /data/vllm/gemma-3-12b-it | 23G |
| 7 | Mistral-7B-Instruct-v0.2 | /data/vllm/Mistral-7B-Instruct-v0.2 | 28G |
| 8 | Qwen2.5-Coder-7B-Instruct | /data/vllm/Qwen2.5-Coder-7B-Instruct | 15G |
| 9 | Qwen3-14B | /data/vllm/Qwen3-14B | 28G |
| 10 | Qwen3.5-9B | /data/vllm/Qwen3.5-9B | 19G |
| 11 | starcoder2-7b | /data/vllm/starcoder2-7b | 14G |

附属（非模型）：`huggingface/` 缓存 157G、`.cache`、`._____temp`、`hfd.sh`、`LICENSE`、`README.md`。

**模型目录数量：11**（另有 157G HF 缓存）。

### 2.2 vLLM 配置文件（`/home/yuyong/vllm/`，MODEL_CONFIG_FILES）

| 文件 | model path | served_model_name | port |
|---|---|---|---|
| qwen3-5.yaml | /data/vllm/CodeLlama-13b-Instruct-hf/ | codellama-13b-instruct-hf | 8000 |
| codellama13b.yaml | /data/vllm/CodeLlama-13b-Instruct-hf/ | codellama-13b | 8000 |
| codellama7b.yaml | /data/vllm/codellama-7b-instruct-hf/ | codellama-7b | 8000 |
| deepseek.yaml | /data/vllm/deepseek-coder-6.7b-instruct | deepseek-coder-6.7b-instruct | 8000 |
| mistral.yaml | /data/vllm/Mistral-7B-Instruct-v0.2/ | mistral-7b | 8000 |
| gemma.yaml | /data/vllm/gemma-2-9b-it/ | gemma2-9b | 8000 |
| qwen.yaml | /data/vllm/Qwen2.5-Coder-7B-Instruct | qwen2.5-coder-7b-instruct | 8000 |

**7 个配置全部绑定同一端口 8000、单模型** —— 换模型 = 换配置重启，不是"同一端口多模型并存"。

### 2.3 Ollama 已安装模型（`ollama serve`，/api/tags）

| # | model id | size (bytes) | quant |
|---|---|---|---|
| 1 | qwen3-coder:30b | 18,556,700,761 | Q4_K_M |
| 2 | qwen3-embedding:0.6b | 639,150,858 | Q8_0 |
| 3 | linux6200/bge-reranker-v2-m3:latest | 1,159,777,159 | F16 |
| 4 | nomic-embed-text:latest | 274,302,450 | F16 |
| 5 | qwen2.5-coder:14b-instruct | 8,988,124,298 | Q4_K_M |
| 6 | qwen2.5-coder:7b-instruct | 4,683,087,561 | Q4_K_M |
| 7 | qwen3:8b | 5,225,388,164 | Q4_K_M |
| 8 | qwen3-embedding:8b | 4,676,805,193 | Q4_K_M |
| 9 | codellama:13b-instruct | 7,365,960,935 | Q4_0 |
| 10 | deepseek-r1:7b | （Q4_K_M, 7.6B） | Q4_K_M |

---

## 3. Listening Ports

只读 `ss -lntup`（`sudo -n` 需密码不可用；部分端口属主为其他用户，结合 `ps`/`systemctl`/配置文件归属）。

| PORT | LISTEN addr | PID | USER | PROCESS | 说明 |
|---|---|---|---|---|---|
| **8000** | 0.0.0.0 | 3068143 | syy | python3.12 vllm serve | **vLLM OpenAI API** |
| **11434** | *:0.0.0.0 | 3561 | ollama | /usr/local/bin/ollama serve | **Ollama API（OpenAI 兼容）** |
| **3000** | 0.0.0.0 | 2124 | wsy | open-webui serve --port 3000 | Open WebUI（需登录） |
| 8888 | 0.0.0.0 | 2117 | wsy | jupyter-lab | Jupyter（302 跳登录） |
| 9000 | *:0.0.0.0 | (nginx-ui) | root | nginx-ui | nginx 管理 UI（app.ini HttpPort=9000） |
| 443 | 0.0.0.0 + [::] | 4042966 | root | nginx master | 仅静态站（无 proxy_pass） |
| 9090 | * | 未确认 | — | （401/405，需鉴权） | 非模型服务，属主未确认 |
| 7474 / 7687 | 0.0.0.0 | docker-proxy | root | Docker neo4j | 图数据库，非模型 |
| 6443 / 10250 / 10248-10259 / 10010 | 127.0.0.1 等 | k3s | root | k3s control plane | 集群 |
| 7890 | * | clash-verge | — | 代理 | 非模型 |
| 5201 / 631 / 3389 等 | * | iperf3 / cups / 远程桌面 | — | — | 非模型 |
| 54649 等高位端口 | * | 3068373 | syy | VLLM::EngineCore | vLLM 内部 ZMQ |

模型/API 相关端口结论：**8000（vLLM）、11434（Ollama）、3000（Open WebUI）**。

---

## 4. Running Model Services

`ps -eo user,pid,ppid,lstart,args` 全量筛选结果：

| 服务 | PID | Owner | 启动时间 | 命令 |
|---|---|---|---|---|
| vLLM API | 3068143 | syy | 2026-09-23 01:29 | python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml |
| vLLM EngineCore | 3068373 | syy | 2026-09-23 01:29 | VLLM::EngineCore（43,508 MiB） |
| Ollama | 3561 | ollama | 2026-05-21 | /usr/local/bin/ollama serve（Restart=always） |
| Open WebUI | 2124 | wsy | 2026-05-21 | open-webui serve --port 3000 |
| JupyterLab | 2117 | wsy | 2026-05-21 | jupyter-lab --ip=0.0.0.0 --port=8888 |
| nginx | 4042966 | root | 2026-09-15 | nginx: master |
| nginx-ui | 2123 | root | 2026-05-21 | nginx-ui |
| Docker | 1383596 | root | 2026-06-18 | dockerd（容器仅 neo4j） |

`pgrep -af litellm / one-api / new-api / text-generation / sglang / tgi`：**全部无结果**。

未发现：LiteLLM、one-api、new-api、TGI、SGLang、自定义 FastAPI Router 进程。

---

## 5. Service Managers

### systemd（只读，未做任何 start/stop/restart）

| unit | 状态 | enabled |
|---|---|---|
| ollama.service | active (running)，since 2026-05-21 | enabled |
| open-webui.service | active (running)，since 2026-05-21 | enabled |
| nginx.service | active (running) | enabled |
| nginx-ui.service | active (running) | enabled |
| docker.service | active (running) | — |
| jupyter.service | unit 文件存在 | — |
| vllm / litellm / model 相关 unit | **不存在** | — |

`systemctl --failed`：仅 `nxserver.service`（NoMachine，与模型无关）。

`systemctl cat ollama`：`User=ollama`，`OLLAMA_HOST=0.0.0.0:11434`，`Restart=always`。

### tmux / screen

| session | owner | 说明 |
|---|---|---|
| `vllm`（2026-09-23 01:29:48 创建） | syy | 当前 vLLM 所在，`tmux ls` 可见 |
| `tmux new -s vllm`（2026-05-22 创建，PID 2578574，PPID 1） | yuyong | 训练前旧 session 仍在；socket /tmp/tmux-1013，syy 无权进入，内容未验证 |
| screen | — | 无 |

### Docker

`syy` 不在 docker 组，`docker ps` → permission denied（记录为限制）。通过 docker-proxy 可见宿主端口仅 7474/7687 = neo4j 容器，**无模型容器**（无 ollama/litellm/vllm/open-webui 容器映射）。`docker compose ls` 无输出。

---

## 6. API Gateway / Router

**API gateway/router found: NO**（不存在独立统一网关进程）

证据：

1. `pgrep litellm / one-api / new-api`：无。
2. systemd unit 文件中无代理/llm/api 相关服务（`list-unit-files | grep` 仅命中 iio-sensor-proxy）。
3. nginx：`grep -r proxy_pass /etc/nginx/` → **零命中**；唯一启用站点 `sites-available/default` 只 listen 443、root /var/www/html、无 upstream。
4. `/home/yuyong`、`/home/syy` 深度 4 的 yaml/yml/json/toml/service/sh 中无 litellm/proxy/router/model-router 类配置（仅 vLLM cache json）。
5. `/home/yuyong/vllm/` 7 个 yaml 全部是单模型、同端口 8000 的 vLLM 配置。
6. Open WebUI（3000）探测：`/v1/models` GET → SPA HTML；`/api/models` → 403；`/v1/chat/completions` POST → 405 —— 有登录墙，不是开放的 API 网关。

**Gateway/router type: 无独立网关。"多模型自动加载"能力由 Ollama（11434，OpenAI 兼容 + 按需加载）自身提供。**

---

## 7. Localhost API Tests（REMOTE 上 127.0.0.1）

| Endpoint | HTTP | 结果 |
|---|---|---|
| GET :8000/health | 200 | PASS（0.003s） |
| GET :8000/v1/models | 200 | 1 model：codellama-13b-instruct-hf（root=/data/vllm/CodeLlama-13b-Instruct-hf/，max_model_len=16384） |
| GET :11434/api/tags | 200 | 10 models |
| GET :11434/v1/models | 200 | 10 models（OpenAI 兼容清单） |
| GET :3000/health | 200 | Open WebUI 正常 |
| GET :9000/ | 200 | nginx-ui |
| GET :9090/ | 401 | 需鉴权，非模型 |
| GET :443/ | 404 | nginx 静态站无 index |
| GET :11434/api/ps | 200 | 审计前 `{"models":[]}`（无常驻加载） |

---

## 8. External IP:PORT Tests（从 LOCAL Mac 发起，IP 已脱敏）

| Endpoint | HTTP | connect | total | 错误 |
|---|---|---|---|---|
| EXTERNAL:8000/health | 200 | 0.0002s | 0.019s | 无 |
| EXTERNAL:8000/v1/models | 200 | — | — | 无（1 model） |
| EXTERNAL:11434/api/tags | 200 | 0.0002s | 0.023s | 无 |
| EXTERNAL:11434/v1/models | 200 | — | — | 无（10 models） |
| EXTERNAL:3000/health | 200 | 0.0003s | 0.035s | 无 |
| EXTERNAL:443/ | 404 | — | — | 静态站无页面（非超时/拒绝） |
| EXTERNAL:8888/ | 302 | — | — | Jupyter 登录跳转 |

**EXTERNAL_HEALTH = PASS；EXTERNAL_MODELS = PASS**（8000 与 11434 均 0.0.0.0 绑定、无防火墙拦截；timeout / refused / 502 等错误均未出现）。

防火墙核查限制：`sudo -n ufw status`、`iptables -S`、`nft list ruleset` 全部需要 root（syy 属 sudo 组但需密码）→ **SKIPPED**。因外部实测全通，无需读取规则即可判定放行。

---

## 9. Per-model Test Matrix

请求模板：`POST /v1/chat/completions`，`max_tokens=8, temperature=0`，content="Reply with exactly: OK"；chat 不支持时回退 `/v1/completions`、embedding 类再回退 `/v1/embeddings`。

| Model | localhost | external IP:PORT | HTTP | Result |
|---|---|---|---|---|
| codellama-13b-instruct-hf（vLLM:8000） | 172 ms | 207 ms | 200 | PASS，回复 "OK" |
| qwen3-coder:30b（:11434） | 34,085 ms | 24,648 ms | 200 | PASS，回复 "OK"（按需加载） |
| qwen2.5-coder:14b-instruct | 10,516 ms | 9,381 ms | 200 | PASS，回复 "OK" |
| codellama:13b-instruct | 23,352 ms | 13,093 ms | 200 | PASS，回复 "OK" |
| qwen3:8b | 10,888 ms | 6,164 ms | 200 | PASS（reasoning 输出被 max_tokens 截断） |
| qwen2.5-coder:7b-instruct | 17,186 ms | 5,485 ms | 200 | PASS，回复 "OK" |
| deepseek-r1:7b | 14,485 ms | 9,682 ms | 200 | PASS（think 输出被截断） |
| linux6200/bge-reranker-v2-m3 | 5,224 ms | 3,155 ms | 200 | PASS（可当 chat 调用，输出无意义属预期） |
| nomic-embed-text:latest | chat 400 → embeddings 200（2,450 ms） | chat 400 → embeddings 200（1,055 ms） | 400/200 | PASS（embedding 模型不支持 chat 属预期） |
| qwen3-embedding:0.6b | chat 400 → embeddings 200（9,152 ms） | chat 400 → embeddings 200（6,701 ms） | 400/200 | PASS（同上） |
| qwen3-embedding:8b | chat 400 → embeddings 200（74,803 ms） | chat 400 → embeddings 200（75,243 ms） | 400/200 | PASS（CPU 模式，慢属预期） |

**API_VISIBLE_MODELS**：8000 → 1 个；11434 → 10 个。合计 11 个 model id 全部完成 localhost + 外部双侧最小调用，**无 FAILED、无 model not found**。

---

## 10. Auto-Load Behavior

**AUTO_LOAD_BEHAVIOR = OBSERVED（WORKING）**

实测序列（Ollama，11434）：

1. 调用前：`nvidia-smi` = 43,812 MiB；`/api/ps` = `{"models":[]}`。
2. `POST /v1/embeddings {model: qwen3-embedding:0.6b}` → HTTP 200，耗时 4,937 ms。
3. 调用后：`nvidia-smi` = **48,391 MiB（+4,579 MiB）**；新增 GPU 进程 **PID 1370584 `/usr/local/bin/ollama` 4,574 MiB**；`pgrep` 出现新 `ollama runner --model .../blobs/sha256-... --port 37549`；`/api/ps` 显示该模型已加载（size_vram ≈ 4.46 GB）。
4. 卸载：`POST /api/generate {keep_alive:0}` → `done_reason:"unload"`，显存回落。

其他观察：

- 逐模型测试中每次请求都触发"新 runner 进程 + 显存变化"，验证**按 model 名称动态加载/切换**确实存在。
- OpenAI 兼容 `/v1/*` 请求里的 `keep_alive:0` 不生效（按默认 5 分钟过期）；原生 `/api/generate keep_alive:0` 才能立即卸载。
- 显存峰值（vLLM + Ollama 同时在跑）48,391 / 49,140 MiB；测试结束已回到 ≈43,812–44,121 MiB（余量为 Ollama CPU 模式 runner 的 304 MiB CUDA context，会随 5 分钟过期自动回收）。
- vLLM health 在全部测试前后均为 **200**，EngineCore PID 3068373 未变、未重启。
- 附带发现：审计期间（非本轮请求触发）有第三方客户端周期性加载 `qwen3-embedding:8b`（CPU 模式，size_vram=0），高度疑似 Open WebUI 的后台 embedding 任务；证明 Ollama 有持续的真实使用方。`journalctl -u ollama` 因 syy 不在 adm 组无法确认调用方（限制，见 §12）。

---

## 11. Previous vs Current Architecture

| Capability | Previous（训练前） | Current（本轮实测） | Difference |
|---|---|---|---|
| 统一 IP+port 多模型 | **无单一统一端口的证据**；并存 8000(vLLM 单模型) + 11434(Ollama 多模型) + 3000(UI) | 相同：8000 + 11434 + 3000 均在线 | 无结构差异 |
| /v1/models 多模型 | 11434 有 10 个（Ollama since 2026-05-21 从未停止） | 11434 有 10 个，全部可调用 | 无 |
| 按 model 动态选择 / 自动加载 | Ollama 具备（同一进程自 5 月运行至今） | 实测 WORKING（§10） | 无 |
| 外网可访问 | 8000/11434/3000 均 0.0.0.0 绑定 | 外部实测 200 | 无 |
| CodeLlama 单模型高性能 | vLLM yuyong 起于 2026-09-22 13:18，单模型 qwen3-5.yaml | vLLM syy 起于 2026-09-23 01:29，同配置同模型同端口 | **owner 变更（yuyong → syy）、启动时间变更**；配置/模型/端口一致 |
| 旧 tmux session `vllm`（yuyong） | 训练前 vLLM 所在 | session 进程 2578574 仍在，内部 vLLM 进程已不在 | 旧 session 残留，syy 无权查看内容 |

**Previous architecture evidence（每条均有 process/port/config/API 出处）：**

- 训练前 vLLM：`coordination/VLLM_RUNBOOK.local.md` 历史记录（PID 2570949/2571460，owner yuyong，tmux，port 8000，qwen3-5.yaml，单模型 codellama-13b-instruct-hf）。
- Ollama：`ollama.service` active since 2026-05-21（早于训练），enabled，`OLLAMA_HOST=0.0.0.0:11434`，10 个模型（模型 mtime 2026-04）。
- Open WebUI：`open-webui.service` active since 2026-05-21，enabled。
- nginx：唯一 default 站点自 2023 起无 proxy_pass，从未是模型代理。
- 无 LiteLLM/one-api/自定义 Router 的任何残留（进程、unit、配置三处均为阴性）。

**Current architecture：**

```
A + D 组合（非 C/E/F）：
- 8000  vLLM          → 单模型 codellama-13b-instruct-hf（syy tmux 启动）
- 11434 Ollama        → 10 模型，OpenAI 兼容 + 按需动态加载（systemd）
- 3000  Open WebUI    → 聊天 UI，需登录（systemd, wsy）
- 443   nginx         → 静态页，无模型代理
```

**Architecture classification：**

- 原服务最可能 = **D（Ollama 动态加载）作为多模型入口**，叠加 **A（vLLM 单模型）** 在 8000，UI 侧为 Open WebUI 3000。
- 排除：B（无多 vLLM 并存端口证据，7 个 yaml 全部 8000）、C（无 LiteLLM/proxy 进程与配置）、E（nginx 无 proxy_pass/upstream）、F（无自定义 FastAPI Router 进程/代码）。
- G 其他：无。

**Key difference（用户感知"没有恢复"与实测的差距）：**

按 model 自动加载的多模型能力本轮实测**全部在线、外部可达、10/10 模型调用成功**。用户如果只测了 8000（vLLM 单模型端口），看到的正是"只有 codellama-13b-instruct-hf"——与训练前 8000 的行为一致。**未发现任何在训练期间被停止且未恢复的模型/网关组件。**

**Root cause（初步，需 Commander 与用户确认原入口）：**

1. 最可能：用户原入口是 11434 或 3000（多模型），但恢复验证只覆盖了 8000，用户按 8000 判断"完整体验没恢复"；或用户期望"单端口多模型"，而该形态（统一网关）在现有证据中**从未存在过**。
2. 次可能：用户原用的入口/端口在本次证据链外（各用户 shell history 不可读、无法重建其客户端 URL）。
3. 非根因（已排除）：防火墙拦截（外部 200）、Ollama 停止（since 05-21 运行）、nginx 代理丢失（从未有）、LiteLLM 丢失（从未存在）。

**Is current service equivalent to pre-training service: PARTIAL**（组件全部在线且行为一致，唯一实质差异是 vLLM owner 由 yuyong 变为 syy；"单端口统一多模型"这一形态无证据存在过，故不能判 YES）。

---

## 12. Root Cause / Missing Components

| 核查项 | 结论 |
|---|---|
| LiteLLM / one-api / new-api | 不存在（进程、systemd、配置三处阴性） |
| Ollama | **运行中**，外部可达，auto-load 实测 WORKING |
| Open WebUI | **运行中**，外部可达（需登录） |
| vLLM | **运行中**，外部可达，单模型 |
| nginx 模型代理 | **从未配置**（无 proxy_pass） |
| systemd 失败单元 | 仅 nxserver（无关） |
| 端口未监听 | 模型相关端口 8000/11434/3000 全部监听中 |
| 缺失组件 | **未发现**；无"该起未起"的服务 |

**无法核查的限制（非结论）：**

- `sudo -n` 需密码 → ufw/iptables/nft、`docker ps`、`lsof` 全进程视图、`nginx -T` 完整测试、其他用户 `/proc/<pid>/environ`、Open WebUI 数据库、yuyong/wsy shell history、`journalctl -u ollama` 调用方均不可读。
- yuyong 的 tmux session 内容无法验证（socket 权限）。
- 训练前用户实际使用的 IP:PORT 无法从服务器端取证（history 不可读）。

---

## 13. Recommended Recovery Plan（只建议，本轮未执行）

1. **先向用户确认训练前实际使用的入口**（IP:PORT 是 8000 / 11434 / 3000 中的哪一个，浏览器还是 curl）。本轮证据显示三者当前全部正常，确认入口即可判定是否真有故障。
2. 若确认原入口 = 11434 或 3000：无需任何修复，只需向用户演示现有用法（`POST http://SERVER_IP:11434/v1/chat/completions` + model 名，或浏览器访问 :3000 登录）。
3. 若用户确实需要"单端口返回多模型并自动路由"（原形态从未存在）：可选方案为部署 LiteLLM（或同类 OpenAI 兼容代理）统一入口，upstream = vLLM:8000 + Ollama:11434；属新建服务，需 Commander 批准后另行实施。
4. 可选运维项：将 vLLM 从 syy tmux 迁回 yuyong owner/原 tmux session（独立运维任务，与本诊断无关，迁移动作本身需要停止/重启，本轮禁止）。
5. 清理 yuyong 残留 tmux session `tmux new -s vllm`（PID 2578574）前须由 yuyong 确认其内容。

---

## Changes made

**NONE**（REMOTE 端零修改：未 kill、未重启、未改配置/防火墙/systemd/tmux/Docker/nginx/模型文件；唯一状态变化为对已存在服务的最小 API 请求所触发的 Ollama 按需加载与卸载，审计结束时已回落至基线 ≈43,812 MiB + 过渡期 304 MiB，vLLM health 全程 200、EngineCore 未重启）。
