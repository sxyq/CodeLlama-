#!/usr/bin/env bash
# TOKEN-AUDIT-001 runner
set -euo pipefail

source "$HOME/codellama-lora/configs/project_env.sh"
source "$HOME/codellama-lora/.venv/bin/activate"

export PROJECT_ROOT="${PROJECT_ROOT:-$HOME/codellama-lora}"
export HF_HOME="$PROJECT_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/cache/huggingface/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/cache/huggingface/transformers"
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
export TMPDIR="$PROJECT_ROOT/cache/tmp"
export TOKENIZERS_PARALLELISM=false

python "$PROJECT_ROOT/scripts/token_audit.py" \
  --dataset "$PROJECT_ROOT/data/Fine-Tuning.json" \
  --tokenizer /data/vllm/CodeLlama-13b-Instruct-hf \
  --output-dir "$PROJECT_ROOT/reports" \
  --lf-root "$PROJECT_ROOT/LLaMA-Factory" \
  --template llama2
