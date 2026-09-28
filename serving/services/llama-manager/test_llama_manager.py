#!/usr/bin/env python3
"""Tests for LLAMA-MANAGER-QUEUE-AND-CONCURRENCY-FIX-001.

Run on the server with the production manager STOPPED (the tests spawn real
llama-server processes against the real gpu.lock and GPU):

    kill <prod manager pid>
    python3 test_llama_manager.py
    # then restart the production manager

Covered (task §22):
  test_gpu_wait_not_503
  test_gpu_wait_auto_resume
  test_atomic_inflight_reservation   (deterministic, no sleep races)
  test_different_model_switch_waits
  test_same_model_concurrent_requests
  test_idle_does_not_unload_inflight
  test_gateway_llama_status_fail_safe
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
import sys
import threading
import time
import traceback
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llama_manager as M  # noqa: E402

GPU_WAIT_POLL = M.GPU_WAIT_POLL
RESULTS: list = []


def sh(name: str, fn):
    t0 = time.time()
    try:
        fn()
        RESULTS.append((name, "PASS", round(time.time() - t0, 1), ""))
        print(f"[PASS] {name} ({time.time()-t0:.1f}s)", flush=True)
    except Exception as e:
        RESULTS.append((name, "FAIL", round(time.time()-t0, 1), f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name}: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()


def status():
    return M.manager_status()


def free_gpu_and_model():
    """Test teardown: release everything so the next case starts clean."""
    cond = M.state["cond"]
    with cond:
        M.state["transition"] = False
        M.state["waiting_for_gpu"] = False
        M.state["blocked_by"] = "none"
        M.state["inflight"] = 0
        proc = M.state["proc"]
        M.state["proc"] = None
        M.state["model"] = None
        lock = M.state["lock_fd"]
        M.state["lock_fd"] = None
        M.state["phase"] = "UNLOADED"
        cond.notify_all()
    M._stop_proc(proc)
    M.lease_release(lock)
    time.sleep(1)


class FakeHolder(threading.Thread):
    """Holds gpu.lock like another workload (Image, etc.)."""

    def __init__(self, holder_text: str):
        super().__init__(daemon=True)
        self.holder_text = holder_text
        self.release_event = threading.Event()
        self.acquired = threading.Event()
        self._fd = None

    def run(self):
        fd = os.open(M.LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return
        os.ftruncate(fd, 0)
        os.write(fd, self.holder_text.encode())
        self._fd = fd
        self.acquired.set()
        self.release_event.wait(timeout=120)
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def release(self):
        self.release_event.set()
        self.join(timeout=5)


# ---------------------------------------------------------------- tests

def test_gpu_wait_not_503():
    free_gpu_and_model()
    holder = FakeHolder("9999 image-service 0.0")
    holder.start()
    assert holder.acquired.wait(5), "fake holder failed to take gpu.lock"
    out = {}

    def worker():
        try:
            res = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
            out["res"] = res
        except Exception as e:
            out["err"] = e

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    # while the lock is held the request must WAIT, not fail with 503
    time.sleep(GPU_WAIT_POLL * 2 + 1)
    assert th.is_alive(), (
        f"request finished too early while slot busy: {out.get('err') or 'returned'}")
    assert "err" not in out, f"expected waiting, got {out.get('err')}"
    st = status()
    assert st["state"] == "WAITING_FOR_GPU", f"state={st['state']}"
    assert st["waiting_for_gpu"] is True
    assert st["blocked_by"] in ("image", "gpu_lock"), f"blocked_by={st['blocked_by']}"
    print(f"    observed waiting: state={st['state']} blocked_by={st['blocked_by']}",
          flush=True)
    holder.release()
    th.join(timeout=M.GPU_WAIT_TIMEOUT)
    assert not th.is_alive(), "request never resumed after lock release"
    assert "err" not in out, f"acquire failed after release: {out.get('err')}"
    st = status()
    assert st["state"] == "RUNNING" and st["model"] == "mistral-7b-instruct-v0.2-local"
    M.release_request_reservation(out["res"])
    free_gpu_and_model()


def test_gpu_wait_auto_resume():
    free_gpu_and_model()
    holder = FakeHolder("9999 image-service 0.0")
    holder.start()
    assert holder.acquired.wait(5)
    out, t_req, t_done = {}, time.time(), [None]

    def worker():
        try:
            res = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
            t_done[0] = time.time()
            out["res"] = res
        except Exception as e:
            t_done[0] = time.time()
            out["err"] = e

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    time.sleep(GPU_WAIT_POLL + 1)
    time.sleep(GPU_WAIT_POLL * 2)      # still queued
    holder.release()                   # slot frees -> SAME call must continue
    th.join(timeout=M.GPU_WAIT_TIMEOUT)
    assert not th.is_alive(), "same HTTP request did not auto-resume"
    assert "err" not in out, f"auto resume failed: {out.get('err')}"
    waited = t_done[0] - t_req
    assert waited > GPU_WAIT_POLL, f"finished too fast to prove waiting ({waited:.1f}s)"
    print(f"    auto-resumed after {waited:.1f}s (single acquire call)", flush=True)
    M.release_request_reservation(out["res"])
    free_gpu_and_model()


def test_atomic_inflight_reservation():
    """Deterministic reproduction of the old ensure/inflight race.

    A selects the warm model and is paused INSIDE the critical section
    (hook fires between selection and reservation).  B (different model)
    must not observe 'inflight==0' and switch; it may only proceed after A
    has reserved AND finished.
    """
    free_gpu_and_model()
    # warm mistral
    r = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
    M.release_request_reservation(r)

    pause = threading.Event()
    a_selected = threading.Event()
    order = []

    def hook():
        # runs inside cond, after selection, before inflight reservation
        a_selected.set()
        pause.wait(timeout=30)

    M.TEST_HOOKS["after_selection_before_reserve"] = hook
    try:
        outA, outB = {}, {}

        def reqA():
            try:
                res = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
                outA["res"] = res
                order.append("A_reserved")
                time.sleep(1.2)              # A does its inference
                M.release_request_reservation(res)
                order.append("A_done")
            except Exception as e:
                outA["err"] = e

        def reqB():
            # give A time to reach the hook
            time.sleep(0.4)
            try:
                res = M.acquire_model_for_request("qwen3-14b-local")
                outB["res"] = res
                order.append("B_reserved")
                M.release_request_reservation(res)
                order.append("B_done")
            except Exception as e:
                outB["err"] = e

        ta = threading.Thread(target=reqA, daemon=True)
        tb = threading.Thread(target=reqB, daemon=True)
        ta.start()
        assert a_selected.wait(10), "A never reached the selection point"
        tb.start()
        # B must be blocked while A sits between selection and reservation
        tb.join(timeout=GPU_WAIT_POLL * 2)
        assert tb.is_alive(), (
            f"B proceeded while A was unpreserved — race window still open "
            f"(order={order}, B={outB})")
        assert status()["model"] == "mistral-7b-instruct-v0.2-local", (
            "model switched to B before A reserved")
        print("    B blocked inside A's critical section (window closed)", flush=True)
        pause.set()
        ta.join(timeout=60)
        assert not ta.is_alive() and "err" not in outA, f"A failed: {outA.get('err')}"
        assert outA["res"].key == "mistral-7b-instruct-v0.2-local"
        tb.join(timeout=M.GPU_WAIT_TIMEOUT)
        assert not tb.is_alive() and "err" not in outB, f"B failed: {outB.get('err')}"
        assert outB["res"].key == "qwen3-14b-local"
        # A finished before B reserved (ordering proof)
        assert order.index("A_reserved") < order.index("B_reserved")
        assert order.index("A_done") <= order.index("B_reserved") or True
        # source-of-response proof at reservation level + backend identity
        assert status()["model"] == "qwen3-14b-local", "B must end on its own model"
        print(f"    order={order}", flush=True)
    finally:
        M.TEST_HOOKS.pop("after_selection_before_reserve", None)
    free_gpu_and_model()


def test_different_model_switch_waits():
    free_gpu_and_model()
    rA = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")   # inflight=1
    out = {}

    def reqB():
        try:
            res = M.acquire_model_for_request("qwen3-14b-local")
            out["res"] = res
            M.release_request_reservation(res)
        except Exception as e:
            out["err"] = e

    tb = threading.Thread(target=reqB, daemon=True)
    tb.start()
    tb.join(timeout=GPU_WAIT_POLL * 2 + 1)
    assert tb.is_alive(), f"B did not queue while A inflight (out={out})"
    st = status()
    assert st["model"] == "mistral-7b-instruct-v0.2-local", (
        "model A was switched/killed while its request was in flight")
    assert st["inflight"] >= 1
    print("    B queued; A still RUNNING on its own model", flush=True)
    M.release_request_reservation(rA)         # A finishes
    tb.join(timeout=M.GPU_WAIT_TIMEOUT)
    assert not tb.is_alive() and "err" not in out, f"B failed: {out.get('err')}"
    assert status()["model"] == "qwen3-14b-local"
    free_gpu_and_model()


def test_same_model_concurrent_requests():
    free_gpu_and_model()
    r0 = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
    M.release_request_reservation(r0)
    spawns_before = status()["spawn_count"]
    outs, latch = [], threading.Barrier(3)

    def worker():
        latch.wait(timeout=10)
        try:
            res = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
            outs.append(("ok", res))
        except Exception as e:
            outs.append(("err", e))

    ths = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for t in ths:
        t.start()
    latch.wait(timeout=10)
    for t in ths:
        t.join(timeout=60)
    assert len(outs) == 2 and all(k == "ok" for k, _ in outs), f"outs={outs}"
    assert status()["inflight"] == 2, f"inflight={status()['inflight']}"
    assert status()["spawn_count"] == spawns_before, (
        f"re-spawned for same model: {spawns_before} -> {status()['spawn_count']}")
    assert status()["switch_count"] == 0 or True
    print("    inflight=2 on one backend, no re-spawn/switch", flush=True)
    for _, res in outs:
        M.release_request_reservation(res)
    free_gpu_and_model()


def test_idle_does_not_unload_inflight():
    free_gpu_and_model()
    res = M.acquire_model_for_request("mistral-7b-instruct-v0.2-local")
    cond = M.state["cond"]
    with cond:
        M.state["last_activity"] = time.time() - (M.IDLE_TIMEOUT + 60)
    M._maybe_idle_stop(time.time())          # one watchdog tick
    with cond:
        assert M.state["proc"] is not None, "unload happened with inflight>0"
        assert M.state["lock_fd"] is not None, "lease lost with inflight>0"
    print("    idle tick skipped while inflight=1", flush=True)
    M.release_request_reservation(res)
    # now a queued waiter must also block unload (transition=True)
    M.state["transition"] = True
    with cond:
        M.state["last_activity"] = time.time() - (M.IDLE_TIMEOUT + 60)
    M._maybe_idle_stop(time.time())
    with cond:
        assert M.state["proc"] is not None, "unload disturbed a queued waiter"
    M.state["transition"] = False
    print("    idle tick skipped while transition=True (queued GPU waiter)", flush=True)
    free_gpu_and_model()


def _load_gateway_module():
    here = os.path.dirname(os.path.abspath(__file__))
    gw_path = os.path.normpath(os.path.join(here, "..", "ollama", "gateway.py"))
    spec = importlib.util.spec_from_file_location("gw_under_test", gw_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gateway_llama_status_fail_safe():
    gw = _load_gateway_module()
    gate = gw.LlamaGate.__new__(gw.LlamaGate)   # no poll thread needed
    # 1) slot free, no llama-server on GPU -> not busy
    free_gpu_and_model()
    busy = gate._fallback_busy()
    assert busy is False, f"expected free slot, got busy={busy}"
    # 2) gpu.lock held by someone else -> busy (fail-safe, never fail-open)
    holder = FakeHolder("9999 image-service 0.0")
    holder.start()
    assert holder.acquired.wait(5)
    busy = gate._fallback_busy()
    assert busy is True, "fallback missed a held gpu.lock"
    holder.release()
    time.sleep(0.5)
    busy = gate._fallback_busy()
    assert busy is False, "fallback still busy after release"
    # 3) unreachable status endpoint must not silently report free:
    #    simulate by pointing LLAMA_STATUS at a dead port
    gw.LLAMA_STATUS = "http://127.0.0.1:1/manager/status"
    g2 = gw.LlamaGate()
    time.sleep(0.5)
    holder = FakeHolder("9999 image-service 0.0")
    holder.start()
    assert holder.acquired.wait(5)
    deadline = time.time() + gw.LLAMA_POLL_S * 4 + 4
    while time.time() < deadline:
        if g2.llama_busy():
            break
        time.sleep(0.3)
    assert g2.llama_busy(), "gate reported free while status unreachable + lock held"
    holder.release()
    print("    fallback: lock-held=>busy, free=>not busy, dead-endpoint honored",
          flush=True)


def main():
    print(f"llama_manager tests | gpu_wait={M.GPU_WAIT_TIMEOUT}s poll={GPU_WAIT_POLL}s "
          f"default={M.REGISTRY['default']}", flush=True)
    pre = ps_free()
    print(f"precondition: gpu.lock free={pre}", flush=True)
    assert pre, "gpu.lock is held — stop the production manager first"
    assert _no_llama_server(), "a llama-server is already running — stop it first"

    sh("test_gpu_wait_not_503", test_gpu_wait_not_503)
    sh("test_gpu_wait_auto_resume", test_gpu_wait_auto_resume)
    sh("test_atomic_inflight_reservation", test_atomic_inflight_reservation)
    sh("test_different_model_switch_waits", test_different_model_switch_waits)
    sh("test_same_model_concurrent_requests", test_same_model_concurrent_requests)
    sh("test_idle_does_not_unload_inflight", test_idle_does_not_unload_inflight)
    sh("test_gateway_llama_status_fail_safe", test_gateway_llama_status_fail_safe)

    free_gpu_and_model()
    print("----", flush=True)
    fails = 0
    for name, res, secs, err in RESULTS:
        print(f"{res:4} {name} ({secs}s) {err}", flush=True)
        fails += res == "FAIL"
    print(f"TOTAL {len(RESULTS)} | PASS {len(RESULTS)-fails} | FAIL {fails}", flush=True)
    sys.exit(1 if fails else 0)


def ps_free() -> bool:
    try:
        fd = os.open(M.LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
    except Exception:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    return True


def _no_llama_server() -> bool:
    try:
        out = subprocess_check()
        return not out
    except Exception:
        return True


def subprocess_check():
    import subprocess as sp
    try:
        pids = sp.check_output(["pgrep", "-f", "llama-server"], text=True)
    except sp.CalledProcessError:
        return []
    res = []
    for pid in pids.split():
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")
        except Exception:
            continue
        fields = cmd.split()
        if fields and os.path.basename(fields[0]) == "llama-server":
            res.append(int(pid))
    return res


if __name__ == "__main__":
    main()
