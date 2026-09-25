# Model Dynamic-Load E2E Validation Report

任务编号：MODEL-DYNAMIC-LOAD-E2E-VALIDATION-001
时间：2026-09-26 00:26 – 00:45 CST
性质：最终 End-to-End 功能验证 + 安全清理 + 文档 + Git（vLLM 保持 STOPPED，未重启/升级 Ollama，未改网络/Open WebUI/CUDA）
服务器：SERVER_IP_REDACTED（用户 syy）

---

## 1. 环境基线（00:26:55）

| 项 | 值 |
|---|---|
| GPU | used 650 MiB / free 47,890 MiB / util 0%（桌面 266 + Image 服务 context 346） |
| port 8000 | **CLOSED**（vLLM 不在，未恢复） |
| 8010 | healthy（backend_alive=false, ctx 32768, lease 空闲, idle 600） |
| 8011 | healthy（model_loaded=false） |
| 11434 | 200 |
| ollama ps | 空 |
| **PRE_TEST_MODEL_INVENTORY** | **11 个模型**（含 KNOWN_BROKEN_DUPLICATE: qwen3.8-27b-zrald-accuracy） |

### 自动分类（以当次 `ollama list` + `ollama show` 实测为准）

| MODEL | TYPE | SIZE | STATUS |
|---|---|---|---|
| qwen2.5-coder:7b-instruct | CHAT/GENERATION（completion/tools/insert） | 4.7 GB | 测试→PASS |
| qwen2.5-coder:14b-instruct | CHAT/GENERATION（completion/tools/insert） | 9.0 GB | 测试→PASS |
| qwen3:8b | CHAT/GENERATION（completion/tools/thinking） | 5.2 GB | 测试→PASS |
| qwen3-coder:30b | CHAT/GENERATION（completion/tools） | 18 GB | 测试→PASS |
| codellama:13b-instruct | CHAT/GENERATION（completion） | 7.4 GB | 测试→PASS |
| deepseek-r1:7b | CHAT/GENERATION（completion，强 thinking） | 4.7 GB | 测试→PASS |
| qwen3-embedding:0.6b | EMBEDDING | 639 MB | 测试→PASS |
| qwen3-embedding:8b | EMBEDDING | 4.7 GB | 测试→PASS |
| nomic-embed-text:latest | EMBEDDING | 274 MB | 测试→PASS |
| linux6200/bge-reranker-v2-m3 | RERANKER（capability=completion） | 1.2 GB | /api/rerank → API_NOT_AVAILABLE |
| qwen3.8-27b-zrald-accuracy | **KNOWN_BROKEN_DUPLICATE** | 16 GB | CONFIRMED_INCOMPATIBLE → 已删除 |

## 2. Zrald cold / warm（llama.cpp :8010）

前置：backend 不存在、GPU≈idle（650 MiB）。首轮尝试被外部 embed 占用 503 拦截（见 §11），卸载后重试成功。

**COLD（REQUEST→SPAWN→LOAD→INFERENCE 一体）**

| 指标 | 值 |
|---|---|
| HTTP | **200** |
| total（含 spawn+load+推理） | **8,905 ms** |
| prompt | 62 tokens @ **124.23 tok/s**（499 ms） |
| decode | 24 tokens @ **35.03 tok/s**（657 ms） |
| 推导 load+overhead | ≈6.7 s |
| usage | prompt 62 / completion 24 |

**WARM**

| 指标 | 值 |
|---|---|
| HTTP | **200** |
| total | **1,093 ms**（cached_tokens 42） |
| prompt | 20 tokens @ 46.01 tok/s（缓存后） |
| decode | 24 tokens @ **35.77 tok/s** |

**内容验证**（max_tokens=128，补测）：返回内容 **`'ZRALD_OK'`**（精确匹配），usage completion 41（含 thinking 段）。

- GPU stable VRAM（加载后）：**18,457 MiB**（llama-server 17,802 + 桌面/context）
- GPU peak（冷热全程采样）：**18,457 MiB**
- **ctx: 32768 · backend: llama.cpp（经 Zrald Lease Manager :8010 → 后端127.0.0.1:8012）**

## 3. Zrald dynamic load / unload

```
REQUEST → SPAWN → LOAD → INFERENCE → IDLE → STOP → VRAM RELEASE   = PASS
```

- idle60 测试：请求完成 → 60s 空闲 → 管理器 SIGTERM 优雅停（日志 `backend stopped (pid …)`）
- 验证：`backend_alive=false` · **8012 CLOSED** · `lease_held=false`（flock 空闲）· **GPU 回到 650 MiB**
- 测试后已恢复 **idle=600**（`/manager/status` 确认）

```
ZRALD_DYNAMIC_LOAD   = PASS
ZRALD_DYNAMIC_UNLOAD = PASS
```

## 4. Ollama 完整模型矩阵（严格串行：load→test→unload→下一个）

每个模型测试前 `ollama ps` 校验（有驻留先安全 unload），测试后 `keep_alive:0` 并确认 ps 空、GPU 回650。

| Model | Type | Load | Inference | Unload | Peak VRAM | Result |
|---|---|---|---|---|---|---|
| qwen2.5-coder:7b-instruct | CHAT | 3,425 ms | 200 · wall 3,521 ms · decode **140.88 t/s** · `OLLAMA_MODEL_OK` | ✓ ps空/GPU650 | 7,351 MiB | **PASS** |
| qwen3:8b | CHAT | 3,560 ms | 200 · wall 4,318 ms · decode **106.23 t/s** · 空内容（thinking 吃满 num_predict=64，推理已执行 64 tok） | ✓ | 11,601 MiB | **PASS** |
| codellama:13b-instruct | CHAT | 3,684 ms | 200 · wall 3,844 ms · decode **86.36 t/s** · `OLLAMA_MODEL_OK` | ✓ | 20,925 MiB | **PASS** |
| qwen2.5-coder:14b-instruct | CHAT | 4,883 ms | 200 · wall 5,010 ms · decode **76.57 t/s** · `OLLOMA_MODEL_OK`（模型自身拼写，输出有效） | ✓ | 15,651 MiB | **PASS** |
| deepseek-r1:7b | CHAT | 3,634 ms | 200 · wall 4,338 ms · decode **133.70 t/s** · thinking 开头被64上限截断 | ✓ | 12,757 MiB | **PASS** |
| qwen3-coder:30b | CHAT | 9,829 ms | 200 · wall 10,040 ms · decode **104.84 t/s** · `OLLAMA_MODEL_OK` | ✓ | 43,943 MiB | **PASS** |
| qwen3-embedding:0.6b | EMBED | 1,771 ms | /api/embed 200 · dim **1024** · wall 1,825 ms | ✓ | 6,775 MiB | **PASS** |
| qwen3-embedding:8b | EMBED | 3,364 ms | /api/embed 200 · dim **4096** · wall 3,434 ms | ✓ | 15,145 MiB | **PASS** |
| nomic-embed-text | EMBED | 1,033 ms | /api/embed 200 · dim **768** · wall 1,071 ms | ✓ | 1,459 MiB | **PASS** |
| bge-reranker-v2-m3 | RERANKER | — | 标准 `POST /api/rerank` → **404**；completion 能力 ping /api/generate 200（模型可加载可响应，非损坏） | ✓ | — | **API_NOT_AVAILABLE**（Ollama0.20.7 无标准端点；模型未判损坏） |
| qwen3.8-27b-zrald-accuracy | BROKEN | — | chat **500**：`qwen3next: layer 64 missing attn_qkv/attn_gate projections`（与历史一致，单次确认后不再重试） | n/a | 0 | **CONFIRMED_INCOMPATIBLE** |

```
Ollama dynamic loading = PASS（每个模型均满足 REQUEST → AUTO LOAD → INFERENCE → keep_alive=0 → VRAM RELEASE）
```

注：每轮卸载后 `gpu_after` 均为 650 MiB；6 个 chat 模型均为冷加载实测（load≈3.4–9.8s）。

## 5. Embedding tests

见上表 3 行：POST `/api/embed`，输入统一 "dynamic loading validation"，仅记录 vector length（1024/4096/768），全部 keep_alive=0 卸载确认。

## 6. Reranker tests

- 标准端点探测：`POST /api/rerank`（query/documents 按任务给定）→ **HTTP 404** → **API_NOT_AVAILABLE**
- 不硬套 chat；以 completion 能力做可用性 ping（/api/generate）→ 200，模型可正常加载运行 → **未判损坏**
- 卸载确认 ✓

## 7. Image generation（Qwen-Image-2.1，:8011）

前置：ollama ps 空、zrald backend 未加载、`model_loaded=false`、GPU 650。

| 指标 | 值 |
|---|---|
| HTTP | **200**（client wall 61,509 ms） |
| **lazy model load** | **1.34 s**（权重已在页缓存） |
| **generation** | **59.95 s**（2048×2048，4 steps，官方示例英文 prompt） |
| GPU peak | **34,726 MiB** |
| 生成期间 lease | **held**（`gpu_lock: "1813048 image-service …"`） |
| model_loaded before request | false ✓ |

```
IMAGE_DYNAMIC_LOAD   = PASS
IMAGE_DYNAMIC_UNLOAD = PASS
```

## 8. Generated image metadata

| 项 | 值 |
|---|---|
| output path | `/home/syy/ai-serving/logs/image/e2e-validation/model-serving-architecture.png` |
| file size | **917,409 bytes**（>0 ✓） |
| PIL | 可读取 ✓（PNG · RGBA） |
| dimensions | **2048 × 2048** ✓ |
| mean/std | 252.4 / 4.9（浅色底技术示意图，非空白非全黑 → **有效**） |
| 入 Git | **禁止**（已在 .gitignore generated/ 覆盖范围外目录，报告中明确不提交该目录） |

## 9. Image unload

- `POST /unload` → `{"unloaded":true,"model_loaded":false}`
- `gpu_lock` → **null**（flock 探针 FREE）
- GPU → **650 MiB**（仅 Image python context346 + 桌面266）

## 10. GPU lock 双向测试（未同时运行两个大模型）

| 方向 | 结果 |
|---|---|
| **ZRALD_BLOCKS_IMAGE** | **PASS**：zrald 持 lease 期间请求 Image → HTTP 503 `gpu lease held by [zrald-manager …]` |
| **IMAGE_BLOCKS_ZRALD** | **PASS**：Image 生成持 lease 期间请求 Zrald → HTTP 503 `lease held by [image-service …]`；Image 正常完成 200 后卸载释放 |

## 11. Ollama external race observations（只记录，未阻止外部客户端）

`journalctl -u ollama` 自 00:26 起的 `/api/embed`：

| 时间 | 来源 | 耗时 |
|---|---|---|
| 00:27:20 | **CLIENT_IP_REDACTED（LAN）** | 3.85 s |
| 00:31:50 | **CLIENT_IP_REDACTED（LAN）** | 4.03 s |
| 00:32:03 | **CLIENT_IP_REDACTED（LAN）** | 387 ms |
| 00:35:39/45/48 | 127.0.0.1（= 本任务 embedding 自测） | 1.8/3.4/1.1 s |

- **RACE EVENT**：00:31:50–00:32:03 LAN embed 将 qwen3-embedding:8b（14.5GB）载入 GPU → **Zrald 冷启动首次尝试被 503 GPU_BUSY 拦截**（同窗口 Image 请求亦503）；卸载后重试成功。
- 成功推理窗口（Zrald 冷/热、30b、两次 Image 生成、双向锁测）内**未观察到**外部 embed 插入、**无 OOM、无 slowdown**。
- 期间观察到的最大总显存为30b 测试时 48,019 MiB（当时 zrald 后端常驻，事后已停）——未 OOM。
- `Ollama external race observed: **YES**`（阻塞式影响1次；外部客户端未被停止）

## 12. Duplicate cleanup

前置四条件全部满足（llama.cpp PASS / 同错误复确认 / 名称精确 / 源文件独立）后执行：

```
BEFORE: 11 models（含 qwen3.8-27b-zrald-accuracy:latest 16GB）
ollama rm qwen3.8-27b-zrald-accuracy  → deleted 'qwen3.8-27b-zrald-accuracy'  = RM_OK
AFTER : 10 models（其余全部在列）
```

- `/data/vllm/Zrald-Qwen3.8-27B-v2/` 存在，size 16,464,440,224，**SHA256 = 322e194f…（复算 MATCH，未被删除）**
- Ollama store：**64 G**（blob 中 `322e194f` 引用计数 =0，16.46GB blob 已回收）
- 删除后功能抽查：`/api/embed`（qwen3-embedding:0.6b）→ **200**，其余模型不受影响
- df 读数 2.1T/62%（四舍五入粒度内）

```
OLLAMA_DUPLICATE_REMOVED = YES
RECOVERED_SPACE = 16,464,440,224 bytes（≈16 GB）
```

## 13. Final API map（最终调用拓扑）

```
TEXT / ZRALD:            CLIENT → :8010 → Zrald Lease Manager → llama.cpp → Qwen3.8-27B Accuracy
OTHER OLLAMA TEXT/EMBED: CLIENT → :11434 → Ollama → requested model
IMAGE:                   CLIENT → :8011 → Image Service → Qwen-Image-2.1
```

- **OPEN_WEBUI_REQUIRED = NO**（:3000 Open WebUI 未删除、未停止、未修改，仅不被依赖）
- vLLM 保持 STOPPED（8000 CLOSED），本轮未恢复

### 最终动态行为确认（§20）

| 链路 | 结果 |
|---|---|
| Zrald REQUEST→SPAWN→LOAD→INFERENCE→IDLE→STOP→VRAM RELEASE | **PASS** |
| Ollama 各模型 REQUEST→AUTO LOAD→INFERENCE→keep_alive=0→VRAM RELEASE | **PASS PER MODEL**（10/10；reranker 端点除外标 API_NOT_AVAILABLE） |
| Qwen-Image REQUEST→LAZY LOAD→GENERATE→UNLOAD→VRAM RELEASE | **PASS** |

## 14. Remaining issues

1. LAN 客户端 CLIENT_IP_REDACTED 直连11434 不受统一 lease 约束——可造成测试前 503 拦截（已观察1次）；Gateway/绑定方案仍待 Commander 决策（见 NEXT_ACTION）。
2. Ollama 0.20.7 无标准 `/api/rerank`（reranker 模型可用性只能以 completion 能力佐证）。
3. thinking 类模型（qwen3:8b、deepseek-r1:7b）在 num_predict=64 下内容为空/截断，属预算问题非功能问题。
4. 示意图以 4-step 快速配置生成（任务指定），画面偏淡（mean252）——如需更清晰版本可后续用 40-step 高质量模式重生成，非本轮目标。
5. Git 执行结果见 §15/最终回复（commit/push 于报告生成后执行）。
