#!/usr/bin/env bash
# Start the Qwen-Image-2.1 service (uvicorn) with env from service.local.env.
# Stop first: pkill -f "uvicorn server:app"
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_SERVING="$(cd "$HERE/../.." && pwd)"
ENV_FILE="$AI_SERVING/configs/image/service.local.env"

cd "$AI_SERVING/services/image"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec "$AI_SERVING/env/image/bin/python" -m uvicorn server:app \
  --host 0.0.0.0 --port 8011 >> "$AI_SERVING/logs/image/service.log" 2>&1
