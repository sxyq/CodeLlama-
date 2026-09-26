"""Request/response schemas for the image service (pydantic v2)."""
from __future__ import annotations
from pydantic import BaseModel, Field

VALID_OUTPUT_FORMATS = ("png", "jpeg", "webp")


class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    n: int = Field(default=1, ge=1, le=4)
    size: str = Field(default="1024x1024")  # WxH, "auto", validated in endpoint
    seed: int | None = None
    num_inference_steps: int | None = Field(default=None, ge=1, le=200)
    # quality preset: fast/low=4, standard/medium=24, high=40 (see server._resolve_steps)
    quality: str | None = None
    output_format: str = "png"


class GenerationImage(BaseModel):
    b64: str | None = None
    b64_json: str | None = None
    path: str | None = None
    seed: int | None = None


class GenerationResponse(BaseModel):
    created: int
    model: str = "Qwen-Image-2.1"
    data: list[GenerationImage]
    load_seconds: float | None = None
    # legacy alias, equal to inference_seconds (kept for old clients)
    generation_seconds: float | None = None
    queue_wait_seconds: float | None = None
    inference_seconds: float | None = None
    total_seconds: float | None = None
    effective_steps: int | None = None


class QueueStats(BaseModel):
    running: int
    pending: int
    # >=1 request currently blocked in WAITING_FOR_GPU (admission not met yet)
    waiting_for_gpu: int = 0
    max_pending: int


class StatusResponse(BaseModel):
    model: str = "Qwen-Image-2.1"
    model_loaded: bool
    idle_timeout_seconds: int
    last_used_age_seconds: float | None
    gpu_lock: str | None
    queue: QueueStats
    # service capability (limits/presets/features) — single source for UI profiles
    capability: dict


class ErrorResponse(BaseModel):
    error: dict


class EditImage(BaseModel):
    b64_json: str | None = None
    path: str
    width: int
    height: int


class EditResponse(BaseModel):
    created: int
    model: str = "Qwen-Image-2.1"
    data: list[EditImage]
    load_seconds: float | None = None
    inference_seconds: float | None = None
    queue_wait_seconds: float | None = None
    total_seconds: float | None = None
    effective_steps: int | None = None
