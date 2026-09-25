#!/usr/bin/env python3
"""Parallel full-snapshot downloader for ModelScope repos (file-level workers)."""
import json
import os
import subprocess
import sys
import threading
import urllib.request

DEST = "/data/vllm/ImageModel/Qwen-Image-2.1"
REPO = "Qwen/Qwen-Image-2.1"
REV = "master"
LOG = "/home/syy/ai-serving/logs/image/download.log"
WORKERS = 4

def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")

def fetch_list():
    req = urllib.request.Request(
        f"https://modelscope.cn/api/v1/models/{REPO}/repo/files?Revision={REV}&Recursive=true",
        headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    out = []
    for f in (d.get("Data") or {}).get("Files") or []:
        if (f.get("Type") or "") == "tree":
            continue
        out.append((f.get("Path"), int(f.get("Size") or 0)))
    return out

def expected_done(path, size):
    p = os.path.join(DEST, path)
    return os.path.exists(p) and os.path.getsize(p) == size and size > 0

def worker(q, wid):
    while True:
        try:
            path, size = q.pop()
        except IndexError:
            return
        if expected_done(path, size):
            log(f"[w{wid}] SKIP {path}")
            continue
        url = f"https://modelscope.cn/api/v1/models/{REPO}/repo?FilePath={path}&Revision={REV}"
        d = os.path.join(DEST, os.path.dirname(path))
        os.makedirs(d, exist_ok=True)
        log(f"[w{wid}] GET {path} ({size})")
        r = subprocess.run(
            ["aria2c", "-x8", "-s8", "-c", "--file-allocation=none",
             "--auto-file-renaming=false", "--retry-wait=5", "--max-tries=20",
             "--timeout=60", "--dir", d, "--out", os.path.basename(path), url],
            capture_output=True)
        # NOTE: dir arg fixed below
        if r.returncode != 0:
            log(f"[w{wid}] FAIL rc={r.returncode} {path}")
        else:
            ok = expected_done(path, size)
            log(f"[w{wid}] {'DONE' if ok else 'SIZE_MISMATCH'} {path}")

def main():
    files = fetch_list()
    todo = [f for f in files if not expected_done(*f)]
    log(f"PARALLEL start total={len(files)} todo={len(todo)}")
    # biggest first for better balance
    todo.sort(key=lambda x: -x[1])
    q = list(todo)
    lock_free = q  # workers pop from end
    threads = []
    for i in range(WORKERS):
        t = threading.Thread(target=worker, args=(lock_free, i))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    # final verify
    bad = [p for p, s in files if not expected_done(p, s)]
    log(f"PARALLEL done missing_or_mismatch={len(bad)}")
    for p in bad:
        log(f"  MISSING {p}")

if __name__ == "__main__":
    main()
