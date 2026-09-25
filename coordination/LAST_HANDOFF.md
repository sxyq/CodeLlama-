# Last Agent Handoff

Updated At: 2026-09-26  
Last Task ID: MODEL-DYNAMIC-LOAD-E2E-VALIDATION-001  
Status: E2E VALIDATION COMPLETED — GIT COMMITTED & PUSHED（结果见最终回复/ git log）

## Completed

- **Zrald 动态链路 PASS**：cold 8,905 ms（prompt 124.23 t/s · decode 35.03 t/s，推导 load≈6.7s）；warm 1,093 ms（decode 35.77 t/s）；内容验证 `ZRALD_OK` 精确返回；idle60 → 后端 GONE + 8012 关闭 + lease 释放 + GPU→650；**idle 已恢复 600**；ctx 32768；backend=llama.cpp（:8010 管理器）
- **Ollama 10/10 模型 E2E PASS**（严格串行 load→test→keep_alive:0→GPU650）：
  - chat×6：qwen2.5-7b(140.88 t/s)、qwen3:8b(106.23)、codellama13b(86.36)、qwen2.5-14b(76.57)、deepseek-r1:7b(133.70)、qwen3-coder:30b(104.84)，load 3.4–9.8s，全部 200
  - embed×3：dim 1024 / 4096 / 768 全 200
  - bge-reranker：`/api/rerank` 404 → **API_NOT_AVAILABLE**（completion ping 200，模型未损坏）
  - duplicate：同 qwen3next 错误 → **CONFIRMED_INCOMPATIBLE**
- **Image PASS**：lazy load 1.34s → gen 59.95s（2048²/4-step）→ 峰 34,726 MiB → lease 持有 → unload 释放锁/GPU650；产出 `logs/image/e2e-validation/model-serving-architecture.png`（917,409 B，PNG RGBA 2048×2048，有效）
- **GPU lock 双向 PASS**：Zrald→Image 503（lease by zrald-manager）；Image→Zrald 503（lease by image-service）；从未同时运行两个大模型
- **Race 观察**：LAN CLIENT_IP_REDACTED embed ×3（00:27:20/00:31:50/00:32:03）曾致 Zrald 冷测首试 503（重试成功）；成功推理窗口无干扰、无 OOM；外部客户端未动
- **Duplicate 清理**：`ollama rm qwen3.8-27b-zrald-accuracy` = RM_OK（11→10 模型全在）；/data 源 GGUF SHA256 复验 MATCH；store 64G（16.46GB blob 已消失）；**RECOVERED ≈16,464,440,224 B**；删后 embed ping 200
- **OPEN_WEBUI_REQUIRED = NO**（:3000 未动）
- 文档：`reports/MODEL_DYNAMIC_LOAD_E2E_VALIDATION.md` + PROJECT_STATE / NEXT_ACTION / REMOTE_RUNBOOK 更新
- **Git：secret scan PASS（无密码/无原始 IP 入库；REMOTE_ACCESS.local.md 被 ignore）→ 已显式 add → commit `feat: finalize dynamic model serving and validation` → push main**（hash 见 git log / 最终回复）

## Status Flags

| Flag | Value |
|---|---|
| ZRALD_DYNAMIC_LOAD / UNLOAD | PASS / PASS |
| OLLAMA_E2E | PASS（10/10；reranker=API_NOT_AVAILABLE） |
| IMAGE_LOAD / GENERATE / UNLOAD | PASS / PASS / PASS |
| GPU_LOCK BIDIRECTIONAL | PASS |
| OLLAMA_DUPLICATE_REMOVED | YES（≈16.46GB 回收） |
| OLLAMA_RACE_OBSERVED | YES（LAN embed 阻塞1次，无 OOM） |
| VLLM | STOPPED（8000 CLOSED） |
| OPENWEBUI_REQUIRED | NO |
| SECRET_SCAN | PASS |
| GIT | COMMITTED & PUSHED（HEAD==origin/main 见最终回复） |

## 服务终态

| 端口 | 服务 | 状态 |
|---|---|---|
| 8010 | Zrald llama.cpp（管理器+按需8012） | RUNNING，idle600，lease 空闲 |
| 8011 | Image Service | RUNNING，unloaded，idle600，锁空闲 |
| 11434 | Ollama（10 模型） | RUNNING |
| 3000 | Open WebUI | RUNNING（不被依赖） |
| 8000 | vLLM | CLOSED |
| GPU | 650 MiB used（桌面+image context） | 基线 |

## Exact Next Action

WAIT FOR COMMANDER REVIEW；可选项见 NEXT_ACTION（LAN Gateway 方案、rerank 端点、40-step 高质量示意图）

## Do Not

- 未授权不恢复 vLLM、不升级/重启 Ollama、不改 LAN bind/网络
- 生成图片与日志不入 Git（.gitignore 已覆盖）
