#!/usr/bin/env python3
"""Generate upstream preset-config.json from models.json.

models.json is the deployment model registry (real api_base lives only on
the server and is gitignored). Upstream gpt_image_playground consumes a
preset config via VITE_DEFAULT_API_URL at build time; this script maps the
first generation-capable model into an upstream profile so the WebUI opens
with a ready-to-use model selector entry.

Usage: gen-preset-config.py <models.json> <out preset-config.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    models_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    data = json.loads(models_path.read_text(encoding="utf-8"))
    models = data.get("models") or []
    picked = next(
        (m for m in models if m.get("supports_generation") or m.get("supports_edit")),
        None,
    )
    if not picked:
        print("gen-preset-config: no usable model in", models_path, file=sys.stderr)
        return 1

    usable = [m for m in models if m.get("supports_generation") or m.get("supports_edit")]
    profiles = []
    for i, m in enumerate(usable):
        profiles.append({
            "id": m["id"],
            "name": m.get("display_name", m["id"]),
            "provider": "openai",
            "baseUrl": m["api_base"],
            "model": m.get("display_name", m["id"]),
            "apiMode": "images",
            # non-secret placeholder: the backend performs no authentication, but
            # the upstream UI refuses to submit with an empty API key
            "apiKey": "internal-no-auth",
            "isDefault": m["id"] == picked["id"],
            "timeout": 600,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"profiles": profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"gen-preset-config: wrote {out_path} ({len(profiles)} profile(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
