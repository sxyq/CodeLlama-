# NEXT_ACTION

Updated At: 2026-09-26  
Task: IMAGE-WEBUI-QUALITY-SAFETY-001

Current Phase:

QUALITY + INFERENCE SAFETY COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：本轮 secret scan → commit（`fix: align image quality presets and inference lifecycle`）→ push main，结果见 LAST_HANDOFF/最终回复
2. （可选）LAN embed 接入统一 Gateway / 绑定127.0.0.1（需与 CLIENT_IP_REDACTED 属主协调）——
   `qwen3-embedding:8b` 周期驻留决定 Image 冷加载窗口（载入后不受影响）
3. （可选）mask/inpaint 编辑——需 QwenImageEditInpaint 权重（新模型下载，另批授权）
4. （可选）WebUI 上传按钮自动化补测——待 IAB filechooser 路由可用（平台侧 image/image[] 已 curl 实证）
5. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- WEBUI_8020 = RUNNING（dist 已重建：质量三档中文 + 生效步数显示）
- IMAGE_QUALITY_MAP = fast4/medium24/high40，显式优先，双端点统一
- IMAGE_INFERENCE_GUARD = ON（推理中 /unload → 409，watcher 跳过）
- IMAGE_TIMING = queue_wait/load/inference/total（generation_seconds 兼容=inference）
- IMAGE_TEMP_TTL = 1800s/300s（未改动）
- 禁止：未授权下载新模型、动 :8010/Ollama/vLLM/CUDA/网络/Open WebUI、真实 IP 入 Git
