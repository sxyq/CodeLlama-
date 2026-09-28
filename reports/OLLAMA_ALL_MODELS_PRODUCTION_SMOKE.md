# OLLAMA ALL MODELS PRODUCTION SMOKE REPORT

Task ID: OLLAMA-ALL-MODELS-PRODUCTION-SMOKE-001
Date: 2026-09-28
Result: **NETWORK_BLOCKED**

---

## 1. Reachability check（任务书 §1，第一步）

从执行机对 SERVER_IP 的直接 TCP 探测：

| Target | Round 1 | Round 2 | Round 3 | Round 4 |
|---|---|---|---|---|
| SSH :22 | FAIL (timeout) | FAIL | FAIL | FAIL |
| SERVER_IP:11434 | FAIL (timeout) | FAIL | FAIL | FAIL |
| SERVER_IP:8011 | FAIL (timeout) | FAIL | FAIL | FAIL |

- 4 轮探测，含 20s 间隔重试，跨约 1 分钟；本轮之前十余分钟内另有 5 次以上同样结果。
- 诊断（本机侧，只读）：执行机当前位于 `10.225.129.0/24`（en0，网关可达、ARP 正常），路由表中**无到 `10.16.15.x` 网段的路由**，流量走默认网关后丢弃；到该网段无 ARP 记录。
- 上一次成功 SSH 是 2026-09-27 完成 `OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001` 时，其后执行机网络发生切换。

**判定：NETWORK_BLOCKED → 按任务书 §1 STOP。**

---

## 2. 未执行项（不猜测、不伪造）

以下全部**未执行**，因为无法建立到服务器的连接。本报告不包含任何本轮的服务状态断言、端口读数、模型清单读数或 PASS 结论。

- §2 端口核验（`ss -lntp`）：未执行
- §3 当前模型清单（`ollama list` / `GET /api/tags`）：未执行
- §5 Chat 模型 6 个串行调用：未执行
- §6 Embedding 模型 3 个调用：未执行
- §7 Reranker 调用：未执行
- §8 严格串行 runner 释放验证：未执行
- §9 GPU / peak VRAM 记录：未执行
- §10 Gateway log 核对与 Image 状态确认：未执行
- §12 Qwen3.5-9B 只读核验（`ls /data/vllm/Qwen3.5-9B`、读取 `config.json`）：未执行
- §13 vLLM :8000 与进程只读核验：未执行

最终结果表（§11）：**无可填行**——没有发起任何调用，因此没有 HTTP 码、维度、显存或释放结果可记录。

```
| Model | Type | Endpoint | HTTP | Output/Dim | Peak VRAM | Released | Result |
|---|---|---|---|---|---|---|---|
| （全部） | — | — | — | — | — | — | 未执行（NETWORK_BLOCKED） |
```

---

## 3. 历史参考（非本轮实测，仅供网络恢复后对照）

以下来自本会话 2026-09-27 `OLLAMA-QWEN3-EMBEDDING-06B-VERIFY-DEPLOY-001` 的真实读数，**不是本轮结果**：

- 端口当时：11434 网关 LISTEN、11435 仅回环、8010/8011/8020/3000 开、8000 CLOSED
- 模型当时：10 个（6 chat + 3 embedding + 1 reranker），与任务书预期一致
- `qwen3-embedding:0.6b` 经 11434 调用 PASS（dim 1024、keep_alive=0 注入、runner ≤1s 释放）
- Image 调度回归 PASS
- 6 个 chat 模型与 8b/nomic embedding、reranker：**该轮也未逐一实测**，仍属本轮待测项

---

## 4. 磁盘上的 Qwen3.5-9B（文档记录，非本轮核验）

`reports/SERVER_MODEL_SERVICE_AUDIT.md`（2026-09-25 盘点）记录 `/data/vllm/Qwen3.5-9B` = 19G 存在；`reports/UNIFIED_MODEL_STAGING.md` 记录其后 11 个模型目录原样未动。**本轮未做 `ls` / `config.json` 实读**，`QWEN35_WEIGHT_PRESENT` 本轮无法判定。

---

## 5. Changes made

**NONE**（服务器未连接，零服务端操作；本地仅新增本报告与协调文件更新）。

## 6. Blocking issues

**NETWORK_BLOCKED** — 执行机到 SERVER_IP 网段无路由。需恢复原网络环境（同一内网/VPN）后重新执行本任务；任务书允许网络恢复后从 §1 重新开始。
