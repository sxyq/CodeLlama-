"""Request/response schemas for the image service (pydantic v2)."""
from __future__ import annotations
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    n: int = Field(default=1, ge=1, le=4)
    size: str = Field(default="1024x1024")  # WxH
    seed: int | None = None
    num_inference_steps: int | None = None


class GenerationImage(BaseModel):
    b64: str | None = None
    path: str | None = None
    seed: int | None = None


class GenerationResponse(BaseModel):
    created: int
    model: str = "Qwen-Image-2.1"
    data: list[GenerationImage]
    load_seconds: float | None = None
    generation_seconds: float | None = None


class StatusResponse(BaseModel):
    model: str = "Qwen-Image-2.1"
    model_loaded: bool
    idle_timeout_seconds: int
    last_used_age_seconds: float | None
    gpu_lock: str | None


class ErrorResponse(BaseModel):
    error: dict
