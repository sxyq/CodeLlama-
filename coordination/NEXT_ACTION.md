# NEXT_ACTION

Updated At: 2026-09-26  
Task: IMAGE-WEBUI-QUEUE-TEMP-STORAGE-001

Current Phase:

IMAGE WEBUI PLATFORM COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：本轮 secret scan → commit（`feat: deploy internal image webui platform`）→ push，结果见 LAST_HANDOFF/最终回复
2. （可选）LAN embed 接入统一 Gateway / 绑定127.0.0.1（需与 CLIENT_IP_REDACTED 属主协调）——解决
   `qwen3-embedding:8b` 周期驻留导致 Image 冷加载 503 的窗口依赖
3. （可选）mask/inpaint 编辑——需 QwenImageEditInpaint 对应权重（新模型下载，另批授权）
4. （可选）WebUI 上传按钮的自动化验证——待 IAB filechooser 路由可用后补测（平台侧 image/image[] 已 curl 实证）
5. （可选）/unload 推理中拒绝逻辑（本轮观察到并发安全但语义可更严）
6. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- WEBUI_8020 = RUNNING（dist @ aa2556df + P1-P5）
- IMAGE_QUEUE = 1/8/480s，E2E PASS
- IMAGE_TEMP_TTL = 1800s/300s（60s 实测后已恢复）
- CORS = 白名单精确 origin，代码零真实 IP
- BROWSER_LOCAL_HISTORY = ENABLED；SERVER_HISTORY = DISABLED
- 禁止：未授权下载新模型、动 :8010/Ollama/vLLM/CUDA/网络/Open WebUI、真实 IP 入 Git
