# Unified Model Staging Report

任务编号：UNIFIED-MODEL-STAGING-001
时间：2026-09-25 16:58 – 20:09 CST
性质：预部署 / Staging（下载 + 目录 + 配置 + 代码骨架；不停服务、不加载模型、不 Git 提交）
服务器：SERVER_IP_REDACTED（主机名 SERVER_HOSTNAME_REDACTED，用户 syy）

---

## 1. Connection

- SSH PASS（`syy@SERVER_IP_REDACTED`，key 认证，BatchMode）
- date/hostname/whoami/id/uptime 记录于 16:58（k3s-infra-01 / syy / uid=1013 / sudo 组）

## 2. Privilege

```
PRIVILEGE_ESCALATION = SUCCESS
SUDO_AVAILABLE = YES
```

- 验证方式：密码仅经**当前命令 stdin**（heredoc 单行）传给 `sudo -S -v`，随后 `sudo -n id` → uid=0(root)。
- 密码**未**写入任何文件/README/脚本/报告/Git，未出现在 stdout/argv，事后未保存。
- 提权仅用于：创建 `/data/vllm/Zrald-Qwen3.8-27B-v2`、`/data/vllm/ImageModel`（+chown syy、chmod 755）。

## 3. Network（最小验证，未改任何网络配置）

| 项 | 结果 |
|---|---|
| GITHUB_DIRECT | 200 |
| PYPI_DIRECT | 200 |
| HF_MIRROR_DIRECT | 200 |
| HF_DIRECT | 000（timeout，预期内） |
| HF_CLASH（127.0.0.1:7890） | 200 |

代理仅在**当次下载命令**内临时使用（`curl -x` / `aria2c --all-proxy`），无永久 export、未改 `/etc/environment`、`~/.bashrc`、Clash、路由。

## 4. Current services（staging 全程未受影响）

| Port | Service | PID | 状态 |
|---|---|---|---|
| 8000 | vLLM 0.22.0 | 3068143 / EngineCore 3068373（etime 2d18:39，未重启） | RUNNING，health **200** |
| 11434 | Ollama 0.20.7 | 3561（未重启） | RUNNING，api/tags **200** |
| 3000 | Open WebUI | 2124 | RUNNING（监听确认） |
| 8011 | Image Service | — | **STAGED，未启动** |

GPU 终态 43,812 / 49,140 MiB（与任务开始时基线一致），仅 Xorg/gnome-remote-desktop/vLLM::EngineCore，**无新增 GPU 进程**。

## 5. Existing model layout

- `/data/vllm/` 原有 11 个模型目录 +157G HF 缓存：**全部原样，未移动、未改名、未 chown 整树**。
- Ollama internal store `/usr/share/ollama/.ollama`：**未触碰**（未复制 blob、未改 manifests）。

## 6. New directory layout

### 模型（/data/vllm）

```
/data/vllm/
├── <原有 11 模型，原样>
├── Zrald-Qwen3.8-27B-v2/
│   └── zraldqwen3.8-accuracy.gguf        # 16,464,440,224 B
└── ImageModel/
    └── Qwen-Image-2.1/                   # 完整 snapshot，29 文件
```

owner/group/mode：三个新目录均 `syy syy`，`drwxr-sr-x+`（755，继承 setgid+ACL），syy 可写实测通过。

### Serving（/home/syy/ai-serving）

```
ai-serving/
├── README.md
├── configs/{vllm/{README.md,original/*.yaml×7}, ollama/{README.md,Modelfile.zrald-qwen3.8-27b-accuracy}, image/qwen-image-2.1.yaml, video/{README.md,video-service.example.yaml}}
├── services/{image/{server.py,model_manager.py,schemas.py,README.md}, video/README.md}
├── scripts/{common/read_gguf_header.py, common/repair_gguf_holes.py, image/download_qwen_image.sh, image/download_parallel.py, vllm/, ollama/, video/}
├── state/{models.json, service_state.json, README.md}
├── logs/{lifecycle/, image/, video/}
└── env/{image/, video/}                   # 仅目录，本轮不装 Python 环境
```

## 7–10. Zrald 下载

| 项 | 值 |
|---|---|
| ZRALD_REPO | Zrald/Zrald-qwen3.8-27b-v2 |
| ZRALD_REVISION | 34d2b18a06239df60a850db6799879c3e2da9a94（远端 API 查询，非猜测） |
| ZRALD_ACCURACY_FILENAME | **zraldqwen3.8-accuracy.gguf** |
| ZRALD_REMOTE_SIZE | 16,464,440,224 B |
| Local path | /data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf |
| 仓库其他文件 | balance 10.9GB / compressed 9.8GB（未下载）；无需额外 tokenizer/config 小文件 |
| Download source | **HF_MIRROR（主体）+ CLASH（尾段与修补）** |
| Download status | **SUCCESS** |

### 完整性验证

```
SHA256(local)  = 322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482
SHA256(LFS oid)= 322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482   MATCH
file(1) magic = GGUF v3；非 HTML / 非 LFS pointer / 无 .incomplete / 尺寸精确
```

（LFS oid 来源：`/raw/<rev>/...` pointer 文件 `oid sha256:...` + API tree `lfs.oid`，两处一致。）

### 下载过程实录（经验记录）

1. hf-mirror 单连接 36 KB/s → aria2 ×16 爆发至 ~613 MB/s。
2. 随后被限速（0–51 KB/s）；停止 aria2 时文件 15.60GB，**内含 15 处零字节空洞（14.41GB）**（分段未写满）。
3. 经 Clash 按字节范围补尾 859MB 后 SHA 仍不匹配 → 零字节扫描定位空洞 → 4 线程经 Clash 逐洞修补（断点续传+重试）→ 仍差边界 → 诊断发现**空洞前缘的混合块残留 18KB–978KB 尾随零**（共 ~5.6MB）→ 精确补拉 15 段 → **SHA256 全匹配**。
4. 修补工具已沉淀：`scripts/common/repair_gguf_holes.py`（扫描/修补/校验一体）。

## 11. Zrald GGUF metadata（只读 header，未加载模型）

| 字段 | 值 |
|---|---|
| magic / version | GGUF / **3** |
| tensor_count | 866 |
| kv_count | 50 |
| general.architecture | **qwen35** |
| general.name | Qwen3.8-27B |
| **qwen35.context_length** | **262144** → `NATIVE_CONTEXT_METADATA = 262144` |
| qwen35.block_count | 65 |
| qwen35.embedding_length | 5120 |
| attention.head_count / head_count_kv | 24 / 4 |
| general.file_type | 15（llama.cpp ftype 15 = MOSTLY_Q4_K_M） |
| general.quantization_version | 2 |

工具：`scripts/common/read_gguf_header.py`（stdlib，GGUF 数组头为 u32+u64）。

## 12–15. Qwen-Image-2.1 下载

| 项 | 值 |
|---|---|
| Repository | **ModelScope** Qwen/Qwen-Image-2.1（HF 未使用） |
| Revision | master |
| Local path | /data/vllm/ImageModel/Qwen-Image-2.1 |
| Total size | **33,134,789,599 B**（与 API 文件清单逐字节一致） |
| File count | **29**（API 清单 29，落地 29） |
| Download source | **MODELSCOPE**（cdn-lfs-cn；先单序脚本，中途切 4 并发文件级下载器） |
| Download status | **SUCCESS** |
| Integrity status | PASS：无 `.aria2`/`.tmp`/`.incomplete`/`.part`、无 0 字节文件、`missing_or_mismatch=0` |

### 主要组件（model_index.json）

- pipeline: **QwenImage21Pipeline**（保存者 diffusers 0.37.0.dev0 → 部署期需安装含该类的 diffusers 版本）
- processor: transformers Qwen3VLProcessor
- text_encoder: transformers Qwen3VLForConditionalGeneration（4 分片，17.6GB）
- transformer: diffusers QwenImage21Transformer2DModel（2 分片，14.2GB）
- vae: diffusers AutoencoderKLQwenImage21（1.35GB）
- scheduler: FlowMatchEulerDiscreteScheduler
- 大 safetensors 尺寸已逐一记录（9,968,332,504 / 4,998,056,552 / 4,915,962,464×2 / 4,261,951,904 / 2,704,357,976 / 1,350,989,512）

## 16. Image config

- 路径：`/home/syy/ai-serving/configs/image/qwen-image-2.1.yaml`
- 内容：path=/data/vllm/ImageModel/Qwen-Image-2.1、backend=diffusers、dtype=bfloat16、local_files_only=true、lazy_load=true、cpu_offload=true、port=8011、idle_timeout=600、exclusive_large_model=true、check_ollama_before_load=true
- 本轮**未**创建 venv、**未**启动模型（env/image 仅目录）

## 17. Ollama config

- Modelfile：`/home/syy/ai-serving/configs/ollama/Modelfile.zrald-qwen3.8-27b-accuracy`
  - `FROM /data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf`
  - `PARAMETER num_ctx 32768`（不默认 262144）
- README：alias planned **qwen3.8-27b-zrald-accuracy**、来源/SHA/元数据/流程齐备
- **ollama create executed: NO**；Ollama 服务未重启；internal store 未动

## 18. vLLM snapshot

- 路径：`/home/syy/ai-serving/configs/vllm/original/`（7 个 yaml，保持原名）
- 敏感扫描：命中的均为 `max_num_batched_tokens` 等参数名（非凭据）；7 文件全文此前已通读，无 password/token/secret
- 原配置根 `/home/yuyong/vllm/` **未修改**；本轮明确 DO NOT STOP VLLM（未停）

## 19. Video placeholder

- 目录：configs/video（README + video-service.example.yaml）、services/video（README）、scripts/video、logs/video、env/video 全部 STAGED
- video-service.example.yaml：path TBD / lazy_load true / idle 600 / exclusive GPU / 端口 TBD
- **Video model: NONE**（未下载任何视频模型）

## 20. Disk usage

| 时点 | Free |
|---|---|
| FREE_BEFORE（17:38） | 1.4T（3.5T，60% used） |
| FREE_AFTER_ZRALD | ≈1.4T（16.5GB 内含于该读数；df -h 于下载中期仍 60%） |
| FREE_AFTER_IMAGE（20:09） | **1,395,447,111,680 B ≈ 1.3T（62% used）** |

`du`：Zrald-Qwen3.8-27B-v2 = 16G；ImageModel/Qwen-Image-2.1 = 31G。

## 21. Service health after staging

| 核查项 | 结果 |
|---|---|
| 8000 /health | **200**（监听中） |
| 11434 /api/tags | **200** |
| 3000 | 监听中 |
| vLLM PID 3068143 / 3068373 | 未变化（etime 连续 2d18:39） |
| Ollama PID 3561 | 未变化 |
| GPU used | 43,812 MiB（与 staging 开始时一致） |
| 新增 GPU 进程 | 无 |

## 22. Changes made

- 新建：`/data/vllm/Zrald-Qwen3.8-27B-v2`、`/data/vllm/ImageModel`（+子目录）、`/home/syy/ai-serving/` 全树
- 下载：Zrald Accuracy GGUF（16.46GB，SHA 验证通过）、Qwen-Image-2.1 完整 snapshot（33.13GB，29 文件）
- 写入：配置（vllm snapshot/ollama Modelfile+README/image yaml/video 占位）、服务代码骨架（server.py/model_manager.py/schemas.py/README）、状态登记（models.json/service_state.json/README）、工具脚本（gguf 解析/空洞修补/下载器）、主 README、下载日志
- LOCAL：`serving/` 同步（configs/services/scripts/state/README）；本报告；index.html 仪表盘
- 未 git commit / 未 git push

## 23. Explicitly NOT performed

- **vLLM was NOT stopped**（无 kill/stop/restart；YAML 未改；sleep 未执行）
- **Ollama was NOT restarted**；**ollama create NOT executed**；未删除/移动任何既有 Ollama 模型
- **Qwen-Image was NOT loaded**；Image service NOT started（8011 未监听）；venv NOT installed
- **No model inference performed**（零推理请求；GGUF 仅读 header）
- 未启动任何新大模型到 GPU（GPU 显存与基线完全一致）
- 未改 Open WebUI、CUDA/driver、系统网络、Clash、防火墙、默认路由
- 未删除/移动 `/data/vllm` 既有模型；未写入任何 IP/密码/token/凭据到文件或 Git
- 未 git commit、未 git push

## 遗留与部署期注意

1. Image venv 未装：需 diffusers（含 **QwenImage21Pipeline**，模型由 0.37.0.dev0 保存）+ transformers/accelerate/pillow/fastapi/uvicorn，独立于 vLLM/Ollama 环境。
2. `ollama create qwen3.8-27b-zrald-accuracy -f .../Modelfile.zrald-qwen3.8-27b-accuracy` 留待部署期（会生成第二份 Ollama blob 属预期存储）。
3. 下载过程提示：hf-mirror/xet 存在按流量限速；aria2 多段下载中断后可能产生零字节空洞，**务必以 SHA256 收口**（工具已沉淀）。
4. Qwen-Image 全量 33GB 与 Zrald 16.5GB 已占 ~49.6GB 新增磁盘，剩余 1.3T 充足。
