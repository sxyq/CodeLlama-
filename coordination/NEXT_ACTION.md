# NEXT_ACTION

Updated At: 2026-09-28  
Task: LOCAL-MODEL-UNIFIED-DYNAMIC-SERVING-001

Current Phase:

三级 Serving 策略落地完成 — AWAITING COMMANDER REVIEW

Next Action:

1. Git：分阶段白名单提交
   - `feat: generalize llama cpp model manager`（serving/services/llama-manager、serving/configs/llama-manager、serving/services/ollama/gateway.py）
   - `docs: record local model serving matrix`（reports + coordination）→ push main
2. （可选）LEVEL 3 预案：若未来出现仅 vLLM 可跑的模型，按报告 §7 设计建 `services/vllm-manager/`
3. （可选）Ollama 上游 bug 反馈：gemma2 本地导入 panic（`interface conversion: string → map`）与 Qwen3/Mistral/Starcoder2 架构缺失
4. （可选）恢复 vLLM（需授权）

Flags:

- VLLM_RUNNING = NO / VLLM_DYNAMIC = NOT_NEEDED
- OLLAMA = 14 模型（原 10 完好 + 4 local），入口 :11434 网关（新增 LlamaGate）
- LLAMA_MANAGER :8010 = registry 6 模型，default zrald，idle 600s，flock gpu.lock
- GPU STRICT_SERIAL = Image ∧ Ollama ∧ llama.cpp 三方闭环实测 PASS
- QWEN35 = Ollama registered（文本+视觉 PASS），原 19G 权重未动
- 磁盘 = 可用 1.2T；ConvertedGGUF 28G（F16 已清）
- 禁止：未授权删模型/改原权重/改 /home/yuyong/vllm/改 CUDA/driver/真实 IP 入 Git
