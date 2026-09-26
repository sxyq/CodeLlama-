"""Qwen-Image-2.1 serving API (lazy load + GPU lease + queue + TTL outputs).

Start != load: server boots with MODEL_LOADED=false; the pipeline is
loaded lazily on the first queued generation/edit request.

Design notes:
- CORS origins are read from IMAGE_ALLOWED_ORIGINS (no real IP in code).
- Both image endpoints share one ImageQueue (single execution slot).
- Outputs land in temp_output.TEMP_OUTPUT_ROOT and expire after
  IMAGE_OUTPUT_RETENTION_SECONDS (cleaner sweeps at startup + interval).
"""
from __future__ import annotations

import base64
import io
import math
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import capability
from capability import (
    MAX_ASPECT_RATIO,
    MAX_EDGE,
    MAX_PIXELS,
    MAX_REFERENCE_IMAGES,
    MIN_EDGE,
    MULTIPLE_OF,
)
from model_manager import (
    GPU_WAIT_TIMEOUT,
    MANAGER,
    GpuBusy,
    GpuWaitTimeout,
    IDLE_TIMEOUT,
    InferenceBusy,
)
from queue_manager import IMAGE_QUEUE, QueueFull, QueueTimeout
from schemas import (
    EditImage,
    EditResponse,
    GenerationImage,
    GenerationRequest,
    GenerationResponse,
    StatusResponse,
)
from temp_output import start_cleaner, write_output

# --- CORS: explicit origins only (never "*"), config-driven ---------------
_DEFAULT_ORIGINS = [
    "http://localhost:8020",
    "http://127.0.0.1:8020",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_EXTRA_ORIGINS = [
    o.strip() for o in os.environ.get("IMAGE_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
ALLOWED_ORIGINS = list(dict.fromkeys([*_DEFAULT_ORIGINS, *_EXTRA_ORIGINS]))


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_cleaner()
    yield


app = FastAPI(title="Qwen-Image-2.1 Service", version="0.2-queue", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.exception_handler(RequestValidationError)
async def _validation_400(request, exc):
    # keep the project error style: schema problems -> 400 (no stack traces)
    return JSONResponse(status_code=400, content={
        "error": {"code": "INVALID_REQUEST", "message": "missing or invalid request fields"}
    })


@app.exception_handler(HTTPException)
async def _http_error(request, exc):
    # single error envelope for every coded error: {"error": {"code", "message"}}
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = {"error": {"code": f"HTTP_{exc.status_code}", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


# --- shared validation helpers --------------------------------------------
VALID_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}


def _bad(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _parse_size(size: str | None, default: tuple[int, int]) -> tuple[int, int]:
    """Parse "WxH" (also X/×); "auto"/empty -> default. Enforce capability limits."""
    raw = (size or "").strip().lower()
    if raw in ("", "auto"):
        return default
    for sep in ("x", "×"):
        if sep in raw:
            w_str, _, h_str = raw.partition(sep)
            break
    else:
        raise _bad("INVALID_SIZE", f"size must look like 1024x1024, got {size!r}")
    try:
        w, h = int(w_str.strip()), int(h_str.strip())
    except ValueError:
        raise _bad("INVALID_SIZE", f"size must look like 1024x1024, got {size!r}")
    _check_dims(w, h)
    return w, h


def _check_dims(w: int, h: int) -> None:
    if not (MIN_EDGE <= w <= MAX_EDGE and MIN_EDGE <= h <= MAX_EDGE):
        raise _bad("INVALID_SIZE",
                   f"width/height must be within {MIN_EDGE}-{MAX_EDGE}, got {w}x{h}")
    if w * h > MAX_PIXELS:
        raise _bad("INVALID_SIZE",
                   f"total pixels must be <= {MAX_PIXELS}, got {w}x{h} ({w * h})")
    if max(w, h) / min(w, h) > MAX_ASPECT_RATIO:
        raise _bad("INVALID_SIZE",
                   f"aspect ratio must be <= {MAX_ASPECT_RATIO}, got {w}x{h}")
    if w % MULTIPLE_OF or h % MULTIPLE_OF:
        raise _bad("INVALID_SIZE",
                   f"width/height must be multiples of {MULTIPLE_OF}, got {w}x{h}")


def _clamp_dims(w: int, h: int) -> tuple[int, int]:
    """Scale oversized keep-original inputs down into the capability envelope."""
    if w <= 0 or h <= 0:
        raise _bad("INVALID_IMAGE", f"invalid image dimensions {w}x{h}")
    if w <= MAX_EDGE and h <= MAX_EDGE and w * h <= MAX_PIXELS:
        return w, h
    scale = min(MAX_EDGE / max(w, h), math.sqrt(MAX_PIXELS / float(w * h)))
    cw, ch = max(MULTIPLE_OF, int(w * scale)), max(MULTIPLE_OF, int(h * scale))
    if cw * ch > MAX_PIXELS:  # guard float rounding overshoot
        cw, ch = int(cw * 0.999), int(ch * 0.999)
    return cw, ch


def _check_format(fmt: str | None) -> str:
    key = (fmt or "png").strip().lower()
    if key not in VALID_FORMATS:
        raise _bad("INVALID_FORMAT", f"output_format must be png/jpeg/webp, got {fmt!r}")
    return VALID_FORMATS[key]


def _convert_image_format(blob: bytes, fmt: str) -> tuple[bytes, str]:
    """Pipeline always yields PNG bytes; convert only when asked for jpeg/webp."""
    if fmt == "png":
        return blob, "png"
    from PIL import Image
    img = Image.open(io.BytesIO(blob))
    buf = io.BytesIO()
    if fmt == "jpeg":
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        bg.save(buf, format="JPEG", quality=95)
        return buf.getvalue(), "jpg"
    img.save(buf, format="WEBP", quality=95)
    return buf.getvalue(), "webp"


def _int_or_none(value) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        raise _bad("INVALID_REQUEST", f"expected an integer, got {value!r}")


# --- quality -> inference steps (single helper, shared by both endpoints) --
# table lives in capability.py (single source of truth with the UI profile)
QUALITY_STEPS = capability.QUALITY_STEPS
DEFAULT_STEPS = capability.DEFAULT_STEPS


def _resolve_steps(explicit: int | None, quality: str | None) -> int:
    """Priority: explicit num_inference_steps > quality preset > 24."""
    if explicit is not None:
        return explicit
    q = (quality or "").strip().lower()
    if q:
        return QUALITY_STEPS.get(q, DEFAULT_STEPS)
    return DEFAULT_STEPS


# --- endpoints --------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "qwen-image-2.1", "model_loaded": MANAGER.loaded}


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    from model_manager import GPU_LOCK_PATH
    age = (time.time() - MANAGER.last_used) if MANAGER.last_used else None
    lock = None
    if getattr(MANAGER, "_lease_fd", None) is not None:
        try:
            lock = GPU_LOCK_PATH.read_text().strip()
        except OSError:
            lock = "held"
    return StatusResponse(
        model_loaded=MANAGER.loaded,
        idle_timeout_seconds=IDLE_TIMEOUT,
        last_used_age_seconds=age,
        gpu_lock=lock,
        queue={
            **IMAGE_QUEUE.stats(),
            "waiting_for_gpu": int(bool(MANAGER.waiting_for_gpu)),
        },
        capability=capability.as_dict(),
    )


@app.post("/v1/images/generations", response_model=GenerationResponse)
def generations(req: GenerationRequest) -> GenerationResponse:
    t_start = time.time()
    width, height = _parse_size(req.size, (1024, 1024))
    fmt = _check_format(req.output_format)
    negative = req.negative_prompt.strip() if req.negative_prompt and req.negative_prompt.strip() else None
    steps = _resolve_steps(req.num_inference_steps, req.quality)
    print(f"[gen] steps={steps} explicit={req.num_inference_steps} "
          f"quality={req.quality} size={width}x{height} n={req.n}", flush=True)

    was_loaded = MANAGER.loaded
    t_queue = time.time()
    try:
        IMAGE_QUEUE.acquire()
    except QueueFull as e:
        raise _bad("QUEUE_FULL", str(e), status=429)
    except QueueTimeout as e:
        raise _bad("QUEUE_TIMEOUT", str(e), status=503)
    queue_wait = time.time() - t_queue
    try:
        try:
            blobs, infer_s = MANAGER.generate(
                prompt=req.prompt, n=req.n, size=f"{width}x{height}",
                negative_prompt=negative, seed=req.seed, steps=steps,
            )
        except GpuWaitTimeout:
            raise _bad("GPU_WAIT_TIMEOUT",
                       f"等待 GPU 超时（{GPU_WAIT_TIMEOUT}s）", status=503)
        except GpuBusy as e:
            raise _bad("GPU_BUSY", str(e), status=503)
        except HTTPException:
            raise
        except Exception as e:  # load/generation failure
            raise _bad("GENERATION_FAILED", str(e), status=500)
    finally:
        IMAGE_QUEUE.release()

    load_s = MANAGER.last_load_seconds if not was_loaded else None
    stamp = int(time.time())
    data = []
    for i, blob in enumerate(blobs):
        blob, ext = _convert_image_format(blob, fmt)
        path = write_output(f"gen_{stamp}_{i}.{ext}", blob)
        data.append(GenerationImage(
            b64=base64.b64encode(blob).decode(),
            b64_json=base64.b64encode(blob).decode(),
            path=str(path),
            seed=req.seed,
        ))
    total_s = time.time() - t_start
    return GenerationResponse(
        created=stamp, data=data,
        load_seconds=round(load_s, 3) if load_s else None,
        # legacy field kept equal to inference_seconds
        generation_seconds=round(infer_s, 3),
        queue_wait_seconds=round(queue_wait, 3),
        inference_seconds=round(infer_s, 3),
        total_seconds=round(total_s, 3),
        effective_steps=steps,
    )


@app.post("/v1/images/edits", response_model=EditResponse)
async def edits(request: Request) -> EditResponse:
    t_start = time.time()
    form = await request.form()

    prompt = str(form.get("prompt") or "").strip()
    if not prompt:
        raise _bad("INVALID_REQUEST", "prompt is required")
    if form.get("mask"):
        raise _bad("MASK_UNSUPPORTED", "mask editing unsupported by current model")

    files = [f for f in (*form.getlist("image[]"), *form.getlist("image"))
             if hasattr(f, "read")]
    if not files:
        raise _bad("INVALID_IMAGE", "image file is required (field image or image[])")
    if len(files) > MAX_REFERENCE_IMAGES:
        raise _bad("TOO_MANY_REFERENCE_IMAGES",
                   f"Qwen-Image-2.1 accepts at most {MAX_REFERENCE_IMAGES} reference images",
                   status=400)

    from PIL import Image as PILImage
    pils = []
    for f in files:
        raw = await f.read()
        if not raw:
            raise _bad("INVALID_IMAGE", "image file is empty")
        if len(raw) > 20 * 1024 * 1024:
            raise _bad("IMAGE_TOO_LARGE", "image exceeds 20MB limit")
        try:
            pil = PILImage.open(io.BytesIO(raw))
            pil.load()
        except Exception:
            raise _bad("INVALID_IMAGE", "file is not a readable image (PNG/JPEG/WEBP)")
        if pil.mode not in ("RGB", "RGBA"):
            pil = pil.convert("RGB")
        pils.append(pil)
    main = pils[0]  # image 1 = main image; images 2..N = style references
    images = pils[0] if len(pils) == 1 else pils  # native multi-image list input

    # target output size: explicit width/height > size field > keep original (main)
    width = _int_or_none(form.get("width"))
    height = _int_or_none(form.get("height"))
    size_field = form.get("size")
    if width is not None or height is not None:
        if width is None or height is None:
            raise _bad("INVALID_SIZE", "width and height must be given together")
        _check_dims(width, height)
    elif size_field and str(size_field).strip().lower() != "auto":
        width, height = _parse_size(str(size_field), (main.width, main.height))
    else:
        # keep original (clamped into the capability envelope if oversized)
        width, height = _clamp_dims(main.width, main.height)

    fmt = _check_format(str(form.get("output_format") or "png"))
    negative = str(form.get("negative_prompt") or "").strip() or None
    explicit_steps = _int_or_none(form.get("num_inference_steps"))
    if explicit_steps is not None and not (1 <= explicit_steps <= 200):
        raise _bad("INVALID_REQUEST", "num_inference_steps must be within 1-200")
    quality = str(form.get("quality") or "").strip() or None
    steps = _resolve_steps(explicit_steps, quality)
    print(f"[edit] steps={steps} explicit={explicit_steps} quality={quality} "
          f"target={width}x{height} refs={len(pils)}", flush=True)
    seed = _int_or_none(form.get("seed"))

    was_loaded = MANAGER.loaded

    def _job():
        t_queue = time.time()
        try:
            IMAGE_QUEUE.acquire()
        except QueueFull as e:
            raise _bad("QUEUE_FULL", str(e), status=429)
        except QueueTimeout as e:
            raise _bad("QUEUE_TIMEOUT", str(e), status=503)
        queue_wait = time.time() - t_queue
        try:
            outs, infer_s = MANAGER.edit(
                image=images, prompt=prompt, negative_prompt=negative,
                steps=steps, seed=seed, width=width, height=height,
            )
        finally:
            IMAGE_QUEUE.release()
        return outs, infer_s, queue_wait

    try:
        outs, infer_s, queue_wait = await run_in_threadpool(_job)
    except GpuWaitTimeout:
        raise _bad("GPU_WAIT_TIMEOUT",
                   f"等待 GPU 超时（{GPU_WAIT_TIMEOUT}s）", status=503)
    except GpuBusy as e:
        raise _bad("GPU_BUSY", str(e), status=503)
    except HTTPException:
        raise
    except Exception:
        raise _bad("EDIT_FAILED", "image editing pipeline failed", status=500)

    load_s = 0.0 if was_loaded else (MANAGER.last_load_seconds or 0.0)
    stamp = int(time.time())
    data = []
    for i, (blob, out_w, out_h) in enumerate(outs):
        blob, ext = _convert_image_format(blob, fmt)
        path = write_output(f"edit_{stamp}_{i}.{ext}", blob)
        data.append(EditImage(
            b64_json=base64.b64encode(blob).decode(),
            path=str(path), width=out_w, height=out_h,
        ))
    total_s = time.time() - t_start
    return EditResponse(
        created=stamp, data=data,
        load_seconds=round(load_s, 3),
        inference_seconds=round(infer_s, 3),
        queue_wait_seconds=round(queue_wait, 3),
        total_seconds=round(total_s, 3),
        effective_steps=steps,
    )


@app.post("/unload")
def unload() -> dict:
    try:
        changed = MANAGER.unload()
    except InferenceBusy as e:
        # never block for minutes and never release the gpu lease mid-run
        raise _bad("INFERENCE_BUSY", str(e), status=409)
    return {"unloaded": changed, "model_loaded": MANAGER.loaded}
