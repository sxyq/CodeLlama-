#!/usr/bin/env python3
"""Find all-zero holes and re-fetch via proxy with per-hole retry + part resume."""
import hashlib
import os
import queue
import subprocess
import sys
import threading
import time

CH = 1 << 20
PROXY = "http://127.0.0.1:7890"
ATTEMPTS = 5


def scan(path):
    holes, start, off = [], None, 0
    with open(path, "rb") as f:
        while True:
            b = f.read(CH)
            if not b:
                break
            if len(b) == CH and b.count(0) == CH:
                if start is None:
                    start = off
            else:
                if start is not None:
                    holes.append((start, off))
                    start = None
            off += len(b)
        if start is not None:
            holes.append((start, off))
    merged = []
    for h in holes:
        if merged and h[0] <= merged[-1][1] + CH:
            merged[-1] = (merged[-1][0], h[1])
        else:
            merged.append(h)
    return merged


def patch(path, a, part):
    with open(part, "rb") as src, open(path, "r+b") as dst:
        dst.seek(a)
        while True:
            b = src.read(8 << 20)
            if not b:
                break
            dst.write(b)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(32 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def fetch_hole(path, url, a, b):
    part = f"{path}.fixpart.{a}"
    want = b - a
    for attempt in range(1, ATTEMPTS + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have == want:
            break
        if have > want:
            os.unlink(part)
            have = 0
        start = a + have
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "1200", "-x", PROXY,
             "-r", f"{start}-{b-1}", "-o", "-", url],
            stdout=open(part, "ab"), stderr=subprocess.DEVNULL)
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if r.returncode == 0 and have == want:
            break
        print(f"RETRY hole={a} attempt={attempt} rc={r.returncode} have={have}/{want}", flush=True)
        time.sleep(5)
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have != want:
        return False
    patch(path, a, part)
    os.unlink(part)
    return True


def main():
    path, expect, url = sys.argv[1], sys.argv[2], sys.argv[3]
    threads = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    holes = scan(path)
    total = sum(b - a for a, b in holes)
    print(f"HOLES {len(holes)} BYTES {total}", flush=True)
    if not holes:
        s = sha256(path)
        print(f"SHA256={s} MATCH={'YES' if s == expect else 'NO'}", flush=True)
        return 0 if s == expect else 1
    q: queue.Queue = queue.Queue()
    for h in holes:
        q.put(h)
    fails = []

    def worker():
        while True:
            try:
                a, b = q.get_nowait()
            except queue.Empty:
                return
            if fetch_hole(path, url, a, b):
                print(f"OK hole {a}-{b-1}", flush=True)
            else:
                print(f"FAIL hole {a}-{b-1}", flush=True)
                fails.append((a, b))

    ts = [threading.Thread(target=worker) for _ in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    if fails:
        print(f"REMAINING_FAILS {len(fails)}", flush=True)
        return 2
    s = sha256(path)
    ok = s == expect
    print(f"SHA256={s} MATCH={'YES' if ok else 'NO'}", flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
