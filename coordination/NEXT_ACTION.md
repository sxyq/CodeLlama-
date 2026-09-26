# NEXT_ACTION

Updated At: 2026-09-27  
Task: GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001

Current Phase:

STRICT OLLAMA/IMAGE SCHEDULER COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：secret scan → 白名单 add → commit（`feat: serialize ollama and image gpu workloads`）→ push main
2. （可选）WebUI profile timeout600 → ≥900，消除长等待时前端先断、服务端孤儿完成的错位（报告§13.1）
3. （可选）等待中请求的 Cancel（需 job id 架构，历轮记录未实现）
4. （可选）运维手册固化：Ollama 释放一律 API keep_alive=0（`ollama stop` CLI 在本服务器404空转）
5. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- OLLAMA_TOPOLOGY = gateway0.0.0.0:11434 → backend127.0.0.1:11435（unit 已改，勿回改）
- STRICT_EXCLUSION = Image: runner空∧lock∧VRAM+3072；网关: Image占槽扣完成类 + 等待态放行释放
- QUEUE_TIMEOUT = 1200 ≥ GPU_WAIT_TIMEOUT = 900
- CUDA_OOM（本轮）= NO
- WEBUI_8020 = RUNNING（等待状态徽标 + 超高质量（实验性）·120）
- 禁止：未授权动 Ollama 模型/systemd 回改、vLLM/Zrald/CUDA/网络、为测试反复制造 OOM、真实 IP 入 Git
