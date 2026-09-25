#!/usr/bin/env python3
"""Lightweight GGUF header/metadata reader (stdlib only, no weight loading)."""
import struct
import sys

U8, I8, U16, I16, U32, I32, F32, BOOL, STR, ARR, U64, I64, F64 = range(13)
SCALAR_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def read_str(f, cap=64 * 1024 * 1024):
    (n,) = struct.unpack("<Q", f.read(8))
    if n > cap:
        raise ValueError(f"string length {n} exceeds cap — misaligned?")
    return f.read(n).decode("utf-8", errors="replace")


def read_value(f, t, depth=0):
    if depth > 2:
        raise ValueError("nested array")
    if t in SCALAR_SIZE and t != STR and t != ARR:
        fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
               6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}[t]
        return struct.unpack(fmt, f.read(SCALAR_SIZE[t]))[0]
    if t == STR:
        return read_str(f)
    if t == ARR:
        at, n = struct.unpack("<IQ", f.read(12))
        if n > 10_000_000:
            raise ValueError(f"array count {n} insane — misaligned?")
        if at in SCALAR_SIZE and at not in (STR, ARR):
            sz = SCALAR_SIZE[at] * n
            data = f.read(sz)
            if len(data) != sz:
                raise ValueError("short read")
            fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
                   6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}[at]
            return list(struct.unpack(f"{n}{fmt[1:]}", data))
        return [read_value(f, at, depth + 1) for _ in range(n)]
    raise ValueError(f"unknown gguf type {t}")


def main(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"GGUF":
            print(f"NOT_GGUF magic={magic!r}", flush=True)
            return 2
        (version,) = struct.unpack("<I", f.read(4))
        tensor_count, kv_count = struct.unpack("<QQ", f.read(16))
        print(f"MAGIC=GGUF VERSION={version} TENSOR_COUNT={tensor_count} KV_COUNT={kv_count}", flush=True)
        keys = []
        for i in range(kv_count):
            key = read_str(f)
            (t,) = struct.unpack("<I", f.read(4))
            try:
                val = read_value(f, t)
            except Exception as e:
                print(f"STOP_AT kv#{i} key={key!r} err={e}", flush=True)
                return 3
            keys.append((key, val))
            if i < 5 or any(s in key.lower() for s in
                            ("architecture", "context_length", "file_type", "name",
                             "quantization", "embedding_length", "block_count")):
                show = val if not isinstance(val, list) or len(val) <= 8 else f"<list len={len(val)}>"
                print(f"KV {key} = {show}", flush=True)
        print("=== SUMMARY ===", flush=True)
        for key, val in keys:
            lk = key.lower()
            if any(s in lk for s in ("architecture", "context_length", "file_type",
                                     "quantization", "embedding_length", "block_count",
                                     "general.name", "head_count", "expert_count")):
                show = val if not isinstance(val, list) or len(val) <= 16 else f"<list len={len(val)}>"
                print(f"{key} = {show}", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
