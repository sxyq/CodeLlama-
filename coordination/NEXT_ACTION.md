# NEXT_ACTION

Updated At: 2026-09-26  
Task: QWEN-IMAGE-MAX-CAPABILITY-AND-UI-PROFILE-001

Current Phase:

MAX CAPABILITY + UI PROFILE COMPLETE — AWAITING COMMANDER REVIEW

Next Action:

1. Git：secret scan → 白名单 add → commit（`feat: enable qwen image full capability profile`）→ push main
2. （可选）embed 客户端 `keep_alive=0` / Gateway 收口——消除5ref+2K OOM 与冷加载窗口依赖
   （需与 CLIENT_IP_REDACTED 属主协调，继承既有待办）
3. （可选）1536×2752+5ref 空闲窗口补测（需 embed 长静默 >5min，看门狗脚本已就绪 `/tmp/idle_ref5.py`）
4. （可选）IAB filechooser 修复后的字面“磁盘上传5张”补测
5. （可选）n（输出数量）与显存关系专项评估（n=4 实测 img 30.9GB 偏高）
6. （可选）恢复 vLLM（需 Commander 授权）

Flags:

- VLLM_RUNNING = NO
- WEBUI_8020 = RUNNING（Model Profile dist）
- IMAGE_CAPABILITY = capability.py 单源：5ref / 2752 / 4.3MP / 1.8 / 16x / 4-24-40
- IMAGE_QUEUE = 1/8/480（未改）
- IMAGE_TTL = 1800/300（未改）
- 禁止：未授权动 :8010/Ollama/vLLM/CUDA/网络、embed 驻留下5ref2K 压测、真实 IP 入 Git
