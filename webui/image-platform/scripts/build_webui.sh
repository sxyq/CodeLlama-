#!/usr/bin/env bash
# Build the internal image WebUI (gpt_image_playground) into ../dist.
# Run from webui/image-platform/ on the server.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$HERE/config/models.json"
PRESET="$HERE/config/preset-config.json"

if [ ! -f "$MODELS" ]; then
  echo "build_webui: missing $MODELS (copy config/models.example.json and set real api_base)" >&2
  exit 1
fi

python3 "$HERE/scripts/gen-preset-config.py" "$MODELS" "$PRESET"

cd "$HERE/upstream"
if [ ! -d node_modules ]; then
  npm ci
fi
VITE_DEFAULT_API_URL="$PRESET" npm run build

rm -rf "$HERE/dist"
cp -R "$HERE/upstream/dist" "$HERE/dist"
echo "build_webui: OK -> $HERE/dist"
