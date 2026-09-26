# NEXT_ACTION

Updated At: 2026-09-27  
Task: IMAGE-GPU-WAIT-QUEUE-AND-MAX-STEPS-001

Current Phase:

GPU WAIT QUEUE + MAX STEPS COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：secret scan → 白名单 add → commit（`feat: add gpu wait queue and extended image quality steps`）→ push main
2. （可选）等待中请求的 Cancel 能力——需 job id/中断传播架构（本轮按§7 记录未实现）
3. （可选）embed `keep_alive=0` / Gateway 收口——消除 OLLAMA_EXTERNAL_RACE（5ref×2K 中途载入竞态），
   需与 CLIENT_IP_REDACTED 属主协调（既有待办）
4. （可选）不同 seed/输入的 steps 构图方差复验（本轮单 seed 下构图随步数非单调，报告§9 已记录）
5. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- WEBUI_8020 = RUNNING（slider1-200 / Ultra120 / 等待GPU徽标 / 提示与预计耗时）
- IMAGE_GPU_WAIT = admission 预算制 + WAITING_FOR_GPU + 900s 超时；queue 含 waiting_for_gpu
- STEPS_PROFILE = 官方40 / Ultra120（plateau）/ max200；STEPS_VRAM_SCALING=MINIMAL
- OLLAMA_EXTERNAL_RACE = STILL_PRESENT（生产路径不碰 Ollama）
- IMAGE_TTL = 1800/300（未改）；QUEUE = 1/8/480（未改）
- 禁止：未授权动 :8010/Ollama/vLLM/CUDA/网络、为测试反复制造 OOM、真实 IP 入 Git
