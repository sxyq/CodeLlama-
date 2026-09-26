"""Qwen-Image-2.1 lifecycle: lazy load + GPU lock + idle unload + GPU wait.

Design rules (staging rules):
- Import of this module MUST NOT load the model or touch the GPU.
- torch / diffusers are imported lazily inside load().
- GPU admission is VRAM-budget based (free VRAM vs request budget + safety
  margin), NOT "ollama must be empty": a resident embedding model is fine
  while the budget still fits. The cross-service gpu.lock (Image <-> Zrald)
  is a separate condition inside the same wait loop.
- Requests failing admission wait in WAITING_FOR_GPU (no gpu.lock held),
  retrying every GPU_WAIT_POLL_SECONDS until IMAGE_GPU_WAIT_TIMEOUT_SECONDS
  -> GpuWaitTimeout (503 GPU_WAIT_TIMEOUT). Normal queuing never busy-fails.
- Cross-service GPU lease: state/gpu.lock via OS-level flock (atomic, no create-then-check race).
- Idle > IDLE_TIMEOUT seconds -> automatic unload (never while inference is running).
"""
from __future__ import annotations

import fcntl
import gc
import math
import os
import subprocess
import threading
import time
from pathlib import Path

MODEL_PATH = "/data/vllm/ImageModel/Qwen-Image-2.1"
GPU_LOCK_PATH = Path("/home/syy/ai-serving/state/gpu.lock")
IDLE_TIMEOUT = int(os.environ.get("IMAGE_IDLE_TIMEOUT", "600"))  # seconds, default 600
GPU_WAIT_TIMEOUT = int(os.environ.get("IMAGE_GPU_WAIT_TIMEOUT_SECONDS", "900"))
GPU_WAIT_POLL_SECONDS = float(os.environ.get("IMAGE_GPU_WAIT_POLL_SECONDS", "3"))
GPU_SAFETY_MARGIN_MIB = int(os.environ.get("IMAGE_GPU_SAFETY_MARGIN_MIB", "3072"))
# Qwen-Image-2.1 samples guidance-free by default (true_cfg_scale=1); a
# non-empty negative prompt only takes effect with CFG enabled. 4.0 matches
# the Qwen-Image family's guidance convention.
TRUE_CFG_SCALE = 4.0


def estimate_gpu_budget_mib(width: int, height: int, ref_count: int = 0,
                            n: int = 1) -> int:
    """Expected peak VRAM of one request in MiB (calibrated on this A6000):

    t2i   1MP=17316, t2i 4.19MP=33700, t2i 1MP n=4=30926
    edit  1MP refs 1/2/3/4/5 = 20578/21712/24284/28614/31414
    edit  5ref 4.19MP=41372
    """
    mp = (width * height) / 1_000_000.0
    if ref_count <= 0:
        base = 12180 + 5136 * mp
        if n > 1:
            base += (n - 1) * 4500
        return int(base)
    base = 17316 + ref_count * 2900  # 1MP edit curve
    base += max(0.0, mp - 1.0) * 3400  # marginal beyond 1MP for edits
    return int(base)


class GpuBusy(Exception):
    """Raised when admission fails right now (VRAM budget or gpu.lock)."""


class GpuWaitTimeout(Exception):
    """Raised when admission never succeeds within IMAGE_GPU_WAIT_TIMEOUT_SECONDS."""

    def __init__(self, waited_s: float, last_reason: str):
        self.waited_s = waited_s
        self.last_reason = last_reason
        super().__init__(f"waited {waited_s:.1f}s for GPU: {last_reason}")


class InferenceBusy(Exception):
    """Raised when unload is refused because an inference is running."""


class ModelManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Held across ensure_loaded + pipeline call + result encoding.
        # unload()/idle watcher try it non-blocking: busy -> refuse, never
        # tear down the pipeline, empty_cache, or release gpu.lock mid-run.
        self._inference_lock = threading.Lock()
        self._pipeline = None
        self.loaded = False
        self.last_used: float = 0.0
        self._watcher_started = False
        self.last_load_seconds: float | None = None
        self._lease_fd: int | None = None
        self.waiting_for_gpu = False  # True while >=1 request is in WAITING_FOR_GPU

    # ---------- GPU admission (VRAM budget, not "ollama empty") ----------
    @staticmethod
    def _gpu_admission(budget_mib: int) -> None:
        """Allow iff free VRAM for this process >= budget + safety margin.

        others = every compute process except this pid (ollama runner, zrald
        llama-server, desktop). Our own residual context is reusable and is
        not counted against us. Raises GpuBusy with the reason otherwise.
        """
        try:
            gpu_csv = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5).stdout.strip()
            apps_out = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5).stdout
        except Exception as e:
            raise GpuBusy(f"gpu query failed: {e}")
        gpu_out = [x.strip() for x in gpu_csv.split(",") if x.strip()]
        if len(gpu_out) < 2:
            raise GpuBusy(f"gpu query returned no data: {gpu_csv!r}")
        total_mib, _used_mib = int(gpu_out[0]), int(gpu_out[1])
        others = 0
        me = os.getpid()
        for line in apps_out.strip().splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                pid, mem = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            if pid != me:
                others += mem
        free_for_us = total_mib - others
        need = budget_mib + GPU_SAFETY_MARGIN_MIB
        if free_for_us < need:
            raise GpuBusy(
                f"vram admission failed: free_for_us={free_for_us}MiB "
                f"< budget={budget_mib}MiB + margin={GPU_SAFETY_MARGIN_MIB}MiB "
                f"(others={others}MiB)")

    def _acquire_gpu_lock(self) -> None:
        """Atomic OS-level lease: flock(LOCK_EX|LOCK_NB) on a STABLE file.

        No create-then-check race: the kernel arbitrates exclusively.
        The file is never unlinked (unlink would break inode stability).
        """
        GPU_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(GPU_LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o664)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            try:
                holder = GPU_LOCK_PATH.read_text().strip()
            except Exception:
                holder = "?"
            os.close(fd)
            raise GpuBusy(f"gpu lease held by [{holder}]")
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()} image-service {time.time()}\n".encode())
        self._lease_fd = fd

    def _release_gpu_lock(self) -> None:
        fd = getattr(self, "_lease_fd", None)
        if fd is None:
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
            self._lease_fd = None

    # ---------- lifecycle ----------
    def ensure_loaded(self, budget_mib: int) -> None:
        """Admission -> gpu.lock -> re-admission -> (lazy) load.

        Raises GpuBusy when VRAM budget or the cross-service lock is not
        available right now; never holds gpu.lock while merely waiting.
        """
        with self._lock:
            self._gpu_admission(budget_mib)
            if self.loaded and self._pipeline is not None:
                self.last_used = time.time()
                return
            t_load0 = time.time()
            self._acquire_gpu_lock()
            # --- post-lease re-check (close the check-then-load race) ---
            try:
                self._gpu_admission(budget_mib)
            except GpuBusy:
                self._release_gpu_lock()
                raise
            # Lazy heavy imports: module import stays GPU-free
            try:
                import torch
                from diffusers import DiffusionPipeline

                pipe = DiffusionPipeline.from_pretrained(
                    MODEL_PATH,
                    torch_dtype=torch.bfloat16,
                    local_files_only=True,
                )
                pipe.enable_model_cpu_offload()  # BF16 + CPU offload
            except Exception:
                # never leak the GPU lock on a failed load
                self._release_gpu_lock()
                raise
            self._pipeline = pipe
            self.loaded = True
            self.last_used = time.time()
            self.last_load_seconds = time.time() - t_load0
            print(f"[model_manager] loaded in {self.last_load_seconds:.2f}s", flush=True)
            self._start_watcher()

    def ensure_loaded_waiting(self, budget_mib: int,
                              timeout_s: int | None = None) -> float:
        """WAITING_FOR_GPU loop: retry admission until allowed or timeout.

        Returns seconds spent waiting (0 when admitted immediately).
        Raises GpuWaitTimeout on timeout (queue slot is released by caller).
        Sets self.waiting_for_gpu while blocked so /status can show it.
        """
        timeout_s = GPU_WAIT_TIMEOUT if timeout_s is None else timeout_s
        t0 = time.time()
        deadline = t0 + timeout_s
        entered = False
        last_reason = "not admitted"
        while True:
            try:
                self.ensure_loaded(budget_mib)
                waited = time.time() - t0
                if entered:
                    self.waiting_for_gpu = False
                    print(f"[gpu-wait] admitted after {waited:.1f}s "
                          f"(budget={budget_mib}MiB)", flush=True)
                return waited
            except GpuBusy as e:
                last_reason = str(e)
                if not entered:
                    entered = True
                    self.waiting_for_gpu = True
                    print(f"[gpu-wait] WAITING_FOR_GPU budget={budget_mib}MiB "
                          f"timeout={timeout_s}s reason: {last_reason}", flush=True)
                if time.time() >= deadline:
                    self.waiting_for_gpu = False
                    waited = time.time() - t0
                    print(f"[gpu-wait] TIMEOUT after {waited:.1f}s "
                          f"reason: {last_reason}", flush=True)
                    raise GpuWaitTimeout(waited, last_reason)
                time.sleep(GPU_WAIT_POLL_SECONDS)

    @staticmethod
    def _cfg_kwargs(negative_prompt: str | None) -> dict:
        """negative_prompt only works when true_cfg_scale > 1 (pipeline rule)."""
        if negative_prompt:
            return {"negative_prompt": negative_prompt, "true_cfg_scale": TRUE_CFG_SCALE}
        return {}

    def generate(self, prompt: str, n: int, size: str,
                 negative_prompt: str | None = None,
                 seed: int | None = None,
                 steps: int | None = None) -> tuple[list[bytes], float]:
        """Returns (png_bytes, inference_seconds).

        The inference guard covers ensure_loaded -> pipeline call -> PNG
        encoding, so unload can never interleave with a running generation.
        """
        import io
        import torch
        width, height = (int(x) for x in size.lower().split("x"))
        budget = estimate_gpu_budget_mib(width, height, ref_count=0, n=n)
        with self._inference_lock:
            self.ensure_loaded_waiting(budget)
            generator = None
            if seed is not None:
                generator = torch.Generator(device="cpu").manual_seed(seed)
            kwargs: dict = dict(
                prompt=prompt,
                width=width, height=height, num_images_per_prompt=n,
                **self._cfg_kwargs(negative_prompt),
            )
            if steps:
                kwargs["num_inference_steps"] = steps
            if generator is not None:
                kwargs["generator"] = generator
            t0 = time.time()
            result = self._pipeline(**kwargs)
            elapsed = time.time() - t0
            self.last_used = time.time()
            import PIL.Image  # noqa: F401  (pipeline returns PIL images)
            out: list[bytes] = []
            for img in result.images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                out.append(buf.getvalue())
            return out, elapsed

    def edit(self, image, prompt: str, negative_prompt: str | None = None,
             steps: int | None = None, seed: int | None = None,
             width: int | None = None, height: int | None = None):
        """Image-to-image edit via QwenImage21Pipeline(image=...).

        Official model-card path; only passes parameters that the current
        pipeline signature really supports (no mask / no strength).

        Output size is kept exactly at (width, height) of the main image:
        the pipeline floors dims to a multiple of 16, so we ceil up for it
        and crop back.

        `image` is a single PIL image or an ordered list of PIL images
        (1 = main image, 2..N = references). The pipeline natively accepts
        PipelineImageInput (list) — never a hand-merged contact sheet.

        The inference guard covers ensure_loaded -> pipeline call -> crop +
        PNG encoding, mirroring generate().
        """
        import io
        import torch
        main = image[0] if isinstance(image, list) else image
        ref_count = len(image) if isinstance(image, list) else 1
        target_w = width or main.width
        target_h = height or main.height
        budget = estimate_gpu_budget_mib(target_w, target_h, ref_count=ref_count, n=1)
        with self._inference_lock:
            self.ensure_loaded_waiting(budget)
            pipe_w = math.ceil(target_w / 16) * 16
            pipe_h = math.ceil(target_h / 16) * 16
            kwargs: dict = dict(
                prompt=prompt, image=image,
                width=pipe_w, height=pipe_h,
                **self._cfg_kwargs(negative_prompt),
            )
            if steps:
                kwargs["num_inference_steps"] = steps
            if seed is not None:
                kwargs["generator"] = torch.Generator(device="cpu").manual_seed(seed)
            t0 = time.time()
            result = self._pipeline(**kwargs)
            elapsed = time.time() - t0
            self.last_used = time.time()
            out = []
            for img in result.images:
                if img.size != (target_w, target_h):
                    img = img.crop((0, 0, target_w, target_h))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                out.append((buf.getvalue(), img.width, img.height))
            return out, elapsed

    def unload(self) -> bool:
        """Tear down the pipeline + release gpu.lock.

        Raises InferenceBusy (without touching the pipeline or the lease)
        when an inference holds the guard. The lock is taken non-blocking so
        callers never stall behind a long generation.
        """
        if not self._inference_lock.acquire(blocking=False):
            raise InferenceBusy("image inference is currently running")
        try:
            with self._lock:
                if self._pipeline is None:
                    self.loaded = False
                    self._release_gpu_lock()
                    return False
                self._pipeline = None
                self.loaded = False
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
                self._release_gpu_lock()
                return True
        finally:
            self._inference_lock.release()

    # ---------- idle watcher ----------
    def _start_watcher(self) -> None:
        if self._watcher_started:
            return
        self._watcher_started = True

        def _loop() -> None:
            while True:
                time.sleep(15)
                if not (self.loaded and self.last_used
                        and time.time() - self.last_used > IDLE_TIMEOUT):
                    continue
                try:
                    self.unload()
                except InferenceBusy:
                    # inference running: skip this round, the next tick retries
                    continue

        t = threading.Thread(target=_loop, daemon=True, name="idle-unload")
        t.start()


MANAGER = ModelManager()
