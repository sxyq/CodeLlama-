# README.local — 内部图像平台（WebUI + Image API）

任务：IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001

## 结构

```
webui/image-platform/
├── upstream/          # CookSleep/gpt_image_playground @ aa2556df + 本平台补丁（见下）
├── dist/              # 构建产物（gitignore；由 scripts/build_webui.sh 生成）
├── config/
│   ├── models.example.json   # 模型注册表模板（提交）
│   ├── models.json           # 真实注册表（含真实 api_base，gitignore）
│   └── preset-config.json    # 构建时生成（gitignore）
├── scripts/
│   ├── gen-preset-config.py  # models.json -> 上游 preset 配置
│   ├── build_webui.sh        # 生成 preset + npm run build -> dist/
│   └── serve_static.py       # 轻量静态服务（0.0.0.0:8020，无 Docker）
└── README.local.md
```

## Upstream

- UPSTREAM_REPO: CookSleep/gpt_image_playground
- UPSTREAM_COMMIT: aa2556df3f0b2e211645d7fce095bb442bcea059
- UPSTREAM_LICENSE: MIT
- package manager: npm；build: `tsc -b && vite build`

## 本平台对 upstream 的最小功能补丁（P1–P5）

| # | 目的 | 主要文件 |
|---|---|---|
| P1 | 新增 negative_prompt / num_inference_steps / seed 控件并写入请求体 | types.ts, inputParamsPanel.tsx, openaiCompatibleImageApi.ts, persistedState.ts |
| P2 | 尺寸约束 512–2048、64 倍数、预设表重写 | size.ts, SizePickerModal.tsx |
| P3 | 单次输出上限 10→4（对齐后端 n≤4） | paramCompatibility.ts |
| P4 | 禁用 mask 编辑并提示 `Mask editing unsupported by current model.` | store.ts |
| P5 | 队列状态徽标（轮询 `{api_base}/status` 显示 running/pending） | QueueStatusBadge.tsx, InputBar.tsx |

验证基线：`npm ci` / `npm run build` / `npm test`（34 文件 576 用例全绿）。

## 构建与启动（服务器）

```bash
cd $HOME/ai-serving/webui/image-platform
cp config/models.example.json config/models.json   # 首次；填真实 api_base
# 编辑 config/models.json -> api_base = http://<真实IP>:8011/v1
bash scripts/build_webui.sh
nohup python3 scripts/serve_static.py --port 8020 \
  > $HOME/ai-serving/logs/webui/serve.log 2>&1 &
```

WebUI: http://SERVER_IP:8020
Backend: http://SERVER_IP:8011（Image API，见 serving/services/image/README.md）

## 关键约定

- 浏览器直连 :8011，CORS 白名单由后端 `IMAGE_ALLOWED_ORIGINS` 环境变量读取（代码内无真实 IP）。
- 上游 preset 内 `apiKey: "internal-no-auth"` 仅为占位（后端不做认证），非真实凭据。
- 服务器图片只写 `/home/syy/ai-serving/tmp/image-output/`，默认 1800s 后被 cleaner 删除。
- 浏览器本地历史 = IndexedDB（上游默认，BROWSER_LOCAL_HISTORY=ENABLED）；服务器历史 = DISABLED。
- mask 编辑已禁用（当前模型不支持）。

## 更新 upstream

重新拉取新 commit 前，先保存本平台补丁（上表），再套用并跑 `npm run build && npm test`。
