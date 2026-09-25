# vLLM Configs

- original config root: /home/yuyong/vllm （READ ONLY，禁止修改原文件）
- snapshot dir: configs/vllm/original/ （保持原文件名，脱敏检查通过：无 password/token/secret）
- current port: 8000
- current status: RUNNING（本阶段 DO NOT STOP VLLM）
- current served model: codellama-13b-instruct-hf（config: qwen3-5.yaml）
- 启动方式（历史记录，勿执行）: syy tmux `vllm` -> python3.12 -m vllm.entrypoints.cli.main serve --config /home/yuyong/vllm/qwen3-5.yaml

配置清单（original/ 下）：
| file | model path | served name | port |
|---|---|---|---|
| qwen3-5.yaml | /data/vllm/CodeLlama-13b-Instruct-hf/ | codellama-13b-instruct-hf | 8000 |
| codellama13b.yaml | /data/vllm/CodeLlama-13b-Instruct-hf/ | codellama-13b | 8000 |
| codellama7b.yaml | /data/vllm/codellama-7b-instruct-hf/ | codellama-7b | 8000 |
| deepseek.yaml | /data/vllm/deepseek-coder-6.7b-instruct | deepseek-coder-6.7b-instruct | 8000 |
| mistral.yaml | /data/vllm/Mistral-7B-Instruct-v0.2/ | mistral-7b | 8000 |
| gemma.yaml | /data/vllm/gemma-2-9b-it/ | gemma2-9b | 8000 |
| qwen.yaml | /data/vllm/Qwen2.5-Coder-7B-Instruct | qwen2.5-coder-7b-instruct | 8000 |

STAGING NOTE: 本轮不修改任何 vLLM YAML，不停止 vLLM。
