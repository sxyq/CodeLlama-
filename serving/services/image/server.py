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
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from model_manager import MANAGER, GpuBusy, IDLE_TIMEOUT
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


# --- shared validation helpers --------------------------------------------
VALID_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}


def _bad(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _parse_size(size: str | None, default: tuple[int, int]) -> tuple[int, int]:
    """Parse "WxH" (also X/×); "auto"/empty -> default. Enforce 512-2048 and /16."""
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
    if not (512 <= w <= 2048 and 512 <= h <= 2048):
        raise _bad("INVALID_SIZE", f"width/height must be within 512-2048, got {w}x{h}")
    if w % 16 or h % 16:
        raise _bad("INVALID_SIZE", f"width/height must be multiples of 16, got {w}x{h}")


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
        queue=IMAGE_QUEUE.stats(),
    )


@app.post("/v1/images/generations", response_model=GenerationResponse)
def generations(req: GenerationRequest) -> GenerationResponse:
    width, height = _parse_size(req.size, (1024, 1024))
    fmt = _check_format(req.output_format)
    negative = req.negative_prompt.strip() if req.negative_prompt and req.negative_prompt.strip() else None

    t_start = time.time()
    was_loaded = MANAGER.loaded
    try:
        IMAGE_QUEUE.acquire()
    except QueueFull as e:
        raise _bad("QUEUE_FULL", str(e), status=429)
    except QueueTimeout as e:
        raise _bad("QUEUE_TIMEOUT", str(e), status=503)
    try:
        try:
            blobs = MANAGER.generate(
                prompt=req.prompt, n=req.n, size=f"{width}x{height}",
                negative_prompt=negative, seed=req.seed, steps=req.num_inference_steps,
            )
        except GpuBusy as e:
            raise _bad("GPU_BUSY", str(e), status=503)
        except HTTPException:
            raise
        except Exception as e:  # load/generation failure
            raise _bad("GENERATION_FAILED", str(e), status=500)
    finally:
        IMAGE_QUEUE.release()

    total_s = time.time() - t_start
    load_s = MANAGER.last_load_seconds if not was_loaded else None
    gen_s = max(total_s - (load_s or 0.0), 0.0)
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
    return GenerationResponse(
        created=stamp, data=data,
        load_seconds=round(load_s, 3) if load_s else None,
        generation_seconds=round(gen_s, 3),
    )


@app.post("/v1/images/edits", response_model=EditResponse)
async def edits(request: Request) -> EditResponse:
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
    if len(files) > 1:
        raise _bad("MULTIPLE_IMAGES", "multiple input images are not supported by current model")

    raw = await files[0].read()
    if not raw:
        raise _bad("INVALID_IMAGE", "image file is empty")
    if len(raw) > 20 * 1024 * 1024:
        raise _bad("IMAGE_TOO_LARGE", "image exceeds 20MB limit")
    try:
        from PIL import Image as PILImage
        pil = PILImage.open(io.BytesIO(raw))
        pil.load()
    except Exception:
        raise _bad("INVALID_IMAGE", "file is not a readable image (PNG/JPEG/WEBP)")
    if pil.mode not in ("RGB", "RGBA"):
        pil = pil.convert("RGB")

    # target output size: explicit width/height > size field > keep original
    width = _int_or_none(form.get("width"))
    height = _int_or_none(form.get("height"))
    size_field = form.get("size")
    if width is not None or height is not None:
        if width is None or height is None:
            raise _bad("INVALID_SIZE", "width and height must be given together")
        _check_dims(width, height)
    elif size_field and str(size_field).strip().lower() != "auto":
        width, height = _parse_size(str(size_field), (pil.width, pil.height))
    else:
        width, height = pil.width, pil.height
        if max(width, height) > 2048:  # GPU safety cap for oversized uploads
            scale = 2048 / max(width, height)
            width, height = max(16, round(width * scale)), max(16, round(height * scale))

    fmt = _check_format(str(form.get("output_format") or "png"))
    negative = str(form.get("negative_prompt") or "").strip() or None
    steps = _int_or_none(form.get("num_inference_steps"))
    if steps is not None and not (1 <= steps <= 200):
        raise _bad("INVALID_REQUEST", "num_inference_steps must be within 1-200")
    seed = _int_or_none(form.get("seed"))

    was_loaded = MANAGER.loaded

    def _job():
        try:
            IMAGE_QUEUE.acquire()
        except QueueFull as e:
            raise _bad("QUEUE_FULL", str(e), status=429)
        except QueueTimeout as e:
            raise _bad("QUEUE_TIMEOUT", str(e), status=503)
        try:
            return MANAGER.edit(
                image=pil, prompt=prompt, negative_prompt=negative,
                steps=steps, seed=seed, width=width, height=height,
            )
        finally:
            IMAGE_QUEUE.release()

    t_start = time.time()
    try:
        outs, infer_s = await run_in_threadpool(_job)
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
    return EditResponse(
        created=stamp, data=data,
        load_seconds=round(load_s, 3),
        inference_seconds=round(infer_s, 3),
    )


@app.post("/unload")
def unload() -> dict:
    changed = MANAGER.unload()
    return {"unloaded": changed, "model_loaded": MANAGER.loaded}
