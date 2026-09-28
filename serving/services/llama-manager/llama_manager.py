#!/usr/bin/env python3
"""General llama.cpp dynamic model manager.

Generalized from zrald_lease_manager.py (single hard-coded model) into a
registry-driven manager while keeping the original Zrald :8010 API behaviour.

- Public OpenAI-compatible endpoint (default :8010) -> llama-server :8012
- Model chosen by the OpenAI `model` field; unknown names fall back to the
  registry default (Zrald backward compatibility: legacy clients keep working)
- Spawn-on-demand: first API request acquires the UNIFIED GPU lease
  (flock state/gpu.lock), re-checks Ollama/nvidia, then starts llama-server
- Model switch: request for model B while model A idles -> stop A (lease
  KEPT) -> spawn B; if A is mid-inference the B request queues on the
  condition variable (never kills an in-flight job)
- idle > IDLE_TIMEOUT (600s) -> graceful SIGTERM -> lease released
- Local /health and /manager/status never touch the backend
  (health polls do not reset idle), same contract as the original manager
"""
from __future__ import annotations

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

import yaml

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get(
    "LLAMA_MANAGER_CONFIG",
    "/home/syy/ai-serving/configs/llama-manager/models.yaml",
)
LOCK_PATH = os.environ.get("GPU_LOCK_PATH", "/home/syy/ai-serving/state/gpu.lock")
LLAMA_SERVER = os.environ.get(
    "LLAMA_SERVER_BIN",
    "/home/syy/ai-serving/runtime/llama.cpp/build/bin/llama-server",
)
BACKEND_PORT = int(os.environ.get("LLAMA_MANAGER_BACKEND_PORT", "8012"))
PUBLIC_PORT = int(os.environ.get("LLAMA_MANAGER_PUBLIC_PORT", "8010"))
IDLE_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_IDLE_TIMEOUT", "600"))
LOG_DIR = os.environ.get("LLAMA_MANAGER_LOG_DIR", "/home/syy/ai-serving/logs/llama-manager")
OLLAMA_PS = os.environ.get("OLLAMA_PS_URL", "http://127.0.0.1:11434/api/ps")
SPAWN_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_SPAWN_TIMEOUT", "240"))
QUEUE_WAIT_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_QUEUE_WAIT", "900"))
MAX_BODY = 64 * 1024 * 1024
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


def load_registry() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    models = cfg.get("models") or {}
    if not models:
        raise RuntimeError(f"no models in {CONFIG_PATH}")
    default = cfg.get("default_model")
    if default not in models:
        default = next(iter(models))
    return {
        "default": default,
        "models": models,
        "backend_port": int(cfg.get("backend_port", BACKEND_PORT)),
        "idle_timeout": int(cfg.get("idle_timeout", IDLE_TIMEOUT)),
    }


REGISTRY = load_registry()
BACKEND_PORT = REGISTRY["backend_port"]
IDLE_TIMEOUT = REGISTRY["idle_timeout"]

state = {
    "proc": None,
    "lock_fd": None,
    "model": None,            # registry key currently loaded
    "last_activity": 0.0,
    "inflight": 0,
    "mu": threading.Lock(),
    "cond": threading.Condition(),
    "spawn_count": 0,
    "switch_count": 0,
}


class GpuBusy(Exception):
    pass


class QueueTimeout(Exception):
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
    os.write(fd, f"{os.getpid()} llama-manager {time.time()}\n".encode())
    return fd


def lease_release(fd: int | None) -> None:
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _gpu_admission() -> None:
    """Re-checked before every spawn (lock already held at that point)."""
    if ollama_has_big_model():
        raise GpuBusy("ollama has a large model in VRAM")
    if nvidia_other_big():
        raise GpuBusy("another big GPU process is active")


def spawn_backend(model_key: str):
    spec = REGISTRY["models"][model_key]
    path = spec["path"]
    if not os.path.exists(path):
        raise RuntimeError(f"model file missing: {path}")
    ctx = int(spec.get("context", 8192))
    gpu_layers = spec.get("gpu_layers", 999)
    alias = spec.get("alias", model_key)
    os.makedirs(LOG_DIR, exist_ok=True)
    log = open(os.path.join(LOG_DIR, f"llama-server-{model_key}.log"), "ab")
    cmd = [
        LLAMA_SERVER,
        "-m", path,
        "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
        "-c", str(ctx), "-ngl", str(gpu_layers),
        "--alias", alias,
    ]
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    try:
        while time.time() - t0 < SPAWN_TIMEOUT:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server exited rc={proc.returncode} "
                    f"(see {LOG_DIR}/llama-server-{model_key}.log)")
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=2) as r:
                    if r.status == 200:
                        body = r.read().decode().replace(" ", "")
                        if '"status":"ok"' in body:
                            return proc
            except Exception:
                pass
            time.sleep(0.5)
        proc.terminate()
        raise RuntimeError("llama-server health timeout")
    except Exception:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise


def _spawn_locked(model_key: str) -> None:
    """Spawn model_key while state['mu'] is held; manages the lease."""
    if state["lock_fd"] is None:
        state["lock_fd"] = lease_acquire()      # may raise GpuBusy
    try:
        _gpu_admission()
        state["proc"] = spawn_backend(model_key)
    except Exception:
        lease_release(state["lock_fd"])
        state["lock_fd"] = None
        state["model"] = None
        raise
    state["model"] = model_key
    state["last_activity"] = time.time()
    state["spawn_count"] += 1


def _stop_locked(keep_lease: bool) -> None:
    """Stop llama-server while state['mu'] is held."""
    p = state["proc"]
    state["proc"] = None
    state["model"] = None
    if p is not None:
        try:
            p.send_signal(signal.SIGTERM)
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        finally:
            print(f"[llama-mgr] backend stopped (pid {p.pid})", flush=True)
    if not keep_lease:
        lease_release(state["lock_fd"])
        state["lock_fd"] = None


def ensure_model(model_key: str) -> None:
    """Make sure model_key is loaded and warm; queues behind in-flight jobs."""
    deadline = time.time() + QUEUE_WAIT_TIMEOUT
    with state["mu"]:
        # 1) same model, backend alive -> warm
        p = state["proc"]
        if state["model"] == model_key and p is not None and p.poll() is None:
            state["last_activity"] = time.time()
            return
        # 2) different model or dead backend -> wait for in-flight to drain
        while state["inflight"] > 0:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise QueueTimeout(f"queue wait exceeded {QUEUE_WAIT_TIMEOUT}s")
            with state["cond"]:
                state["cond"].wait(timeout=min(remaining, 5))
        switching = state["proc"] is not None and state["model"] != model_key
        try:
            if state["proc"] is not None:
                # model switch or dead proc: keep the lease across the swap
                _stop_locked(keep_lease=True)
            _spawn_locked(model_key)
        except Exception:
            if switching:
                state["switch_count"] += 1
            raise
        if switching:
            state["switch_count"] += 1
            print(f"[llama-mgr] switched to {model_key}", flush=True)


def watchdog() -> None:
    while True:
        time.sleep(5)
        p = state["proc"]
        if p is None:
            continue
        if p.poll() is not None:
            print(f"[llama-mgr] backend died rc={p.returncode}", flush=True)
            with state["mu"]:
                _stop_locked(keep_lease=False)
            continue
        if state["inflight"] > 0:
            continue
        if time.time() - state["last_activity"] > IDLE_TIMEOUT:
            print(f"[llama-mgr] idle {IDLE_TIMEOUT}s -> graceful stop", flush=True)
            with state["mu"]:
                if state["inflight"] == 0 and state["proc"] is not None \
                        and time.time() - state["last_activity"] > IDLE_TIMEOUT:
                    _stop_locked(keep_lease=False)


def resolve_model(body: bytes) -> str:
    """OpenAI model field -> registry key; unknown/absent -> default (Zrald)."""
    try:
        obj = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        obj = {}
    key = obj.get("model") if isinstance(obj, dict) else None
    if isinstance(key, str) and key in REGISTRY["models"]:
        return key
    return REGISTRY["default"]


def rewrite_model_field(body: bytes, alias: str) -> bytes:
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception:
        return body
    if not isinstance(obj, dict):
        return body
    obj["model"] = alias
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[llama-mgr] {self.address_string()} {fmt % args}", flush=True)

    def _local_json(self, code: int, obj: dict, extra_headers: dict | None = None) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("body too large")
        return self.rfile.read(n) if n else b""

    def _manager_status(self) -> dict:
        with state["mu"]:
            p = state["proc"]
            alive = p is not None and p.poll() is None
            model = state["model"]
            ctx = (REGISTRY["models"].get(model) or {}).get("context")
            return {
                # fields kept verbatim from the original zrald manager
                "backend_alive": alive,
                "backend_pid": p.pid if alive else None,
                "lease_held": state["lock_fd"] is not None,
                "inflight": state["inflight"],
                "idle_timeout": IDLE_TIMEOUT,
                "spawn_count": state["spawn_count"],
                "ctx": ctx,
                # new fields (additive only, legacy clients unaffected)
                "model": model,
                "switch_count": state["switch_count"],
                "service": "llama-cpp-model-manager",
                "zrald_compat": True,
                "default_model": REGISTRY["default"],
                "models": sorted(REGISTRY["models"].keys()),
            }

    def _handle_local(self) -> bool:
        path = self.path.split("?", 1)[0]
        if path in ("/manager/status",):
            self._local_json(200, self._manager_status())
            return True
        if path == "/health":
            with state["mu"]:
                alive = state["proc"] is not None and state["proc"].poll() is None
                model = state["model"]
                ctx = (REGISTRY["models"].get(model) or {}).get("context")
            self._local_json(200, {
                "status": "ok", "service": "llama-cpp-model-manager",
                "zrald_compat": True, "backend_alive": alive,
                "ctx": ctx, "port": PUBLIC_PORT,
                "default_model": REGISTRY["default"],
            })
            return True
        if path in ("/v1/models", "/v1/models/"):
            data = [
                {"id": k, "object": "model", "owned_by": "llama-manager",
                 "path": v.get("path"), "context": v.get("context")}
                for k, v in REGISTRY["models"].items()
            ]
            self._local_json(200, {"object": "list", "data": data})
            return True
        return False

    def _proxy(self, method: str) -> None:
        if self._handle_local():
            return
        body = b""
        if method in ("POST", "PUT", "PATCH"):
            body = self._read_body()
        desired = resolve_model(body)
        try:
            ensure_model(desired)
        except GpuBusy as e:
            return self._local_json(503, {"error": {"code": "GPU_BUSY", "message": str(e)}})
        except QueueTimeout as e:
            return self._local_json(503, {"error": {"code": "QUEUE_TIMEOUT", "message": str(e)}})
        except Exception as e:
            return self._local_json(500, {"error": {"code": "SPAWN_FAILED", "message": str(e)}})

        alias = REGISTRY["models"][desired].get("alias", desired)
        if body:
            body = rewrite_model_field(body, alias)
        conn = http.client.HTTPConnection("127.0.0.1", BACKEND_PORT, timeout=600)
        try:
            with state["cond"]:
                state["inflight"] += 1
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in HOP_HEADERS | {"host", "content-length"}}
            if body:
                headers["Content-Length"] = str(len(body))
            headers["Connection"] = "close"
            conn.request(method, self.path, body=body or None, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() in ("content-length", "connection"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            try:
                self._local_json(502, {"error": {"code": "BACKEND_ERROR", "message": str(e)}})
            except Exception:
                pass
        finally:
            conn.close()
            with state["cond"]:
                state["inflight"] = max(state["inflight"] - 1, 0)
                state["cond"].notify_all()
            state["last_activity"] = time.time()

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")


def main() -> None:
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    threading.Thread(target=watchdog, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PUBLIC_PORT), Handler)
    srv.daemon_threads = True
    print(f"[llama-mgr] listening :{PUBLIC_PORT} -> backend :{BACKEND_PORT} "
          f"idle={IDLE_TIMEOUT}s lease=flock({LOCK_PATH}) "
          f"default={REGISTRY['default']} models={sorted(REGISTRY['models'])}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
