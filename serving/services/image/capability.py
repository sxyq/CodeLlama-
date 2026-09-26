"""Single source of truth for the Qwen-Image-2.1 service capability.

Frontend model profiles mirror these values (webui .../lib/modelProfile.ts)
and refresh from GET /status -> capability at runtime, so backend validation
and UI limits stay in lockstep (task QWEN-IMAGE-MAX-CAPABILITY-AND-UI-PROFILE-001 §22).
"""
from __future__ import annotations

MAX_REFERENCE_IMAGES = 5
MIN_EDGE = 512
MAX_EDGE = 2752
MAX_PIXELS = 4_300_800  # 2400x1792, largest official preset area
MAX_ASPECT_RATIO = 1.8  # 2752/1536 = 1.797, widest tested preset
MULTIPLE_OF = 16

# quality preset -> inference steps (also used by server._resolve_steps).
# "max" = Ultra tier filled from this round's steps matrix (plateau at 120).
QUALITY_STEPS = {
    "fast": 4,
    "low": 4,
    "standard": 24,
    "medium": 24,
    "auto": 24,
    "high": 40,
    "xhigh": 40,
    "max": 120,
}
DEFAULT_STEPS = 24

# steps tiers (task §26): UI profile + /status.capability single source
OFFICIAL_RECOMMENDED_STEPS = 40
RECOMMENDED_HIGH_STEPS = 120  # Ultra preset, from the 24..200 matrix
MAX_CUSTOM_STEPS = 200

# Official Qwen-Image 2K aspect-ratio presets + the quick 1:1 option.
# production=False presets stay out of the normal UI picker (§16).
RESOLUTIONS = [
    {"label": "1024x1024", "width": 1024, "height": 1024, "production": True},
    {"label": "2048x2048", "width": 2048, "height": 2048, "production": True},
    {"label": "2400x1792", "width": 2400, "height": 1792, "production": True},
    {"label": "1792x2400", "width": 1792, "height": 2400, "production": True},
    {"label": "2528x1696", "width": 2528, "height": 1696, "production": True},
    {"label": "1696x2528", "width": 1696, "height": 2528, "production": True},
    {"label": "2752x1536", "width": 2752, "height": 1536, "production": True},
    {"label": "1536x2752", "width": 1536, "height": 2752, "production": True},
]

FEATURES = {
    "supports_edit": True,
    "supports_multi_reference": True,
    "supports_rgba": False,   # pipeline exposes no background/alpha output
    "supports_mask": False,   # QwenImage21Pipeline has no mask parameter
    "supports_strength": False,
}


def as_dict() -> dict:
    return {
        "model": "Qwen-Image-2.1",
        "max_reference_images": MAX_REFERENCE_IMAGES,
        "min_edge": MIN_EDGE,
        "max_edge": MAX_EDGE,
        "max_pixels": MAX_PIXELS,
        "max_aspect_ratio": MAX_ASPECT_RATIO,
        "multiple_of": MULTIPLE_OF,
        "quality_steps": {"fast": 4, "standard": 24, "high": 40},
        "steps": {
            "official_recommended_steps": OFFICIAL_RECOMMENDED_STEPS,
            "recommended_high_steps": RECOMMENDED_HIGH_STEPS,
            "max_custom_steps": MAX_CUSTOM_STEPS,
        },
        "resolutions": RESOLUTIONS,
        **FEATURES,
    }
