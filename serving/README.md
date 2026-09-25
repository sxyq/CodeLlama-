# AI Serving（统一 Serving 目录 — STAGING）

## MODEL STORAGE: /data/vllm/

- Text（新）: Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf
- Image（新）: ImageModel/Qwen-Image-2.1/（完整 snapshot）
- 既有 11 个模型目录：保持原样，未移动未修改

## SERVICE CONFIG: /home/syy/ai-serving/

configs/{vllm,ollama,image,video} · services/{image,video} · scripts/{common,vllm,ollama,image,video} · state · logs · env/{image,video}

## ORIGINAL VLLM CONFIG: /home/yuyong/vllm/（只读，未修改）

## OLLAMA INTERNAL STORE: /usr/share/ollama/.ollama（只读，未触碰）

## CURRENT SERVICES

| Port | Service | State |
|---|---|---|
| 8000 | vLLM | RUNNING — **本轮 DO NOT MODIFY / DO NOT STOP** |
| 11434 | Ollama | RUNNING — 未重启，未 create 新模型 |
| 3000 | Open WebUI | RUNNING — 未修改 |
| 8011 | Image Service | **NOT STARTED — STAGED ONLY** |

## STAGING 规则

- 本轮只准备：文件/目录/配置/代码骨架/下载/登记。
- 不停止 vLLM、不重启 Ollama、不执行 ollama create、不启动 image 服务、不加载任何新模型到 GPU。
