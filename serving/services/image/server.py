"""Qwen-Image-2.1 serving API (staged, NOT started this round).

Start != load: server boots with MODEL_LOADED=false; the pipeline is
loaded lazily on the first /v1/images/generations request.

Future start command (deployment stage only):
  $HOME/ai-serving/env/image/bin/uvicorn server:app \
      --host 0.0.0.0 --port 8011
"""
from __future__ import annotations

import base64
import time
from pathlib import Path

import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from model_manager import MANAGER, GpuBusy, IDLE_TIMEOUT
from schemas import (
    EditImage,
    EditResponse,
    GenerationImage,
    GenerationRequest,
    GenerationResponse,
    StatusResponse,
)

app = FastAPI(title="Qwen-Image-2.1 Service", version="0.1-staged")

OUTPUT_DIR = Path("/home/syy/ai-serving/logs/image/generated")


@app.exception_handler(RequestValidationError)
async def _validation_400(request, exc):
    # keep the project error style: form/schema problems -> 400 (no stack traces)
    return JSONResponse(status_code=400, content={
        "error": {"code": "INVALID_REQUEST", "message": "missing or invalid form fields (image + prompt required)"}
    })


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "qwen-image-2.1", "model_loaded": MANAGER.loaded}


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    age = (time.time() - MANAGER.last_used) if MANAGER.last_used else None
    lock = None
    if getattr(MANAGER, "_lease_fd", None) is not None:
        lock_file = Path("/home/syy/ai-serving/state/gpu.lock")
        try:
            lock = lock_file.read_text().strip()
        except Exception:
            lock = "held"
    return StatusResponse(
        model_loaded=MANAGER.loaded,
        idle_timeout_seconds=IDLE_TIMEOUT,
        last_used_age_seconds=age,
        gpu_lock=lock,
    )


@app.post("/v1/images/generations", response_model=GenerationResponse)
def generations(req: GenerationRequest) -> GenerationResponse:
    t_start = time.time()
    try:
        blobs = MANAGER.generate(
            prompt=req.prompt, n=req.n, size=req.size,
            negative_prompt=req.negative_prompt, seed=req.seed,
            steps=req.num_inference_steps,
        )
    except GpuBusy as e:
        raise HTTPException(status_code=503, detail={"code": "GPU_BUSY", "message": str(e)})
    except Exception as e:  # load/generation failure
        raise HTTPException(status_code=500, detail={"code": "GENERATION_FAILED", "message": str(e)})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    data = []
    for i, blob in enumerate(blobs):
        path = OUTPUT_DIR / f"gen_{stamp}_{i}.png"
        path.write_bytes(blob)
        data.append(GenerationImage(
            b64=base64.b64encode(blob).decode(),
            path=str(path),
            seed=req.seed,
        ))
    total_s = time.time() - t_start
    load_s = MANAGER.last_load_seconds
    gen_s = max(total_s - (load_s or 0.0), 0.0) if load_s else None
    return GenerationResponse(created=stamp, data=data,
                              load_seconds=load_s, generation_seconds=gen_s)


MAX_UPLOAD_MB = 20


@app.post("/v1/images/edits", response_model=EditResponse)
async def edits(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str | None = Form(None),
    num_inference_steps: int | None = Form(None),
    seed: int | None = Form(None),
    width: int | None = Form(None),
    height: int | None = Form(None),
) -> EditResponse:
    # --- input validation (400s, no stack traces) ---
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_REQUEST", "message": "prompt is required"}})
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_IMAGE", "message": "image file is empty"}})
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail={"error": {"code": "IMAGE_TOO_LARGE", "message": f"image exceeds {MAX_UPLOAD_MB}MB limit"}})
    try:
        from PIL import Image as PILImage
        pil = PILImage.open(io.BytesIO(raw))
        pil.load()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_IMAGE", "message": "file is not a readable image (PNG/JPEG/WEBP)"}})
    if pil.mode not in ("RGB", "RGBA"):
        pil = pil.convert("RGB")
    # keep output resolution aligned with the input unless caller overrides
    if width is None:
        width = pil.width
    if height is None:
        height = pil.height

    # --- edit (lazy load + flock lease + re-checks live in ensure_loaded) ---
    was_loaded = MANAGER.loaded
    t_start = time.time()
    try:
        outs, infer_s = MANAGER.edit(
            image=pil, prompt=prompt, negative_prompt=negative_prompt,
            steps=num_inference_steps, seed=seed, width=width, height=height,
        )
    except GpuBusy as e:
        raise HTTPException(status_code=503, detail={"code": "GPU_BUSY", "message": str(e)})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"error": {"code": "EDIT_FAILED", "message": "image editing pipeline failed"}})

    total_s = time.time() - t_start
    load_s = 0.0 if was_loaded else (MANAGER.last_load_seconds or 0.0)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    data = []
    for i, (blob, w, h) in enumerate(outs):
        path = OUTPUT_DIR / f"edit_{stamp}_{i}.png"
        path.write_bytes(blob)
        data.append(EditImage(path=str(path), width=w, height=h))
    return EditResponse(created=stamp, data=data,
                        load_seconds=round(load_s, 3),
                        inference_seconds=round(infer_s, 3))


@app.post("/unload")
def unload() -> dict:
    changed = MANAGER.unload()
    return {"unloaded": changed, "model_loaded": MANAGER.loaded}
