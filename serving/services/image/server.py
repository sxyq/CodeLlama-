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

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from model_manager import MANAGER, GpuBusy, IDLE_TIMEOUT
from schemas import (
    GenerationImage,
    GenerationRequest,
    GenerationResponse,
    StatusResponse,
)

app = FastAPI(title="Qwen-Image-2.1 Service", version="0.1-staged")

OUTPUT_DIR = Path("/home/syy/ai-serving/logs/image/generated")


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


@app.post("/v1/images/edits")
def edits() -> JSONResponse:
    return JSONResponse(status_code=501, content={
        "error": {"code": "NOT_IMPLEMENTED", "message": "image editing not implemented yet"}
    })


@app.post("/unload")
def unload() -> dict:
    changed = MANAGER.unload()
    return {"unloaded": changed, "model_loaded": MANAGER.loaded}
