# Video Configs（预留，仅占位）

- 本轮未选定视频模型、未下载任何视频模型、未安装视频环境。
- 未来候选（仅列举，不代表选择）：Wan / HunyuanVideo / LTX-Video 或其他。
- 该目录是未来视频模型统一配置位置：configs/video/<model>.yaml

设计原则（与 image 一致）：
- model.path: TBD
- runtime.lazy_load: true（启动 != 加载模型；首个请求才加载）
- service.idle_timeout_seconds: 600（空闲自动释放 GPU）
- gpu.exclusive_large_model: true（与 Ollama/Image 共用 GPU 冲突策略）
- 未来 GPU 争用与 image 共用 state/gpu.lock

预留 API：
  GET  /health
  GET  /status
  POST /v1/videos/generations
  POST /unload

示例：video-service.example.yaml
