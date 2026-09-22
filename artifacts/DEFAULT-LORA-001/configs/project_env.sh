# ENV-WORKSPACE-001 project-local environment
# Source this file only for this project shell. Do not put into ~/.bashrc.

export PROJECT_ROOT="$HOME/codellama-lora"
export HF_HOME="$PROJECT_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/cache/huggingface/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/cache/huggingface/transformers"
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
export TMPDIR="$PROJECT_ROOT/cache/tmp"
export TOKENIZERS_PARALLELISM=false

# Prefer project venv when present
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  export PATH="$PROJECT_ROOT/.venv/bin:$PATH"
  export VIRTUAL_ENV="$PROJECT_ROOT/.venv"
fi
