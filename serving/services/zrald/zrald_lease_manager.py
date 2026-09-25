#!/usr/bin/env python3
"""Zrald llama.cpp lease manager.

- Public OpenAI-compatible endpoint on :8010 (reverse proxy to llama-server :8012)
- Spawn-on-demand: first API request acquires the UNIFIED GPU lease (flock on
  state/gpu.lock), re-checks Ollama/nvidia, then starts llama-server (ctx 32768).
- Lease is held for the entire time llama-server is alive (covers all inference).
- Idle > ZRALD_IDLE_TIMEOUT (default 600s) -> graceful SIGTERM llama-server
  -> lease released. No kill -9 unless graceful stop fails.
- Local /health never touches the backend (so health polls do not reset idle).
"""
import fcntl
import http.client
import json
import os
import signal
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK_PATH = "/home/syy/ai-serving/state/gpu.lock"
GGUF = "/data/vllm/Zrald-Qwen3.8-27B-v2/zraldqwen3.8-accuracy.gguf"
LLAMA_SERVER = "/home/syy/ai-serving/runtime/llama.cpp/build/bin/llama-server"
BACKEND_PORT = 8012
PUBLIC_PORT = int(os.environ.get("ZRALD_PUBLIC_PORT", "8010"))
IDLE_TIMEOUT = int(os.environ.get("ZRALD_IDLE_TIMEOUT", "600"))
CTX = 32768
OLLAMA_PS = "http://127.0.0.1:11434/api/ps"

state = {
    "proc": None,
    "lock_fd": None,
    "last_activity": 0.0,
    "inflight": 0,
    "mu": threading.Lock(),
    "busy_reason": None,
    "spawn_count": 0,
}


class GpuBusy(Exception):
    pass


def ollama_has_big_model() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_PS, timeout=3) as r:
            data = json.load(r)
        return any(int(m.get("size_vram", 0)) > 1_000_000_000 for m in data.get("models", []))
    except Exception:
        return False


def nvidia_other_big() -> bool:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5).stdout
        self_pid = os.getpid()
        proc_pid = (state["proc"].pid if state["proc"] else -1)
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            pid, mem = int(parts[0]), int(parts[1])
            if pid in (self_pid, proc_pid):
                continue
            if mem > 1024:
                return True
    except Exception:
        return False
    return False


def lease_acquire() -> int:
    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        try:
            holder = open(LOCK_PATH).read().strip()
        except Exception:
            holder = "?"
        os.close(fd)
        raise GpuBusy(f"lease held by [{holder}]")
    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()} zrald-manager {time.time()}\n".encode())
    return fd


def lease_release(fd: int | None) -> None:
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def spawn_backend():
    log = open("/home/syy/ai-serving/logs/zrald/llama-server.log", "ab")
    cmd = [
        LLAMA_SERVER,
        "-m", GGUF,
        "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
        "-c", str(CTX), "-ngl", "999",
        "--alias", "zrald-qwen3.8-27b-accuracy",
    ]
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    # wait for health
    t0 = time.time()
    while time.time() - t0 < 180:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited rc={proc.returncode} (see logs/zrald/llama-server.log)")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=2) as r:
                if r.status == 200:
                    body = r.read().decode()
                    if '"status":"ok"' in body.replace(" ", "") or r.status == 200:
                        return proc
        except Exception:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("llama-server health timeout")


def ensure_backend() -> None:
    with state["mu"]:
        p = state["proc"]
        if p is not None and p.poll() is None:
            state["last_activity"] = time.time()
            return
        # dead or absent -> acquire lease and (re)spawn
        if state["lock_fd"] is None:
            state["lock_fd"] = lease_acquire()   # may raise GpuBusy
        try:
            if ollama_has_big_model():
                raise GpuBusy("ollama has a large model in VRAM")
            if nvidia_other_big():
                raise GpuBusy("another big GPU process is active")
            state["proc"] = spawn_backend()
        except Exception:
            lease_release(state["lock_fd"])
            state["lock_fd"] = None
            raise
        state["last_activity"] = time.time()
        state["spawn_count"] += 1


def stop_backend() -> None:
    with state["mu"]:
        p = state["proc"]
        if p is None:
            return
        state["proc"] = None
        try:
            p.send_signal(signal.SIGTERM)
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()          # graceful failed -> allowed last resort
                p.wait(timeout=5)
        finally:
            lease_release(state["lock_fd"])
            state["lock_fd"] = None
            state["last_activity"] = 0.0
        print(f"[zrald-mgr] backend stopped (pid {p.pid})", flush=True)


def watchdog():
    while True:
        time.sleep(5)
        p = state["proc"]
        if p is None:
            continue
        if p.poll() is not None:      # crashed/exited on its own
            print(f"[zrald-mgr] backend died rc={p.returncode}", flush=True)
            stop_backend()
            continue
        if state["inflight"] > 0:
            continue
        if time.time() - state["last_activity"] > IDLE_TIMEOUT:
            print(f"[zrald-mgr] idle {IDLE_TIMEOUT}s -> graceful stop", flush=True)
            stop_backend()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[zrald-mgr] {self.address_string()} {fmt % args}", flush=True)

    def _local_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method: str):
        if self.path in ("/manager/status",):
            with state["mu"]:
                p = state["proc"]
                alive = p is not None and p.poll() is None
                return self._local_json(200, {
                    "backend_alive": alive,
                    "backend_pid": p.pid if alive else None,
                    "lease_held": state["lock_fd"] is not None,
                    "inflight": state["inflight"],
                    "idle_timeout": IDLE_TIMEOUT,
                    "spawn_count": state["spawn_count"],
                    "ctx": CTX,
                })
        if self.path == "/health":
            with state["mu"]:
                alive = state["proc"] is not None and state["proc"].poll() is None
            return self._local_json(200, {
                "status": "ok", "service": "zrald-llamacpp",
                "backend_alive": alive, "ctx": CTX, "port": PUBLIC_PORT,
            })
        # real API path -> ensure backend (lease + double checks + spawn)
        try:
            ensure_backend()
        except GpuBusy as e:
            return self._local_json(503, {"error": {"code": "GPU_BUSY", "message": str(e)}})
        except Exception as e:
            return self._local_json(500, {"error": {"code": "SPAWN_FAILED", "message": str(e)}})

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        conn = http.client.HTTPConnection("127.0.0.1", BACKEND_PORT, timeout=300)
        try:
            state["inflight"] += 1
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in ("host", "content-length", "connection")}
            if body is not None:
                headers["Content-Length"] = str(len(body))
            conn.request(method, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() in ("transfer-encoding", "content-length", "connection"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            try:
                self._local_json(502, {"error": {"code": "BACKEND_ERROR", "message": str(e)}})
            except Exception:
                pass
        finally:
            conn.close()
            state["inflight"] = max(state["inflight"] - 1, 0)
            state["last_activity"] = time.time()

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")


def main():
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    threading.Thread(target=watchdog, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PUBLIC_PORT), Handler)
    print(f"[zrald-mgr] listening :{PUBLIC_PORT} -> backend :{BACKEND_PORT} "
          f"idle={IDLE_TIMEOUT}s ctx={CTX} lease=flock({LOCK_PATH})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
