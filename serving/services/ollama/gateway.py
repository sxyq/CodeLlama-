#!/usr/bin/env python3
"""Ollama GPU Gateway — strict Image<->Ollama serialisation entry point.

Listens on the PUBLIC Ollama address (0.0.0.0:11434) and relays to the
Ollama backend moved to loopback (127.0.0.1:11435), so every existing LAN
client keeps using the same IP:PORT while all requests pass the scheduler.

Per-request policy (task GPU-SCHEDULER-STRICT-OLLAMA-IMAGE-001 §9):
- GPU completion endpoints wait while the Image service has an active job
  (image RUNNING or WAITING slot occupied), then forward -> the Ollama GPU
  runner can never load concurrently with Image inference.
- Embed-family requests get keep_alive=0 injected when the client omitted
  it (compat verified: vectors returned, runner unloads immediately).
- All other endpoints relay immediately.

Both legs use Connection: close (one HTTP transaction per connection);
connection-per-request clients are unaffected, keep-alive clients reconnect.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.request

LISTEN_HOST = os.environ.get("GATEWAY_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("GATEWAY_LISTEN_PORT", "11434"))
BACKEND_HOST = os.environ.get("GATEWAY_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("GATEWAY_BACKEND_PORT", "11435"))
IMAGE_STATUS = os.environ.get("GATEWAY_IMAGE_STATUS", "http://127.0.0.1:8011/status")
IMAGE_WAIT_TIMEOUT = int(os.environ.get("GATEWAY_IMAGE_WAIT_TIMEOUT", "1800"))
IMAGE_POLL_S = float(os.environ.get("GATEWAY_IMAGE_POLL", "2"))
# injected default for embed-family when the client omitted keep_alive
EMBED_KEEP_ALIVE = os.environ.get("GATEWAY_EMBED_KEEP_ALIVE", "0")
MAX_HEAD = 64 * 1024
MAX_BODY = int(os.environ.get("GATEWAY_MAX_BODY", str(64 * 1024 * 1024)))

# completion endpoints observed in the7-day journal + standard ollama API
GPU_PATHS = {
    "POST /api/embed",
    "POST /api/embeddings",
    "POST /api/v1/embeddings",
    "POST /v1/embeddings",
    "POST /api/chat",
    "POST /api/generate",
    "POST /api/rerank",
    "POST /v1/chat/completions",
    "POST /v1/completions",
    "POST /api/predict",
}
EMBED_PATHS = {"/api/embed", "/api/embeddings", "/v1/embeddings", "/api/v1/embeddings"}
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


class ImageGate:
    """Tracks whether the Image service occupies the GPU slot."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._state = "idle"
        self._reachable = False
        self._last_poll = 0.0
        self._stop = threading.Event()
        t = threading.Thread(target=self._loop, daemon=True, name="gw-image-gate")
        t.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                with urllib.request.urlopen(IMAGE_STATUS, timeout=3) as r:
                    st = json.load(r)
                running = int(st.get("queue", {}).get("running", 0) or 0) >= 1
                state = (st.get("scheduler") or {}).get("state")
                if state not in ("idle", "queued", "running", "waiting_for_gpu"):
                    state = "running" if running else "idle"
                with self._lock:
                    self._running = running
                    self._state = state
                    self._reachable = True
                    self._last_poll = time.time()
            except Exception:
                with self._lock:
                    self._reachable = False
                    self._running = False
                    self._state = "idle"
            self._stop.wait(IMAGE_POLL_S)

    def image_active(self) -> bool:
        with self._lock:
            return self._running

    def image_state(self) -> str:
        with self._lock:
            return self._state

    def wait_image_idle(self, timeout_s: int) -> float:
        """Block while Image occupies the slot. Returns seconds waited.

        Returns immediately when idle; after any wait, requires one extra
        confirm poll so a just-finished job cannot slip through.
        """
        t0 = time.time()
        ever_waited = False
        while time.time() - t0 < timeout_s:
            if not self.image_active():
                if not ever_waited:
                    return 0.0
                time.sleep(IMAGE_POLL_S)
                if not self.image_active():
                    return time.time() - t0
                continue
            ever_waited = True
            time.sleep(IMAGE_POLL_S)
        raise TimeoutError(f"image slot still busy after {timeout_s}s")


def read_head(conn: socket.socket) -> bytes:
    buf = b""
    conn.settimeout(120)
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk
        if len(buf) > MAX_HEAD:
            raise ValueError("head too large")
    return buf


def parse_head(head: bytes):
    head_only = head.split(b"\r\n\r\n", 1)[0]
    try:
        first, rest = head_only.split(b"\r\n", 1)
    except ValueError:
        raise ValueError("malformed request line")
    parts = first.decode("latin-1").split()
    if len(parts) < 3:
        raise ValueError("malformed request line")
    method, path = parts[0], parts[1]
    headers = {}
    for line in rest.split(b"\r\n"):
        if b":" not in line:
            continue
        k, v = line.split(b":", 1)
        headers[k.decode("latin-1").strip().lower()] = v.decode("latin-1").strip()
    return method, path, headers


def read_body(conn: socket.socket, headers: dict, prelude: bytes) -> bytes:
    """prelude = bytes already read past the header block."""
    if "content-length" in headers:
        n = int(headers["content-length"])
        if n > MAX_BODY:
            raise ValueError("body too large to buffer")
        body = prelude
        while len(body) < n:
            chunk = conn.recv(min(65536, n - len(body)))
            if not chunk:
                break
            body += chunk
        return body[:n]
    if headers.get("transfer-encoding", "").lower() == "chunked":
        raise ValueError("chunked request bodies unsupported")
    return prelude


def is_release_request(body: bytes) -> bool:
    """Explicit keep_alive=0 in the JSON body = unload intent (safe to let
    through while Image is only resource-waiting; it frees the runner)."""
    try:
        obj = json.loads(body.decode("utf-8"))
        return isinstance(obj, dict) and obj.get("keep_alive") == 0
    except Exception:
        return False


def inject_keep_alive(body: bytes) -> bytes:
    if not EMBED_KEEP_ALIVE:
        return body
    try:
        obj = json.loads(body.decode("utf-8"))
        if isinstance(obj, dict) and "keep_alive" not in obj:
            obj["keep_alive"] = json.loads(EMBED_KEEP_ALIVE) \
                if EMBED_KEEP_ALIVE.lstrip("-").isdigit() else EMBED_KEEP_ALIVE
            return json.dumps(obj, ensure_ascii=False).encode("utf-8")
    except Exception:
        return body
    return body


def build_backend_request(method: str, path: str, headers: dict, body: bytes) -> bytes:
    out = [f"{method} {path} HTTP/1.1".encode("latin-1")]
    out.append(f"Host: {BACKEND_HOST}:{BACKEND_PORT}".encode())
    out.append(b"Connection: close")
    for k, v in headers.items():
        if k in HOP_HEADERS or k in ("host", "content-length"):
            continue
        out.append(f"{k}: {v}".encode("latin-1"))
    if body or method in ("POST", "PUT", "PATCH"):
        out.append(f"Content-Length: {len(body)}".encode())
    return b"\r\n".join(out) + b"\r\n\r\n" + body


def relay_response(backend: socket.socket, client: socket.socket) -> None:
    """Read raw response (backend used Connection: close) -> ensure a single
    Connection: close header -> stream the remainder (body, incl. chunked /
    SSE) to client until backend EOF."""
    buf = b""
    backend.settimeout(600)
    while b"\r\n\r\n" not in buf:
        chunk = backend.recv(4096)
        if not chunk:
            break
        buf += chunk
    if b"\r\n\r\n" not in buf:
        client.sendall(buf)
        return
    head, body_part = buf.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    status = lines[0] if lines else b"HTTP/1.1 502 Bad Gateway"
    out_lines = [status]
    for line in lines[1:]:
        lk = line.split(b":", 1)[0].strip().lower()
        if lk in (b"connection", b"keep-alive"):
            continue  # replaced below
        out_lines.append(line)
    out_lines.append(b"Connection: close")
    client.sendall(b"\r\n".join(out_lines) + b"\r\n\r\n" + body_part)
    while True:
        chunk = backend.recv(65536)
        if not chunk:
            break
        client.sendall(chunk)


def error_response(client: socket.socket, status: str, code: str, message: str) -> None:
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    payload = (
        f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode() + body
    try:
        client.sendall(payload)
    except Exception:
        pass


def handle_client(client: socket.socket, addr, gate: ImageGate) -> None:
    key = "?"
    t0 = time.time()
    try:
        head = read_head(client)
        if not head:
            return
        method, path, headers = parse_head(head)
        key = f"{method} {path.split('?', 1)[0]}"
        prelude = head.split(b"\r\n\r\n", 1)[1]

        body = read_body(client, headers, prelude)
        waited = 0.0
        if key in GPU_PATHS:
            bypass = (gate.image_state() == "waiting_for_gpu"
                      and is_release_request(body))
            if bypass:
                print(f"[gw] {time.strftime('%T')} BYPASS_RELEASE {key} "
                      f"(image resource-waiting; release unblocks it)", flush=True)
            else:
                try:
                    waited = gate.wait_image_idle(IMAGE_WAIT_TIMEOUT)
                except TimeoutError:
                    print(f"[gw] {time.strftime('%T')} HOLD_TIMEOUT {key} "
                          f"after {IMAGE_WAIT_TIMEOUT}s", flush=True)
                    error_response(client, "503 Service Unavailable", "IMAGE_GPU_BUSY",
                                   f"image workload still running after {IMAGE_WAIT_TIMEOUT}s")
                    return
                if waited >= IMAGE_POLL_S * 2:
                    print(f"[gw] {time.strftime('%T')} HELD {key} {waited:.1f}s "
                          f"(image slot busy)", flush=True)
        if key.split(" ", 1)[1] in EMBED_PATHS:
            new_body = inject_keep_alive(body)
            if new_body is not body:
                headers = dict(headers)
                headers["content-length"] = str(len(new_body))
                print(f"[gw] {time.strftime('%T')} KEEP_ALIVE_INJECT {key} "
                      f"-> {EMBED_KEEP_ALIVE}", flush=True)
                body = new_body

        backend = socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=10)
        try:
            backend.sendall(build_backend_request(method, path, headers, body))
            relay_response(backend, client)
        finally:
            backend.close()
        print(f"[gw] {time.strftime('%T')} {addr[0]}:{addr[1]} {key} ok "
              f"{(time.time() - t0):.2f}s waited={waited:.1f}s", flush=True)
    except Exception as e:
        print(f"[gw] {time.strftime('%T')} {key} ERROR {e}", flush=True)
        try:
            error_response(client, "502 Bad Gateway", "GATEWAY_ERROR", str(e))
        except Exception:
            pass
    finally:
        try:
            client.close()
        except Exception:
            pass


def main() -> None:
    gate = ImageGate()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(128)
    print(f"[gw] listening on {LISTEN_HOST}:{LISTEN_PORT} -> "
          f"{BACKEND_HOST}:{BACKEND_PORT} (image status: {IMAGE_STATUS})",
          flush=True)
    while True:
        try:
            conn, addr = srv.accept()
        except KeyboardInterrupt:
            break
        threading.Thread(target=handle_client, args=(conn, addr, gate),
                         daemon=True).start()


if __name__ == "__main__":
    main()
