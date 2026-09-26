#!/usr/bin/env bash
# Start the Ollama GPU Gateway (public :11434 -> backend127.0.0.1:11435).
# Stop first: pkill -f "[g]ateway.py"
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_SERVING="$(cd "$HERE/../.." && pwd)"
ENV_FILE="$AI_SERVING/configs/ollama/gateway.local.env"

mkdir -p "$AI_SERVING/logs/ollama"
cd "$AI_SERVING/services/ollama"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec python3 gateway.py >> "$AI_SERVING/logs/ollama/gateway.log" 2>&1
