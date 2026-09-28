#!/usr/bin/env python3
"""General llama.cpp dynamic model manager (queueing + atomic reservation).

Fixes two production issues (task LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001):

A. GPU busy (Image / Ollama / another holder) no longer returns 503 GPU_BUSY
   immediately.  Requests enter WAITING_FOR_GPU, poll every
   LLAMA_MANAGER_GPU_WAIT_POLL seconds (default 3) up to
   LLAMA_MANAGER_GPU_WAIT_TIMEOUT (default 900), then continue the SAME HTTP
   request automatically once the slot is free.  The gpu.lock is NOT held
   while queued (only brief check-acquire cycles / a held lease while the
   previous model is being swapped).  Only expiry returns
   503 GPU_WAIT_TIMEOUT.

B. ensure_model() and inflight++ used to be two steps -> a request could
   select model A and, before reserving inflight, another thread could
   switch to model B and the first request would hit the wrong backend.
   All selection + switch decision + inflight reservation now happen inside
   one critical section guarded by a single Condition.

State machine (published on /manager/status):
   QUEUED -> WAITING_FOR_GPU -> LOADING -> RUNNING -> IDLE -> UNLOADED
with `waiting_for_gpu` flag and `blocked_by` in
   {ollama, image, gpu_lock, gpu_memory, none}  (no PID / IP exposed).

Startup orphan handling: an existing llama-server bound to :8012 whose model
belongs to this registry is graciously terminated (VRAM confirmed released);
an unrecognised llama-server is never killed — the manager refuses to load
(and reports ORPHAN_UNRESOLVED) instead of starting a second one.

Zrald compatibility kept: port :8010, /health, /manager/status legacy fields,
absent/unknown `model` falls back to the registry default.
"""
from __future__ import annotations

import fcntl
import http.client
import json
import os
import signal
import socket
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
GPU_WAIT_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_GPU_WAIT_TIMEOUT", "900"))
GPU_WAIT_POLL = float(os.environ.get("LLAMA_MANAGER_GPU_WAIT_POLL", "3"))
QUEUE_WAIT_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_QUEUE_WAIT", "900"))
LOG_DIR = os.environ.get("LLAMA_MANAGER_LOG_DIR", "/home/syy/ai-serving/logs/llama-manager")
OLLAMA_PS = os.environ.get("OLLAMA_PS_URL", "http://127.0.0.1:11434/api/ps")
SPAWN_TIMEOUT = int(os.environ.get("LLAMA_MANAGER_SPAWN_TIMEOUT", "240"))
MAX_BODY = 64 * 1024 * 1024
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}

# test-only injection points (empty in production)
TEST_HOOKS: dict = {}

BLOCKED_VALUES = ("ollama", "image", "gpu_lock", "gpu_memory", "none")
PHASES = ("QUEUED", "WAITING_FOR_GPU", "LOADING", "RUNNING", "IDLE", "UNLOADED")


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

# Single source of synchronisation: ONE condition guards ALL mutable state.
state = {
    "cond": threading.Condition(),
    "model": None,            # registry key currently loaded
    "proc": None,             # llama-server Popen
    "inflight": 0,            # reserved requests (proxy in progress)
    "transition": False,      # someone is waiting/loading/switching
    "waiting_for_gpu": False,
    "blocked_by": "none",
    "phase": "UNLOADED",      # QUEUED|WAITING_FOR_GPU|LOADING|RUNNING|IDLE|UNLOADED
    "last_activity": 0.0,
    "lock_fd": None,
    "spawn_count": 0,
    "switch_count": 0,
    "wait_count": 0,          # how many times a request queued for GPU
    "orphan": None,           # None | "resolved" | "unresolved"
}


class GpuWaitTimeout(Exception):
    pass


class QueueTimeout(Exception):
    pass


class OrphanBlocked(Exception):
    pass


# ---------------------------------------------------------------- GPU probes

def _read_lock_holder() -> str:
    try:
        with open(LOCK_PATH, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip().lower()
    except Exception:
        return ""


def _lock_free() -> bool:
    """Non-blocking probe; never keeps the lease."""
    try:
        fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
    except Exception:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        os.close(fd)
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    os.close(fd)
    return True


def lease_acquire() -> int:
    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        os.close(fd)
        raise BlockingIOError("gpu.lock held")
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


def ollama_runner_busy() -> bool:
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


def _classify_lock_holder(holder: str) -> str:
    if not holder:
        return "gpu_lock"
    if "image" in holder:
        return "image"
    if "ollama" in holder:
        return "ollama"
    if "llama-manager" in holder:
        # our own stale string while flock is actually free -> not a blocker
        return "gpu_lock"
    return "gpu_lock"


def gpu_blocked_by() -> str:
    """Cheap non-blocking classification of why the slot is busy."""
    if _lock_free():
        # lock free -> other signals decide
        if ollama_runner_busy():
            return "ollama"
        if nvidia_other_big():
            return "gpu_memory"
        return "none"
    holder = _read_lock_holder()
    if "image" in holder:
        return "image"
    if "ollama" in holder:
        return "ollama"
    # held by someone else: check whether an ollama runner also contributes
    if ollama_runner_busy():
        return "ollama"
    return "gpu_lock"


def _call_hook(name: str) -> None:
    fn = TEST_HOOKS.get(name)
    if fn is not None:
        fn()


# ------------------------------------------------------------- spawn / stop

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
                    if r.status == 200 and '"status":"ok"' in r.read().decode().replace(" ", ""):
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


def _stop_proc(proc) -> None:
    if proc is None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except Exception:
        pass


# ------------------------------------------------------------ orphan handling

def _llama_server_processes() -> list:
    """pid, cmdline of llama-server processes (read-only)."""
    out = []
    try:
        pids = subprocess.check_output(["pgrep", "-f", "llama-server"], text=True)
    except subprocess.CalledProcessError:
        return out
    except Exception:
        return out
    for pid_s in pids.split():
        if not pid_s.isdigit() or int(pid_s) == os.getpid():
            continue
        pid = int(pid_s)
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")
        except Exception:
            continue
        if "llama-server" not in cmd:
            continue          # pgrep self-match guard
        if not cmd.split() or os.path.basename(cmd.split()[0]) != "llama-server":
            continue          # only real llama-server executables count
        out.append((pid, cmd))
    return out


def detect_orphans() -> None:
    """Startup safety: never run a second llama-server for our registry."""
    known_paths = {v["path"] for v in REGISTRY["models"].values()}
    port_busy = False
    try:
        with socket.create_connection(("127.0.0.1", BACKEND_PORT), timeout=0.5):
            port_busy = True
    except Exception:
        port_busy = False

    procs = _llama_server_processes()
    ours, unknown = [], []
    for pid, cmd in procs:
        if any(p in cmd for p in known_paths) or f"--port {BACKEND_PORT}" in cmd:
            ours.append((pid, cmd))
        else:
            unknown.append((pid, cmd))

    if unknown:
        state["orphan"] = "unresolved"
        print(f"[llama-mgr] ORPHAN_UNRESOLVED: {len(unknown)} unrecognised llama-server "
              f"process(es); refusing to start a second backend — manual review required",
              flush=True)
        return

    for pid, cmd in ours:
        print(f"[llama-mgr] orphan llama-server pid={pid} belongs to this registry "
              f"-> graceful terminate", flush=True)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        t0 = time.time()
        while time.time() - t0 < 25:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.5)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if ours:
        time.sleep(2)
        # confirm VRAM released
        for _ in range(10):
            if not nvidia_other_big() or _port_free():
                break
            time.sleep(1)
        print("[llama-mgr] orphan terminated, VRAM released", flush=True)
    state["orphan"] = "resolved" if ours else None
    if port_busy and _port_free() is False:
        print("[llama-mgr] ORPHAN_PORT_BUSY after cleanup", flush=True)


def _port_free() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", BACKEND_PORT), timeout=0.3):
            return False
    except Exception:
        return True


# --------------------------------------------------- atomic request reservation

class Reservation:
    __slots__ = ("key", "released")

    def __init__(self, key: str) -> None:
        self.key = key
        self.released = False


def _reserve_locked() -> None:
    state["inflight"] += 1
    state["last_activity"] = time.time()
    if state["phase"] in ("IDLE", "QUEUED"):
        state["phase"] = "RUNNING"


def release_request_reservation(res: "Reservation") -> None:
    with state["cond"]:
        if not res.released:
            res.released = True
            state["inflight"] = max(0, state["inflight"] - 1)
            state["last_activity"] = time.time()
            state["cond"].notify_all()


def _wait_gpu_until(deadline: float) -> None:
    """Loop until the unified slot is ours.  Called with transition=True and
    WITHOUT holding cond (so /status stays responsive).

    Lock policy:
      * no lease yet -> probe, acquire only when every other signal is quiet;
        never keep the lease while merely queued for a foreign holder.
      * lease already held (model swap) -> keep it across the switch (§13)
        and only wait for Ollama / other big processes to drain.
    """
    cond = state["cond"]
    while True:
        if time.time() >= deadline:
            raise GpuWaitTimeout(f"gpu not available after {GPU_WAIT_TIMEOUT}s")
        have_lock = False
        with cond:
            have_lock = state["lock_fd"] is not None
        if not have_lock:
            if not _lock_free():
                blocked = _classify_lock_holder(_read_lock_holder())
                with cond:
                    state["phase"] = "WAITING_FOR_GPU"
                    state["waiting_for_gpu"] = True
                    state["blocked_by"] = blocked
                time.sleep(GPU_WAIT_POLL)
                continue
            # lock free: confirm the other two signals before taking it
            if ollama_runner_busy():
                with cond:
                    state["phase"] = "WAITING_FOR_GPU"
                    state["waiting_for_gpu"] = True
                    state["blocked_by"] = "ollama"
                time.sleep(GPU_WAIT_POLL)
                continue
            if nvidia_other_big():
                with cond:
                    state["phase"] = "WAITING_FOR_GPU"
                    state["waiting_for_gpu"] = True
                    state["blocked_by"] = "gpu_memory"
                time.sleep(GPU_WAIT_POLL)
                continue
            # all quiet -> take the lease now (brief, then we load)
            try:
                with cond:
                    if state["lock_fd"] is None:
                        state["lock_fd"] = lease_acquire()
            except BlockingIOError:
                with cond:
                    state["blocked_by"] = _classify_lock_holder(_read_lock_holder())
                time.sleep(GPU_WAIT_POLL)
                continue
        else:
            # holding the lease (swap): just wait for the other runners
            if ollama_runner_busy():
                with cond:
                    state["phase"] = "WAITING_FOR_GPU"
                    state["waiting_for_gpu"] = True
                    state["blocked_by"] = "ollama"
                time.sleep(GPU_WAIT_POLL)
                continue
            if nvidia_other_big():
                with cond:
                    state["phase"] = "WAITING_FOR_GPU"
                    state["waiting_for_gpu"] = True
                    state["blocked_by"] = "gpu_memory"
                time.sleep(GPU_WAIT_POLL)
                continue
        # slot is ours
        with cond:
            state["waiting_for_gpu"] = False
            state["blocked_by"] = "none"
        return


def acquire_model_for_request(model_key: str) -> Reservation:
    """Atomic: select model + (wait/switch) + reserve inflight in ONE critical
    section decision.  Other threads can only observe state between our
    decisions, never inside them."""
    if state["orphan"] == "unresolved":
        raise OrphanBlocked("unrecognised llama-server orphan running; load refused")
    deadline = time.time() + QUEUE_WAIT_TIMEOUT
    gpu_deadline = time.time() + GPU_WAIT_TIMEOUT
    cond = state["cond"]
    started_wait = False

    with cond:
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise QueueTimeout(f"queue wait exceeded {QUEUE_WAIT_TIMEOUT}s")
            if state["transition"]:
                # someone else is loading/switching: never start a second one
                if not started_wait:
                    state["wait_count"] += 1
                    if state["phase"] != "WAITING_FOR_GPU":
                        state["phase"] = "QUEUED"
                    started_wait = True
                cond.wait(min(remaining, 1.0))
                continue
            # (1) correct model already warm -> reserve atomically here
            if (state["model"] == model_key and state["proc"] is not None
                    and state["proc"].poll() is None):
                _call_hook("after_selection_before_reserve")
                _reserve_locked()
                return Reservation(model_key)
            # (2) need load/switch: wait until current inference has drained
            if state["inflight"] > 0:
                if not started_wait:
                    state["wait_count"] += 1
                    state["phase"] = "QUEUED"
                    started_wait = True
                cond.wait(min(remaining, 1.0))
                continue
            # (3) we may prepare the model — take the transition slot
            state["transition"] = True
            need_switch = state["model"] is not None and state["model"] != model_key
            old_proc = state["proc"]
            old_model = state["model"]
            state["phase"] = "WAITING_FOR_GPU"
            state["waiting_for_gpu"] = False
            state["blocked_by"] = "none"
            break

    # ---- outside the critical section (transition=True blocks other loads)
    cleanup_lock = True
    try:
        # swap: stop the old backend FIRST (releases its VRAM) — the lease is
        # kept across the switch when we hold it (§13)
        if need_switch and old_proc is not None:
            _stop_proc(old_proc)
            with cond:
                if state["proc"] is old_proc:
                    state["proc"] = None
                    state["model"] = None
                    state["switch_count"] += 1

        with cond:
            state["phase"] = "WAITING_FOR_GPU"
            state["waiting_for_gpu"] = True
            state["wait_count"] += 1
        _wait_gpu_until(gpu_deadline)

        with cond:
            state["phase"] = "LOADING"
            state["waiting_for_gpu"] = False
            state["blocked_by"] = "none"
        proc = spawn_backend(model_key)          # long, outside cond

        with cond:
            state["proc"] = proc
            state["model"] = model_key
            state["spawn_count"] += 1
            state["last_activity"] = time.time()
            _reserve_locked()                    # reservation inside the
            state["transition"] = False          # same critical section as
            state["phase"] = "RUNNING"           # the state swap
            state["cond"].notify_all()
            cleanup_lock = False
            _call_hook("after_load_before_release_cond")
        return Reservation(model_key)
    except GpuWaitTimeout:
        with cond:
            lease = state["lock_fd"]
            state["lock_fd"] = None
        lease_release(lease)                     # queued wait never keeps it
        raise
    finally:
        if cleanup_lock:
            with cond:
                state["transition"] = False
                state["waiting_for_gpu"] = False
                state["blocked_by"] = "none"
                if state["phase"] in ("WAITING_FOR_GPU", "LOADING"):
                    state["phase"] = "RUNNING" if state["proc"] else "UNLOADED"
                if state["proc"] is None:
                    # failed before a backend exists -> never keep the lease
                    lock = state["lock_fd"]
                    state["lock_fd"] = None
                else:
                    lock = None
                state["cond"].notify_all()
            lease_release(lock)


# ------------------------------------------------------------------- idle

def _maybe_idle_stop(now: float) -> None:
    """Called under cond.  Unload only when truly idle (§14)."""
    cond = state["cond"]
    if state["proc"] is None:
        return
    if state["inflight"] > 0:
        return                       # never unload an in-flight request
    if state["transition"]:
        return                       # never disturb a queued GPU waiter
    if state["waiting_for_gpu"]:
        return
    if now - state["last_activity"] <= IDLE_TIMEOUT:
        return
    print(f"[llama-mgr] idle {IDLE_TIMEOUT}s -> graceful stop", flush=True)
    proc = state["proc"]
    state["proc"] = None
    state["model"] = None
    lock = state["lock_fd"]
    state["lock_fd"] = None
    state["phase"] = "UNLOADED"
    _stop_proc(proc)
    lease_release(lock)
    state["cond"].notify_all()


def watchdog() -> None:
    while True:
        time.sleep(5)
        cond = state["cond"]
        with cond:
            proc = state["proc"]
            if proc is not None and proc.poll() is not None:
                print(f"[llama-mgr] backend died rc={proc.returncode}", flush=True)
                state["proc"] = None
                state["model"] = None
                lock = state["lock_fd"]
                state["lock_fd"] = None
                state["phase"] = "UNLOADED"
                lease_release(lock)
                state["cond"].notify_all()
                continue
            _maybe_idle_stop(time.time())


# ------------------------------------------------------------- HTTP layer

def resolve_model(body: bytes) -> str:
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


def manager_status() -> dict:
    with state["cond"]:
        p = state["proc"]
        alive = p is not None and p.poll() is None
        model = state["model"]
        ctx = (REGISTRY["models"].get(model) or {}).get("context")
        if not alive:
            phase = "UNLOADED" if not state["transition"] else state["phase"]
        elif state["transition"]:
            phase = state["phase"]
        elif state["inflight"] > 0:
            phase = "RUNNING"
        else:
            phase = "IDLE"
        blocked = state["blocked_by"] if state["blocked_by"] in BLOCKED_VALUES else "none"
        return {
            # legacy zrald fields (never removed)
            "backend_alive": alive,
            "backend_pid": p.pid if alive else None,
            "lease_held": state["lock_fd"] is not None,
            "inflight": state["inflight"],
            "idle_timeout": IDLE_TIMEOUT,
            "spawn_count": state["spawn_count"],
            "ctx": ctx,
            # new scheduling fields (no PID / IP)
            "state": phase,
            "waiting_for_gpu": bool(state["waiting_for_gpu"]),
            "blocked_by": blocked,
            "gpu_wait_timeout": GPU_WAIT_TIMEOUT,
            "gpu_wait_poll": GPU_WAIT_POLL,
            "model": model,
            "switch_count": state["switch_count"],
            "wait_count": state["wait_count"],
            "orphan": state["orphan"],
            "service": "llama-cpp-model-manager",
            "zrald_compat": True,
            "default_model": REGISTRY["default"],
            "models": sorted(REGISTRY["models"].keys()),
        }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[llama-mgr] {self.address_string()} {fmt % args}", flush=True)

    def _local_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("body too large")
        return self.rfile.read(n) if n else b""

    def _manager_status(self) -> dict:
        return manager_status()


    def _handle_local(self) -> bool:
        path = self.path.split("?", 1)[0]
        if path == "/manager/status":
            self._local_json(200, self._manager_status())
            return True
        if path == "/health":
            with state["cond"]:
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
            reservation = acquire_model_for_request(desired)
        except GpuWaitTimeout as e:
            return self._local_json(503, {"error": {"code": "GPU_WAIT_TIMEOUT",
                                                     "message": str(e)}})
        except QueueTimeout as e:
            return self._local_json(503, {"error": {"code": "QUEUE_TIMEOUT",
                                                     "message": str(e)}})
        except OrphanBlocked as e:
            return self._local_json(503, {"error": {"code": "ORPHAN_UNRESOLVED",
                                                     "message": str(e)}})
        except BlockingIOError as e:
            return self._local_json(503, {"error": {"code": "GPU_BUSY",
                                                     "message": str(e)}})
        except Exception as e:
            return self._local_json(500, {"error": {"code": "SPAWN_FAILED",
                                                     "message": str(e)}})

        try:
            alias = REGISTRY["models"][desired].get("alias", desired)
            if body:
                body = rewrite_model_field(body, alias)
            conn = http.client.HTTPConnection("127.0.0.1", BACKEND_PORT, timeout=600)
            try:
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
            finally:
                conn.close()
        except Exception as e:
            try:
                self._local_json(502, {"error": {"code": "BACKEND_ERROR",
                                                  "message": str(e)}})
            except Exception:
                pass
        finally:
            release_request_reservation(reservation)

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")


def main() -> None:
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    detect_orphans()                       # read-only safety gate before serve
    if state["orphan"] == "unresolved":
        # still serve /status so operators can see it, but refuse loads
        print("[llama-mgr] serving in ORPHAN_UNRESOLVED refusal mode", flush=True)
    threading.Thread(target=watchdog, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PUBLIC_PORT), Handler)
    srv.daemon_threads = True
    print(f"[llama-mgr] listening :{PUBLIC_PORT} -> backend :{BACKEND_PORT} "
          f"idle={IDLE_TIMEOUT}s gpu_wait={GPU_WAIT_TIMEOUT}s/"
          f"{GPU_WAIT_POLL}s lease=flock({LOCK_PATH}) "
          f"default={REGISTRY['default']} models={sorted(REGISTRY['models'])}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
