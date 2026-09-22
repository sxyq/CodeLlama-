#!/usr/bin/env python3
# Collect training metrics after DEFAULT-LORA-001 run. Do not train.

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_timeline(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if "=" in line and not line.startswith("|") and not line.startswith("+"):
            k, v = line.split("=", 1)
            k = k.strip()
            if k in {
                "START_TIME_ISO",
                "END_TIME_ISO",
                "START_TIME_EPOCH",
                "END_TIME_EPOCH",
                "TOTAL_WALL_SECONDS",
                "TRAIN_EXIT_CODE",
                "CONFIG",
            }:
                out[k] = v.strip()
    return out


def summarize_gpu_monitor(csv_path):
    import csv
    out = {
        "peak_gpu_memory_used_mib": None,
        "min_gpu_memory_free_mib": None,
        "avg_gpu_utilization_percent": None,
        "max_gpu_utilization_percent": None,
        "max_temperature_c": None,
        "max_power_w": None,
    }
    path = Path(csv_path)
    if not path.is_file():
        return out
    used, free, util, temp, power = [], [], [], [], []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            def num(key, row=row):
                v = (row.get(key) or "").strip()
                try:
                    return float(v)
                except Exception:
                    return None
            u = num("memory.used")
            fr = num("memory.free")
            g = num("utilization.gpu")
            tp = num("temperature.gpu")
            pw = num("power.draw")
            if u is not None:
                used.append(u)
            if fr is not None:
                free.append(fr)
            if g is not None:
                util.append(g)
            if tp is not None:
                temp.append(tp)
            if pw is not None:
                power.append(pw)
    if used:
        out["peak_gpu_memory_used_mib"] = max(used)
    if free:
        out["min_gpu_memory_free_mib"] = min(free)
    if util:
        out["avg_gpu_utilization_percent"] = sum(util) / len(util)
        out["max_gpu_utilization_percent"] = max(util)
    if temp:
        out["max_temperature_c"] = max(temp)
    if power:
        out["max_power_w"] = max(power)
    return out


def find_peak_gpu(log_dir: Path) -> dict[str, Any]:
    peak = {"max_memory_allocated": None, "max_memory_reserved": None, "nvidia_smi_notes": []}
    for p in sorted(log_dir.glob("**/*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".log", ".txt", ".json"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r"max_memory_allocated[^0-9]{0,20}(\d+)", text):
            peak["max_memory_allocated"] = int(m.group(1))
        for m in re.finditer(r"max_memory_reserved[^0-9]{0,20}(\d+)", text):
            peak["max_memory_reserved"] = int(m.group(1))
        if "MiB" in text and "NVIDIA" in text:
            peak["nvidia_smi_notes"].append(str(p.name))
    return peak


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--experiment-id", default="DEFAULT-LORA-001")
    ap.add_argument("--token-accounting", default=os.path.expanduser("~/codellama-lora/reports/train_token_accounting.json"))
    ap.add_argument("--token-stats", default=os.path.expanduser("~/codellama-lora/reports/token_stats.json"))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)
    timeline = parse_timeline(Path(args.timeline).read_text(encoding="utf-8") if Path(args.timeline).is_file() else "")

    # LLaMA-Factory / HF Trainer outputs (names vary slightly by version)
    candidates = {
        "trainer_state": ["trainer_state.json", "checkpoint-*/trainer_state.json"],
        "train_results": ["train_results.json", "all_results.json"],
        "all_results": ["all_results.json"],
    }

    def first_json(patterns: list[str]) -> Any:
        for pat in patterns:
            if "*" in pat:
                hits = sorted(out_dir.glob(pat))
                for h in hits:
                    data = load_json(h)
                    if data is not None:
                        return {"path": str(h), "data": data}
            else:
                p = out_dir / pat
                data = load_json(p)
                if data is not None:
                    return {"path": str(p), "data": data}
        return None

    trainer_state = first_json(candidates["trainer_state"])
    train_results = first_json(candidates["train_results"])
    all_results = first_json(candidates["all_results"])

    metrics = (train_results or {}).get("data") or {}
    if not metrics and all_results:
        metrics = all_results.get("data") or {}
    state = (trainer_state or {}).get("data") or {}
    log_history = state.get("log_history") or []

    token_acc = load_json(Path(args.token_accounting)) or {}
    token_stats = load_json(Path(args.token_stats)) or {}

    # adapter / checkpoint discovery
    adapter_path = None
    for p in sorted(out_dir.glob("**/*")):
        if p.name in {"adapter_config.json", "adapter_model.safetensors", "adapter_model.bin"}:
            adapter_path = str(p.parent)
            break
    checkpoints = [str(p) for p in sorted(out_dir.glob("checkpoint-*")) if p.is_dir()]

    train_epoch_tokens = token_acc.get("train_tokens_per_epoch_after_cutoff", {})
    train_3e = token_acc.get("train_token_presentations_3e", {})

    report = {
        "experiment_id": args.experiment_id,
        "model": "/data/vllm/CodeLlama-13b-Instruct-hf",
        "framework": "LLaMA-Factory",
        "framework_version": "0.9.6.dev0",
        "framework_commit": "97b32d3133b501432141a82949d5c7bc4d94f23a",
        "dataset_sha256": token_stats.get("dataset", {}).get("sha256") or "28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6",
        "samples": token_acc.get("dataset", {}).get("samples_loaded") or token_stats.get("dataset", {}).get("samples"),
        "template": "llama2",
        "cutoff_len": 2048,
        "packing": False,
        "lora_rank": 8,
        "lora_alpha": 16,
        "lora_dropout": 0,
        "lora_target": "all",
        "epochs": 3.0,
        "learning_rate": 5e-5,
        "batch_size": 2,
        "gradient_accumulation": 8,
        "effective_batch": 16,
        "raw_input_tokens": token_acc.get("raw_tokens", {}).get("input_tokens")
        or token_stats.get("raw_tokens", {}).get("input_total"),
        "raw_output_tokens": token_acc.get("raw_tokens", {}).get("output_tokens")
        or token_stats.get("raw_tokens", {}).get("output_total"),
        "raw_total_tokens": token_acc.get("raw_tokens", {}).get("total_tokens")
        or token_stats.get("raw_tokens", {}).get("total"),
        "effective_input_tokens": token_stats.get("effective_tokens", {}).get("prompt_total"),
        "effective_output_tokens": token_stats.get("effective_tokens", {}).get("response_total"),
        "effective_total_tokens": token_stats.get("effective_tokens", {}).get("total"),
        "train_input_tokens_per_epoch": train_epoch_tokens.get("train_input_context_tokens_per_epoch"),
        "train_output_tokens_per_epoch": train_epoch_tokens.get("train_output_response_tokens_per_epoch"),
        "train_total_tokens_per_epoch": train_epoch_tokens.get("train_total_tokens_per_epoch"),
        "loss_bearing_tokens_per_epoch": train_epoch_tokens.get("loss_bearing_tokens_per_epoch"),
        "train_input_tokens_all_epochs": train_3e.get("train_input_context_tokens_total_3e"),
        "train_output_tokens_all_epochs": train_3e.get("train_output_response_tokens_total_3e"),
        "train_total_tokens_all_epochs": train_3e.get("train_total_token_presentations_3e"),
        "loss_bearing_tokens_all_epochs": train_3e.get("loss_bearing_token_presentations_3e"),
        "start_time": timeline.get("START_TIME_ISO"),
        "end_time": timeline.get("END_TIME_ISO"),
        "wall_seconds": int(timeline["TOTAL_WALL_SECONDS"]) if timeline.get("TOTAL_WALL_SECONDS", "").isdigit() else timeline.get("TOTAL_WALL_SECONDS"),
        "train_exit_code": timeline.get("TRAIN_EXIT_CODE"),
        "train_runtime": metrics.get("train_runtime"),
        "train_loss": metrics.get("train_loss") or metrics.get("loss"),
        "train_samples_per_second": metrics.get("train_samples_per_second"),
        "train_steps_per_second": metrics.get("train_steps_per_second"),
        "train_flos": metrics.get("train_flos") or metrics.get("total_flos"),
        "learning_rate_log": metrics.get("learning_rate"),
        "epoch": metrics.get("epoch"),
        "global_steps": metrics.get("global_step") or state.get("global_step"),
        "log_history_tail": log_history[-5:] if log_history else [],
        "peak_gpu_memory": find_peak_gpu(log_dir),
        "gpu_monitor_summary": summarize_gpu_monitor(log_dir / "gpu_monitor.csv"),
        "output_dir": str(out_dir),
        "adapter_path": adapter_path,
        "checkpoints": checkpoints,
        "trainer_state_path": (trainer_state or {}).get("path"),
        "train_results_path": (train_results or {}).get("path"),
        "all_results_path": (all_results or {}).get("path"),
        "timeline": timeline,
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "global_steps": report["global_steps"], "train_loss": report["train_loss"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
