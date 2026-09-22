#!/usr/bin/env bash
# Log GPU stats every 5s. Failure must not fail training.
OUT="${1:-$HOME/codellama-lora/logs/training/default_baseline_lora/gpu_monitor.csv}"
mkdir -p "$(dirname "$OUT")"
echo "timestamp,utilization.gpu,memory.used,memory.free,temperature.gpu,power.draw" > "$OUT"
while true; do
  ts=$(date -Is)
  row=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free,temperature.gpu,power.draw --format=csv,noheader,nounits 2>/dev/null | head -1)
  if [ -n "$row" ]; then
    echo "$ts,$row" >> "$OUT"
  else
    echo "$ts,,,,," >> "$OUT"
  fi
  sleep 5
done
