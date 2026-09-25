"""Qwen-Image-2.1 lifecycle: lazy load + GPU lock + idle unload.

Design rules (staging contract):
- Import of this module MUST NOT load the model or touch the GPU.
- torch / diffusers are imported lazily inside load().
- Before loading: check Ollama /api/ps; if a large model occupies GPU
  return 503 GPU_BUSY (never kill Ollama runners).
- Cross-service GPU lease: state/gpu.lock via OS-level flock (atomic, no create-then-check race).
- Idle > IDLE_TIMEOUT seconds -> automatic unload.
"""
from __future__ import annotations

import fcntl
import gc
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

MODEL_PATH = "/data/vllm/ImageModel/Qwen-Image-2.1"
GPU_LOCK_PATH = Path("/home/syy/ai-serving/state/gpu.lock")
OLLAMA_PS_URL = "http://127.0.0.1:11434/api/ps"
IDLE_TIMEOUT = int(os.environ.get("IMAGE_IDLE_TIMEOUT", "600"))  # seconds, default 600
OLLAMA_VRAM_BUSY_BYTES = 1_000_000_000  # size_vram above this = GPU busy


class GpuBusy(Exception):
    """Raised when Ollama or another holder occupies the GPU."""


class ModelManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pipeline = None
        self.loaded = False
        self.last_used: float = 0.0
        self._watcher_started = False
        self.last_load_seconds: float | None = None
        self._lease_fd: int | None = None

    # ---------- GPU occupancy ----------
    @staticmethod
    def _ollama_gpu_busy() -> bool:
        try:
            with urllib.request.urlopen(OLLAMA_PS_URL, timeout=3) as r:
                data = json.load(r)
            for m in data.get("models", []):
                if int(m.get("size_vram", 0)) > OLLAMA_VRAM_BUSY_BYTES:
                    return True
        except Exception:
            # Ollama unreachable: do not block, proceed cautiously
            return False
        return False

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

    @staticmethod
    def _nvidia_other_big() -> bool:
        """True when a big GPU consumer other than this process exists."""
        import subprocess
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5).stdout
        except Exception:
            return False
        me = os.getpid()
        for line in out.strip().splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                pid, mem = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            if pid != me and mem > 1024:
                return True
        return False

    # ---------- lifecycle ----------
    def ensure_loaded(self) -> None:
        with self._lock:
            if self.loaded and self._pipeline is not None:
                self.last_used = time.time()
                return
            if self._ollama_gpu_busy():
                raise GpuBusy("ollama has a large model in VRAM")
            t_load0 = time.time()
            self._acquire_gpu_lock()
            # --- post-lease re-checks (close the check-then-load race) ---
            if self._ollama_gpu_busy():
                self._release_gpu_lock()
                raise GpuBusy("ollama loaded a large model after lease")
            if self._nvidia_other_big():
                self._release_gpu_lock()
                raise GpuBusy("another big GPU process appeared after lease")
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

    def generate(self, prompt: str, n: int, size: str,
                 negative_prompt: str | None = None,
                 seed: int | None = None,
                 steps: int | None = None) -> list[bytes]:
        import torch
        self.ensure_loaded()
        width, height = (int(x) for x in size.lower().split("x"))
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(seed)
        kwargs: dict = dict(
            prompt=prompt, negative_prompt=negative_prompt,
            width=width, height=height, num_images_per_prompt=n,
        )
        if steps:
            kwargs["num_inference_steps"] = steps
        if generator is not None:
            kwargs["generator"] = generator
        result = self._pipeline(**kwargs)
        self.last_used = time.time()
        import io
        import PIL.Image  # noqa: F401  (pipeline returns PIL images)
        out: list[bytes] = []
        for img in result.images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            out.append(buf.getvalue())
        return out

    def edit(self, image, prompt: str, negative_prompt: str | None = None,
             steps: int | None = None, seed: int | None = None,
             width: int | None = None, height: int | None = None):
        """Image-to-image edit via QwenImage21Pipeline(image=...).

        Official model-card path; only passes parameters that the current
        pipeline signature really supports (no mask / no strength).
        """
        import io
        import torch
        self.ensure_loaded()
        kwargs: dict = dict(prompt=prompt, image=image)
        if negative_prompt is not None:
            kwargs["negative_prompt"] = negative_prompt
        if steps:
            kwargs["num_inference_steps"] = steps
        if seed is not None:
            kwargs["generator"] = torch.Generator(device="cpu").manual_seed(seed)
        if width and height:
            kwargs["width"] = width
            kwargs["height"] = height
        t0 = time.time()
        result = self._pipeline(**kwargs)
        self.last_used = time.time()
        elapsed = time.time() - t0
        out = []
        for img in result.images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            out.append((buf.getvalue(), img.width, img.height))
        return out, elapsed

    def unload(self) -> bool:
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

    # ---------- idle watcher ----------
    def _start_watcher(self) -> None:
        if self._watcher_started:
            return
        self._watcher_started = True

        def _loop() -> None:
            while True:
                time.sleep(15)
                if (self.loaded and self.last_used
                        and time.time() - self.last_used > IDLE_TIMEOUT):
                    self.unload()

        t = threading.Thread(target=_loop, daemon=True, name="idle-unload")
        t.start()


MANAGER = ModelManager()
