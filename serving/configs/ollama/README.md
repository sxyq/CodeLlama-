# Ollama Configs（预配置，未导入）

- model alias planned: **qwen3.8-27b-zrald-accuracy**
- source: Zrald/Zrald-qwen3.8-27b-v2（revision 34d2b18a06239df60a850db6799879c3e2da9a94）
- actual GGUF filename: zraldqwen3.8-accuracy.gguf
- local path: /data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf
- SHA256: 322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482（来源 x-linked-etag，下载后本地复核）
- GGUF metadata（来自仓库 API）: architecture=qwen35, context_length=262144
- planned num_ctx = **32768**（A6000 48GB 兼顾 KV cache/并发/稳定性；不默认 262144）
- Ollama internal store: /usr/share/ollama/.ollama（本轮禁止直接修改 blobs/manifests）

Modelfile: Modelfile.zrald-qwen3.8-27b-accuracy

后续 deployment 阶段才执行：
  ollama create qwen3.8-27b-zrald-accuracy -f configs/ollama/Modelfile.zrald-qwen3.8-27b-accuracy

本轮明确：**ollama create NOT EXECUTED**；Ollama 服务未重启。
