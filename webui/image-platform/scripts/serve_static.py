#!/usr/bin/env python3
"""Lightweight static file server for the internal image WebUI (no Docker).

Serves the built dist/ on 0.0.0.0:<port>, falls back to index.html for
unknown paths (SPA safety), and never lists directories.

Usage: serve_static.py [--port 8020] [--root DIST_DIR]
"""
from __future__ import annotations

import argparse
import posixpath
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class SpaStaticHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):  # no directory listings
        self.send_error(403, "Forbidden")
        return None

    def send_head(self):
        # SPA fallback: path without a file extension -> index.html
        rel = posixpath.normpath(self.path.lstrip("/").split("?", 1)[0])
        if rel in ("", ".") or (not Path(self.directory, rel).exists()
                                 and "." not in Path(rel).name):
            self.path = "/index.html"
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("[webui]", self.address_string(), fmt % args, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent / "dist"))
    parser.add_argument("--bind", default="0.0.0.0")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "index.html").is_file():
        raise SystemExit(f"serve_static: no index.html under {root}; build first")

    handler = lambda *a, **kw: SpaStaticHandler(*a, directory=str(root), **kw)  # noqa: E731
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"serve_static: http://{args.bind}:{args.port}/ -> {root}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
