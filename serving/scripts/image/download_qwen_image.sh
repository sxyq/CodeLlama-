#!/bin/bash
# Qwen-Image-2.1 full snapshot downloader (ModelScope first, resume-capable)
set -u
DEST=/data/vllm/ImageModel/Qwen-Image-2.1
REPO=Qwen/Qwen-Image-2.1
REV=master
LOG=/home/syy/ai-serving/logs/image/download.log
mkdir -p "$DEST"
curl -sS --max-time 30 -A "Mozilla/5.0" \
  "https://modelscope.cn/api/v1/models/$REPO/repo/files?Revision=$REV&Recursive=true" \
  -o /tmp/ms_files.json || { echo "FILELIST_FAIL" >> "$LOG"; exit 1; }
python3 - <<PY > /tmp/ms_list.txt
import json
d=json.load(open("/tmp/ms_files.json"))
files=d.get("Data",{}).get("Files") or []
for f in files:
    if (f.get("Type") or "")=="tree": continue
    print(f.get("Path"), f.get("Size") or 0)
PY
total=$(wc -l < /tmp/ms_list.txt)
echo "FILES=$total start=$(date)" >> "$LOG"
n=0
while read -r path size; do
  n=$((n+1))
  rel="$path"
  mkdir -p "$DEST/$(dirname "$rel")"
  url="https://modelscope.cn/api/v1/models/$REPO/repo?FilePath=$path&Revision=$REV"
  if [ -f "$DEST/$rel" ] && [ "$(stat -c%s "$DEST/$rel")" = "$size" ] && [ "$size" != "0" ]; then
    echo "[$n/$total] SKIP(exists) $rel" >> "$LOG"; continue
  fi
  echo "[$n/$total] GET $rel ($size bytes)" >> "$LOG"
  aria2c -x8 -s8 -c --file-allocation=none --auto-file-renaming=false --retry-wait=5 --max-tries=10 --timeout=60 \
    --dir="$DEST/$(dirname "$rel")" --out="$(basename "$rel")" "$url" >> "$LOG" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then echo "[$n/$total] FAIL rc=$rc $rel" >> "$LOG"; fi
done < /tmp/ms_list.txt
echo "DONE $(date)" >> "$LOG"
