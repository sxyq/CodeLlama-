# Zrald llama.cpp Service (port 8010)

- 模型: /data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf（Q4_K, qwen35）
- 运行时: /home/syy/ai-serving/runtime/llama.cpp（v0.5.0-dev, commit e85e15c, GGML_CUDA arch86 Release）
- 架构: zrald_lease_manager.py 反向代理 :8010 → llama-server :8012（仅本机）
  - 首个 API 请求 → flock(state/gpu.lock) 统一 GPU lease → 复查 Ollama/nvidia → 启动 llama-server
    (-c 32768 -ngl 999 --alias zrald-qwen3.8-27b-accuracy)
  - lease 在 llama-server 存活期间持续持有（覆盖整个推理期）
  - 空闲 > ZRALD_IDLE_TIMEOUT（默认 600s）→ SIGTERM 优雅停止 → 释放 lease → GPU 归零
  - /health 与 /manager/status 为本地响应，不触发后端、不刷新 idle
- 启动: env/bin 无关，系统 python3 即可
  `python3 /home/syy/ai-serving/services/zrald/zrald_lease_manager.py`
- 日志: logs/zrald/llama-server.log, 管理器 stdout
- 与 Image(8011) 共用 state/gpu.lock（flock 原子互斥）；Ollama 直连客户端不遵守该 lease（见报告）
