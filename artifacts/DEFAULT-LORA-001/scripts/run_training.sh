#!/usr/bin/env bash
# FORMAL-TRAIN-001 / DEFAULT-LORA-001 launcher
set -uo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/codellama-lora}"
source "$PROJECT_ROOT/configs/project_env.sh"
source "$PROJECT_ROOT/.venv/bin/activate"

export HF_HOME="$PROJECT_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/cache/huggingface/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/cache/huggingface/transformers"
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
export TMPDIR="$PROJECT_ROOT/cache/tmp"
export TOKENIZERS_PARALLELISM=false

EXP_ID="DEFAULT-LORA-001"
RUN_NAME="default_baseline_lora"
CFG="$PROJECT_ROOT/configs/training/default_baseline_lora.yaml"
LOG_DIR="$PROJECT_ROOT/logs/training/${RUN_NAME}"
OUT_DIR="$PROJECT_ROOT/outputs/${RUN_NAME}"
mkdir -p "$LOG_DIR" "$OUT_DIR"

START_TIME_ISO="$(date -Is)"
START_TIME_EPOCH="$(date +%s)"
{
  echo "START_TIME_ISO=$START_TIME_ISO"
  echo "START_TIME_EPOCH=$START_TIME_EPOCH"
  echo "CONFIG=$CFG"
  echo "=== nvidia-smi before ==="
  nvidia-smi
} | tee "$LOG_DIR/timeline.txt"

MON_PID=""
bash "$PROJECT_ROOT/scripts/monitor_gpu.sh" "$LOG_DIR/gpu_monitor.csv" >/dev/null 2>&1 &
MON_PID=$!

set +e
llamafactory-cli train "$CFG" >"$LOG_DIR/train_stdout.log" 2>"$LOG_DIR/train_stderr.log"
TRAIN_EXIT_CODE=$?
set -e
cat "$LOG_DIR/train_stdout.log" "$LOG_DIR/train_stderr.log" > "$LOG_DIR/train_combined.log"

END_TIME_ISO="$(date -Is)"
END_TIME_EPOCH="$(date +%s)"
TOTAL_WALL_SECONDS=$((END_TIME_EPOCH - START_TIME_EPOCH))

kill "$MON_PID" 2>/dev/null || true
wait "$MON_PID" 2>/dev/null || true

{
  echo "END_TIME_ISO=$END_TIME_ISO"
  echo "END_TIME_EPOCH=$END_TIME_EPOCH"
  echo "TOTAL_WALL_SECONDS=$TOTAL_WALL_SECONDS"
  echo "TRAIN_EXIT_CODE=$TRAIN_EXIT_CODE"
  echo "=== nvidia-smi after ==="
  nvidia-smi
} | tee -a "$LOG_DIR/timeline.txt"

set +e
python "$PROJECT_ROOT/scripts/collect_training_metrics.py" \
  --output-dir "$OUT_DIR" \
  --log-dir "$LOG_DIR" \
  --config "$CFG" \
  --timeline "$LOG_DIR/timeline.txt" \
  --report "$PROJECT_ROOT/reports/TRAINING_METRICS.json" \
  --experiment-id "$EXP_ID"
echo "METRICS_EXIT_CODE=$?" >> "$LOG_DIR/timeline.txt"
set -e

exit "$TRAIN_EXIT_CODE"
