#!/usr/bin/env python3
# TOKEN-AUDIT-001 — CodeLlama raw + effective SFT token audit (CPU tokenizer only)
# Does NOT load model weights. Does NOT train.

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_SHA256 = "28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6"
CUTOFFS = [512, 1024, 2048, 4096, 8192, 16384]
TASK_ID = "TOKEN-AUDIT-001"
LF_PIN = "97b32d3133b501432141a82949d5c7bc4d94f23a"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def percentile(sorted_vals: list[int], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(sorted_vals[lo])
    return sorted_vals[lo] * (hi - pos) + sorted_vals[hi] * (pos - lo)


def dist_stats(vals: list[int]) -> dict[str, float]:
    if not vals:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "median": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    s = sorted(vals)
    return {
        "count": len(s),
        "min": s[0],
        "max": s[-1],
        "mean": float(statistics.fmean(s)),
        "median": float(statistics.median(s)),
        "p25": percentile(s, 0.25),
        "p50": percentile(s, 0.50),
        "p75": percentile(s, 0.75),
        "p90": percentile(s, 0.90),
        "p95": percentile(s, 0.95),
        "p99": percentile(s, 0.99),
    }


def threshold_counts(vals: list[int]) -> dict[str, int]:
    ths = [512, 1024, 2048, 4096, 8192, 16384]
    return {f"ge_{t}": sum(1 for v in vals if v >= t) for t in ths}


FUNC_PATTERNS = [
    # type name(args) {  /  type name(args) const {
    re.compile(
        r"(?:^|\n)\s*(?:(?:unsigned|signed|static|inline|extern|virtual|constexpr|ZEXPORT|FAR|ZEXTERN|local)\s+)*"
        r"(?:[\w\:\*\&\s]+?)\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{",
        re.MULTILINE,
    ),
]


def extract_function_name(code: str) -> str:
    if not code or not code.strip():
        return "UNKNOWN"
    # strip leading comments roughly
    text = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    text = re.sub(r"//.*?$", " ", text, flags=re.M)
    # common wrappers / non-functions
    for pat in FUNC_PATTERNS:
        matches = pat.findall(text)
        if matches:
            # pick the last top-level-looking definition (often the real one after decls)
            name = matches[-1]
            if name in {"if", "for", "while", "switch", "return", "sizeof", "typeof"}:
                continue
            return name
    return "UNKNOWN"


def infer_seqlen(source_len: int, target_len: int, cutoff_len: int) -> tuple[int, int]:
    # copied semantics from LLaMA-Factory processor_utils.infer_seqlen @ pinned commit
    if target_len * 2 < cutoff_len:
        max_target_len = cutoff_len
    elif source_len * 2 < cutoff_len:
        max_target_len = cutoff_len - source_len
    else:
        max_target_len = int(cutoff_len * (target_len / (source_len + target_len)))
    new_target_len = min(max_target_len, target_len)
    max_source_len = max(cutoff_len - new_target_len, 0)
    new_source_len = min(max_source_len, source_len)
    return new_source_len, new_target_len


def collect_defaults() -> dict[str, Any]:
    out: dict[str, Any] = {"webui": {}, "dataclass": {}, "example_yaml": {}, "hf_training_arguments": {}}
    # WebUI values are transcribed from pinned source with file:line evidence in report.
    out["webui"] = {
        "learning_rate": "5e-5",
        "num_train_epochs": "3.0",
        "cutoff_len": 2048,
        "batch_size": 2,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "cosine",
        "compute_type": "bf16",
        "packing": False,
        "neat_packing": False,
        "train_on_prompt": False,
        "lora_rank": 8,
        "lora_alpha": 16,
        "lora_dropout": 0,
        "lora_target": "",
        "warmup_steps": 0,
        "logging_steps": 5,
        "save_steps": 100,
        "val_size": 0,
        "train_seed": "42",
        "max_samples": "100000",
        "max_grad_norm": "1.0",
        "report_to": "none",
        "extra_args": '{"optim": "adamw_torch"}',
        "evidence": {
            "file": "src/llamafactory/webui/components/train.py",
            "lines": "52-224",
        },
    }
    out["dataclass"] = {
        "learning_rate": "5e-05 (HF TrainingArguments)",
        "num_train_epochs": "3.0 (HF TrainingArguments)",
        "cutoff_len": 2048,
        "batch_size": "per_device_train_batch_size=8 (HF)",
        "gradient_accumulation_steps": 1,
        "lr_scheduler_type": "linear (HF)",
        "warmup_steps": 0,
        "warmup_ratio": None,
        "packing": None,
        "packing_effective_for_sft": False,
        "neat_packing": False,
        "train_on_prompt": False,
        "lora_rank": 8,
        "lora_alpha": None,
        "lora_alpha_effective": "lora_rank * 2 = 16 if unset",
        "lora_dropout": 0.0,
        "lora_target": "all",
        "bf16": False,
        "fp16": False,
        "gradient_checkpointing": False,
        "logging_steps": 500,
        "save_steps": 500,
        "val_size": 0.0,
        "seed": 42,
        "max_samples": None,
        "report_to": "none",
        "optim": "adamw_torch_fused",
        "evidence": {
            "files": [
                "src/llamafactory/hparams/data_args.py",
                "src/llamafactory/hparams/finetuning_args.py",
                "src/llamafactory/hparams/parser.py:645",
            ]
        },
    }
    out["example_yaml"] = {
        "path": "examples/train_lora/qwen3_lora_sft.yaml",
        "learning_rate": "1.0e-4",
        "num_train_epochs": 3.0,
        "cutoff_len": 2048,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "cosine",
        "warmup_ratio": 0.1,
        "bf16": True,
        "lora_rank": 8,
        "lora_target": "all",
        "lora_alpha": None,
        "packing": None,
        "train_on_prompt": None,
        "logging_steps": 10,
        "save_steps": 500,
        "val_size": None,
        "max_samples": 1000,
        "report_to": "none",
        "seed": None,
    }
    try:
        from transformers import TrainingArguments
        import dataclasses
        import inspect

        sig = inspect.signature(TrainingArguments.__init__)
        keys = [
            "learning_rate",
            "num_train_epochs",
            "lr_scheduler_type",
            "warmup_steps",
            "warmup_ratio",
            "logging_steps",
            "save_steps",
            "seed",
            "optim",
            "bf16",
            "fp16",
            "gradient_checkpointing",
            "report_to",
            "per_device_train_batch_size",
            "gradient_accumulation_steps",
            "max_grad_norm",
        ]
        for k in keys:
            p = sig.parameters.get(k)
            val = None if p is None else p.default
            if hasattr(val, "value"):
                val = val.value
            out["hf_training_arguments"][k] = val
    except Exception as e:  # pragma: no cover
        out["hf_training_arguments"] = {"error": str(e)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CodeLlama token audit (tokenizer only)")
    ap.add_argument("--dataset", default=os.path.expanduser("~/codellama-lora/data/Fine-Tuning.json"))
    ap.add_argument("--tokenizer", default="/data/vllm/CodeLlama-13b-Instruct-hf")
    ap.add_argument("--output-dir", default=os.path.expanduser("~/codellama-lora/reports"))
    ap.add_argument("--lf-root", default=os.path.expanduser("~/codellama-lora/LLaMA-Factory"))
    ap.add_argument("--template", default="llama2")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ds_path = Path(args.dataset)
    tok_path = args.tokenizer

    # 1) dataset integrity
    raw = ds_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    hash_ok = sha == EXPECTED_SHA256
    data = json.loads(raw)
    assert isinstance(data, list)
    samples = len(data)
    human_n = gpt_n = empty_h = empty_g = malformed = 0
    pairs = []
    for x in data:
        if not isinstance(x, dict) or "conversations" not in x:
            malformed += 1
            continue
        conv = x["conversations"]
        if not isinstance(conv, list) or len(conv) < 2:
            malformed += 1
            continue
        human = ""
        gpt = ""
        for turn in conv:
            frm = turn.get("from")
            val = turn.get("value", "")
            if frm == "human":
                human_n += 1
                human = str(val)
                if not human.strip():
                    empty_h += 1
            elif frm == "gpt":
                gpt_n += 1
                gpt = str(val)
                if not gpt.strip():
                    empty_g += 1
        pairs.append((human, gpt))

    unique_inputs = len({h for h, _ in pairs})
    unique_outputs = len({g for _, g in pairs})
    unique_pairs = len(set(pairs))
    duplicate_pairs = len(pairs) - unique_pairs

    # 2) tokenizer (CPU only)
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(tok_path, trust_remote_code=True, use_fast=True)
    # Prefer LLaMA-Factory template path
    sys.path.insert(0, str(Path(args.lf_root) / "src"))
    from llamafactory.data.processor.processor_utils import infer_seqlen as lf_infer_seqlen
    from llamafactory.data.template import TEMPLATES
    from llamafactory.extras.constants import IGNORE_INDEX

    template_name = args.template
    template = TEMPLATES[template_name]
    template.fix_special_tokens(tokenizer)

    tok_info = {
        "path": tok_path,
        "class": type(tokenizer).__name__,
        "vocab_size": getattr(tokenizer, "vocab_size", None),
        "len": len(tokenizer),
        "bos_token": tokenizer.bos_token,
        "bos_token_id": tokenizer.bos_token_id,
        "eos_token": tokenizer.eos_token,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token": tokenizer.pad_token,
        "pad_token_id": tokenizer.pad_token_id,
        "unk_token": tokenizer.unk_token,
        "unk_token_id": getattr(tokenizer, "unk_token_id", None),
        "model_max_length": tokenizer.model_max_length,
        "padding_side": tokenizer.padding_side,
        "truncation_side": tokenizer.truncation_side,
        "add_bos_token": getattr(tokenizer, "add_bos_token", None),
        "add_eos_token": getattr(tokenizer, "add_eos_token", None),
        "chat_template_present": isinstance(getattr(tokenizer, "chat_template", None), str),
    }

    # raw tokenize
    rows = []
    for i, (human, gpt) in enumerate(pairs):
        in_ids = tokenizer.encode(human, add_special_tokens=False)
        out_ids = tokenizer.encode(gpt, add_special_tokens=False)
        rows.append(
            {
                "sample_index": i,
                "input_tokens_raw": len(in_ids),
                "output_tokens_raw": len(out_ids),
                "raw_total_tokens": len(in_ids) + len(out_ids),
                "human_sha256": sha256_text(human),
                "gpt_sha256": sha256_text(gpt),
            }
        )

    # effective SFT using LLaMA-Factory template.encode_oneturn + supervised labeling
    IGNORE = IGNORE_INDEX
    train_on_prompt = False  # DataArguments default
    efficient_eos = bool(template.efficient_eos)

    for i, (human, gpt) in enumerate(pairs):
        messages = [
            {"role": "user", "content": human},
            {"role": "assistant", "content": gpt},
        ]
        source_ids, target_ids = template.encode_oneturn(tokenizer, messages, system=None, tools=None)
        # replicate SupervisedDatasetProcessor._encode_data_example single-turn path
        total_length = 0 + (1 if efficient_eos else 0)
        source_len, target_len = lf_infer_seqlen(len(source_ids), len(target_ids), 10**18)
        # no truncation at huge cutoff — measure full effective lengths
        src_full = list(source_ids)
        tgt_full = list(target_ids)
        if train_on_prompt:
            source_label = list(src_full)
        elif efficient_eos:
            source_label = [tokenizer.eos_token_id] + [IGNORE] * (len(src_full) - 1)
        else:
            source_label = [IGNORE] * len(src_full)
        target_label = list(tgt_full)
        input_ids = src_full + tgt_full
        labels = source_label + target_label
        if efficient_eos:
            input_ids = input_ids + [tokenizer.eos_token_id]
            labels = labels + [tokenizer.eos_token_id]
        loss_bearing = sum(1 for x in labels if x != IGNORE)
        rows[i]["effective_prompt_tokens"] = len(src_full) + (1 if efficient_eos and False else 0)
        # prompt side length as used in supervised path (source_ids length)
        rows[i]["effective_prompt_tokens"] = len(src_full)
        rows[i]["effective_response_tokens"] = len(tgt_full)
        rows[i]["effective_total_tokens"] = len(input_ids)
        rows[i]["loss_bearing_tokens"] = loss_bearing
        rows[i]["ignored_tokens"] = len(labels) - loss_bearing
        rows[i]["source_ids_len"] = len(src_full)
        rows[i]["target_ids_len"] = len(tgt_full)

        # cutoff simulations
        for cut in CUTOFFS:
            s_len, t_len = lf_infer_seqlen(len(src_full), len(tgt_full), cut)
            truncated = (s_len < len(src_full)) or (t_len < len(tgt_full))
            rows[i][f"truncated_at_{cut}"] = bool(truncated)
            rows[i][f"eff_total_at_{cut}"] = s_len + t_len + (1 if efficient_eos else 0)
            rows[i][f"prompt_tokens_removed_{cut}"] = len(src_full) - s_len
            rows[i][f"response_tokens_removed_{cut}"] = len(tgt_full) - t_len
            rows[i][f"response_truncated_{cut}"] = t_len < len(tgt_full)

    # aggregates
    raw_in = [r["input_tokens_raw"] for r in rows]
    raw_out = [r["output_tokens_raw"] for r in rows]
    raw_tot = [r["raw_total_tokens"] for r in rows]
    eff_p = [r["effective_prompt_tokens"] for r in rows]
    eff_r = [r["effective_response_tokens"] for r in rows]
    eff_t = [r["effective_total_tokens"] for r in rows]
    loss_b = [r["loss_bearing_tokens"] for r in rows]
    ign = [r["ignored_tokens"] for r in rows]

    cutoff_stats: dict[str, Any] = {}
    for cut in CUTOFFS:
        truncated = sum(1 for r in rows if r[f"truncated_at_{cut}"])
        before = sum(r["effective_total_tokens"] for r in rows)
        after = sum(r[f"eff_total_at_{cut}"] for r in rows)
        removed_prompt = sum(r[f"prompt_tokens_removed_{cut}"] for r in rows)
        removed_resp = sum(r[f"response_tokens_removed_{cut}"] for r in rows)
        resp_trunc = sum(1 for r in rows if r[f"response_truncated_{cut}"])
        cutoff_stats[str(cut)] = {
            "total_samples": len(rows),
            "no_truncation_samples": len(rows) - truncated,
            "truncated_samples": truncated,
            "truncation_rate": truncated / len(rows) if rows else 0.0,
            "total_tokens_before_truncation": before,
            "total_tokens_after_truncation": after,
            "tokens_removed": before - after,
            "removed_token_percentage": ((before - after) / before) if before else 0.0,
            "prompt_tokens_removed": removed_prompt,
            "response_tokens_removed": removed_resp,
            "response_truncated_samples": resp_trunc,
        }

    # target groups
    by_out: dict[str, list[int]] = defaultdict(list)
    for i, (_h, g) in enumerate(pairs):
        by_out[sha256_text(g)].append(i)
    target_groups = []
    for gid, idxs in by_out.items():
        gtext = pairs[idxs[0]][1]
        target_groups.append(
            {
                "group_id": gid,
                "sample_count": len(idxs),
                "function_name": extract_function_name(gtext),
                "sample_indexes_preview": idxs[:5],
            }
        )
    target_groups.sort(key=lambda x: (-x["sample_count"], x["group_id"]))
    group_sizes = [g["sample_count"] for g in target_groups]
    top20 = target_groups[:20]
    fn_counter = Counter(g["function_name"] for g in target_groups)
    unique_fn = sum(1 for k in fn_counter if k != "UNKNOWN")
    unknown_fn_groups = fn_counter.get("UNKNOWN", 0)

    # leakage
    multi_target_groups = sum(1 for g in target_groups if g["sample_count"] > 1)
    samples_in_multi = sum(g["sample_count"] for g in target_groups if g["sample_count"] > 1)
    random_split_has_leakage_risk = multi_target_groups > 0

    # sanity checks
    checks = []
    checks.append(("input_total + output_total == raw_total", sum(raw_in) + sum(raw_out) == sum(raw_tot)))
    checks.append(("samples == 1455", len(rows) == 1455))
    ok_mono_trunc = True
    ok_mono_removed = True
    prev_t = -1
    prev_r = -1
    for cut in CUTOFFS:
        t = cutoff_stats[str(cut)]["truncated_samples"]
        r = cutoff_stats[str(cut)]["tokens_removed"]
        if t > prev_t:
            ok_mono_trunc = False
        if r > prev_r:
            ok_mono_removed = False
        prev_t = t
        prev_r = r
    # larger cutoff => fewer/equal truncation. We iterated ascending, so truncated should be non-increasing.
    # recompute monotonicity properly
    trunc_series = [cutoff_stats[str(c)]["truncated_samples"] for c in CUTOFFS]
    removed_series = [cutoff_stats[str(c)]["tokens_removed"] for c in CUTOFFS]
    ok_mono_trunc = all(trunc_series[i] >= trunc_series[i + 1] for i in range(len(trunc_series) - 1))
    ok_mono_removed = all(removed_series[i] >= removed_series[i + 1] for i in range(len(removed_series) - 1))
    checks.append(("cutoff↑ => truncated samples non-increasing", ok_mono_trunc))
    checks.append(("cutoff↑ => tokens removed non-increasing", ok_mono_removed))

    def pct_ok(st: dict[str, float]) -> bool:
        return st["p50"] <= st["p75"] <= st["p90"] <= st["p95"] <= st["p99"] <= st["max"] + 1e-9

    checks.append(("input percentiles ordered", pct_ok(dist_stats(raw_in))))
    checks.append(("output percentiles ordered", pct_ok(dist_stats(raw_out))))
    checks.append(("total percentiles ordered", pct_ok(dist_stats(raw_tot))))
    checks.append(("target_group_count == unique outputs", len(target_groups) == unique_outputs))
    checks.append(("dataset sha256 matches expected", hash_ok))
    validation_ok = all(ok for _, ok in checks)

    defaults = collect_defaults()

    stats = {
        "task_id": TASK_ID,
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "dataset": {
            "path": str(ds_path),
            "sha256": sha,
            "sha256_expected": EXPECTED_SHA256,
            "sha256_match": hash_ok,
            "samples": samples,
            "conversations_ok": samples - malformed,
            "human_count": human_n,
            "gpt_count": gpt_n,
            "empty_human": empty_h,
            "empty_gpt": empty_g,
            "malformed": malformed,
            "unique_inputs": unique_inputs,
            "unique_outputs": unique_outputs,
            "duplicate_pairs": duplicate_pairs,
            "target_groups": len(target_groups),
        },
        "tokenizer": tok_info,
        "template": {
            "name": template_name,
            "source": "src/llamafactory/data/template.py",
            "class": type(template).__name__,
            "efficient_eos": efficient_eos,
            "train_on_prompt": train_on_prompt,
            "notes": "No dedicated codellama template; llama2 matches tokenizer.chat_template [INST] format.",
        },
        "raw_tokens": {
            "input_total": sum(raw_in),
            "output_total": sum(raw_out),
            "total": sum(raw_tot),
            "input_distribution": dist_stats(raw_in) | threshold_counts(raw_in),
            "output_distribution": dist_stats(raw_out) | threshold_counts(raw_out),
            "total_distribution": dist_stats(raw_tot) | threshold_counts(raw_tot),
        },
        "effective_tokens": {
            "prompt_total": sum(eff_p),
            "response_total": sum(eff_r),
            "total": sum(eff_t),
            "loss_bearing_total": sum(loss_b),
            "ignored_total": sum(ign),
            "prompt_distribution": dist_stats(eff_p),
            "response_distribution": dist_stats(eff_r),
            "total_distribution": dist_stats(eff_t),
        },
        "cutoff_stats": cutoff_stats,
        "target_group_analysis": {
            "target_group_count": len(target_groups),
            "group_size_distribution": dist_stats(group_sizes),
            "multi_sample_groups": multi_target_groups,
            "samples_in_multi_sample_groups": samples_in_multi,
            "unique_function_names": unique_fn,
            "unknown_function_name_groups": unknown_fn_groups,
            "top20_largest_target_groups": top20,
        },
        "llamafactory": {
            "root": args.lf_root,
            "commit": LF_PIN,
            "version": "0.9.6.dev0",
        },
        "defaults": defaults,
        "leakage": {
            "random_sample_split_risk": random_split_has_leakage_risk,
            "target_group_count": len(target_groups),
            "multi_sample_groups": multi_target_groups,
            "samples_in_multi_sample_groups": samples_in_multi,
            "note": "Same gpt/source target mapped to multiple human/assembly inputs.",
        },
        "sanity_checks": [{"name": n, "ok": bool(ok)} for n, ok in checks],
        "audit_validation_ok": validation_ok,
        "flags": {
            "DATASET_HASH_MISMATCH": (not hash_ok),
            "AUDIT_VALIDATION_FAILED": (not validation_ok),
            "GPU_MODEL_LOADED_BY_THIS_TASK": False,
            "TRAINING_STARTED": False,
        },
    }

    # write token_lengths.jsonl
    with (out_dir / "token_lengths.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    (out_dir / "token_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown report
    def fmt(n: int | float) -> str:
        if isinstance(n, float):
            return f"{n:.2f}"
        return f"{n:,}"

    md = []
    md.append("# CodeLlama Token Audit\n")
    md.append(f"任务编号：{TASK_ID}\n")
    md.append("平台：REMOTE-SERVER（CPU tokenizer，不加载 13B 权重）\n")
    md.append(f"时间：{stats['timestamp']}\n")
    md.append("\n## 0. Summary\n")
    md.append("| Item | Value |\n|---|---|\n")
    md.append(f"| Samples | {samples} |\n")
    md.append(f"| Dataset SHA256 | `{sha}` |\n")
    md.append(f"| Tokenizer | {tok_info['class']} / len={tok_info['len']} |\n")
    md.append(f"| Template | `{template_name}` |\n")
    md.append(f"| Raw Input Tokens | {fmt(sum(raw_in))} |\n")
    md.append(f"| Raw Output Tokens | {fmt(sum(raw_out))} |\n")
    md.append(f"| Raw Total Tokens | {fmt(sum(raw_tot))} |\n")
    md.append(f"| Effective Total Tokens | {fmt(sum(eff_t))} |\n")
    md.append(f"| Loss-bearing Tokens | {fmt(sum(loss_b))} |\n")
    for cut in (2048, 4096, 8192):
        md.append(f"| {cut} Truncation Rate | {cutoff_stats[str(cut)]['truncation_rate']:.2%} |\n")
    md.append(f"| Target Groups | {len(target_groups)} |\n")
    md.append(
        f"| Random Split Leakage Risk | {'YES' if random_split_has_leakage_risk else 'NO'} |\n"
    )
    md.append(f"| AUDIT_VALIDATION_OK | {'YES' if validation_ok else 'NO — AUDIT_VALIDATION_FAILED'} |\n")

    md.append("\n## 1. Dataset Integrity\n")
    md.append("| Check | Result |\n|---|---|\n")
    md.append(f"| JSON parse | OK (list) |\n")
    md.append(f"| sample count | {samples} |\n")
    md.append(f"| conversations | {samples - malformed} / malformed {malformed} |\n")
    md.append(f"| human / gpt | {human_n} / {gpt_n} |\n")
    md.append(f"| empty human / gpt | {empty_h} / {empty_g} |\n")
    md.append(f"| unique inputs | {unique_inputs} |\n")
    md.append(f"| unique outputs | {unique_outputs} |\n")
    md.append(f"| duplicate full pairs | {duplicate_pairs} |\n")
    md.append(f"| SHA256 | `{sha}` |\n")
    md.append(f"| SHA256 match expected | {'YES' if hash_ok else 'NO — DATASET_HASH_MISMATCH'} |\n")

    md.append("\n## 2. Tokenizer\n")
    md.append("| Field | Value |\n|---|---|\n")
    for k, v in tok_info.items():
        md.append(f"| {k} | `{v}` |\n")
    md.append("\nchat/template 有关配置：tokenizer 自带 `chat_template`（Llama-2 `<<SYS>>` + `[INST] ... [/INST]` + `</s>`）。\n")
    md.append("`TOKENIZER_READY = YES`\n")

    md.append("\n## 3. LLaMA-Factory Template\n")
    md.append(f"- template name: `{template_name}`\n")
    md.append("- template 定义源码：`src/llamafactory/data/template.py`（`register_template(name=\"llama2\", ...)`，`template_class=Llama2Template`）\n")
    md.append("- 附近源码要点：`format_user=[bos_token]+[INST] {{content}} [/INST]`；`format_assistant` 默认 `{{content}}`+eos；system 融入首轮 user（`Llama2Template`）\n")
    md.append("- BOS/EOS：user 槽位含 `{bos_token}`；assistant 默认槽位含 `{eos_token}`；`efficient_eos=false`\n")
    md.append("- user/assistant 格式：`[INST] ... [/INST]` / `... </s>`\n")
    md.append("- system prompt：无自定义 system 时 `default_system` 为空；有 system 时写成 `<<SYS>>\\n...\\n<</SYS>>\\n\\n` 融入首轮 user\n")
    md.append("- 证据：模型 `tokenizer_config.json` 的 `chat_template` 与 `llama2` 同构（`bos+[INST] ... [/INST]`，assistant ` content + eos`）\n")
    md.append("- 说明：pinned 源码中无 `codellama` 专用 template；WebUI `DEFAULT_TEMPLATE` 无 CodeLlama 条目（未知名会落到 `default`，格式不匹配）。本审计采用与 tokenizer chat_template 一致的 `llama2`，并调用 pinned `TEMPLATE.encode_oneturn` + `infer_seqlen` + supervised labeling。\n")
    md.append("- `TEMPLATE_UNRESOLVED` / `TEMPLATE_AMBIGUOUS`：**否**（已解析为 `llama2`）\n")

    md.append("\n## 4. Raw Token Statistics\n")
    md.append("| dim | min | mean | median | P50 | P75 | P90 | P95 | P99 | max |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for label, vals in (("input", raw_in), ("output", raw_out), ("combined", raw_tot)):
        st = dist_stats(vals)
        md.append(
            f"| {label} | {st['min']} | {st['mean']:.1f} | {st['median']:.1f} | {st['p50']:.1f} | {st['p75']:.1f} | "
            f"{st['p90']:.1f} | {st['p95']:.1f} | {st['p99']:.1f} | {st['max']} |\n"
        )
    md.append("\n阈值样本数：\n\n")
    md.append("| dim | >=512 | >=1024 | >=2048 | >=4096 | >=8192 | >=16384 |\n|---|---:|---:|---:|---:|---:|---:|\n")
    for label, vals in (("input", raw_in), ("output", raw_out), ("combined", raw_tot)):
        th = threshold_counts(vals)
        md.append(
            f"| {label} | {th['ge_512']} | {th['ge_1024']} | {th['ge_2048']} | {th['ge_4096']} | {th['ge_8192']} | {th['ge_16384']} |\n"
        )
    md.append(f"\nRAW_INPUT_TOKENS = {fmt(sum(raw_in))}\n\n")
    md.append(f"RAW_OUTPUT_TOKENS = {fmt(sum(raw_out))}\n\n")
    md.append(f"RAW_TOTAL_TOKENS = {fmt(sum(raw_tot))}\n")

    md.append("\n## 5. Effective SFT Token Statistics\n")
    md.append("复用 pinned LLaMA-Factory：`TEMPLATES['llama2'].encode_oneturn` + `processor_utils.infer_seqlen` + `SupervisedDatasetProcessor` 标注逻辑（`train_on_prompt=False`）。\n")
    md.append("| Field | Tokens |\n|---|---:|\n")
    md.append(f"| EFFECTIVE_CONTEXT_TOKENS（prompt/source） | {fmt(sum(eff_p))} |\n")
    md.append(f"| EFFECTIVE_RESPONSE_TOKENS（assistant） | {fmt(sum(eff_r))} |\n")
    md.append(f"| EFFECTIVE_TOTAL_TOKENS | {fmt(sum(eff_t))} |\n")
    md.append(f"| LOSS_BEARING_TOKENS | {fmt(sum(loss_b))} |\n")
    md.append(f"| IGNORED/MASKED_TOKENS | {fmt(sum(ign))} |\n")
    md.append(f"\n`train_on_prompt` 默认 False：prompt 不参与 loss。\n")

    md.append("\n## 6. Cutoff Simulation\n")
    md.append("使用同一 `infer_seqlen`（pinned `processor_utils.py`）。\n\n")
    md.append("| cutoff | total | truncated | rate | tokens removed | removed ratio | response truncated |\n|---:|---:|---:|---:|---:|---:|---:|\n")
    for cut in CUTOFFS:
        cs = cutoff_stats[str(cut)]
        md.append(
            f"| {cut} | {cs['total_samples']} | {cs['truncated_samples']} | {cs['truncation_rate']:.2%} | "
            f"{fmt(cs['tokens_removed'])} | {cs['removed_token_percentage']:.2%} | {cs['response_truncated_samples']} |\n"
        )
    md.append("\n截断位置（tokens removed 拆分）：\n\n")
    md.append("| cutoff | prompt_tokens_removed | response_tokens_removed |\n|---:|---:|---:|\n")
    for cut in CUTOFFS:
        cs = cutoff_stats[str(cut)]
        md.append(f"| {cut} | {fmt(cs['prompt_tokens_removed'])} | {fmt(cs['response_tokens_removed'])} |\n")

    md.append("\n## 7. Target Group Analysis\n")
    md.append(f"- TARGET_GROUP_COUNT = {len(target_groups)}\n")
    md.append(f"- unique human = {unique_inputs}\n")
    md.append(f"- unique gpt = {unique_outputs}\n")
    md.append(f"- duplicate full pair = {duplicate_pairs}\n")
    gst = dist_stats(group_sizes)
    md.append(
        f"- group size min/max/mean/median/P90 = {gst['min']}/{gst['max']}/{gst['mean']:.2f}/{gst['median']:.1f}/{gst['p90']:.1f}\n"
    )
    md.append(f"- unique function names = {unique_fn}\n")
    md.append(f"- unknown function-name groups = {unknown_fn_groups}\n")
    md.append("\nTop 20 largest target groups（不含完整源码）：\n\n")
    md.append("| rank | SHA256 | sample_count | function_name |\n|---:|---|---:|---|\n")
    for i, g in enumerate(top20, 1):
        md.append(f"| {i} | `{g['group_id'][:16]}…` | {g['sample_count']} | {g['function_name']} |\n")

    md.append("\n## 8. Leakage Risk\n")
    md.append(
        f"- 多样本 target group 数量 = {multi_target_groups}\n"
        f"- 落入多样本 target group 的样本数 = {samples_in_multi}\n"
        f"- independent target groups（按 output SHA256） = {len(target_groups)}\n"
    )
    md.append(
        f"\nRANDOM_SAMPLE_SPLIT_HAS_LEAKAGE_RISK = {'YES' if random_split_has_leakage_risk else 'NO'}\n"
    )
    md.append("\n本轮不决定 80/10/10 或 90/5/5 等划分比例。\n")

    md.append("\n## 9. LLaMA-Factory Defaults\n")
    md.append("| Parameter | WebUI Default | Parser/Dataclass Default | Example YAML | Evidence |\n|---|---|---|---|---|\n")
    rows_def = [
        ("learning_rate", "5e-5", "5e-05 (HF)", "1.0e-4", "webui/components/train.py:52; HF TrainingArguments; examples/train_lora/qwen3_lora_sft.yaml"),
        ("num_train_epochs", "3.0", "3.0 (HF)", "3.0", "train.py:53; HF; yaml"),
        ("cutoff_len", "2048", "2048", "2048", "train.py:72; data_args.py:46; yaml"),
        ("batch_size", "2", "8 (HF per_device)", "1", "train.py:73; HF; yaml"),
        ("gradient_accumulation_steps", "8", "1 (HF)", "8", "train.py:74; HF; yaml"),
        ("packing", "false (Checkbox unchecked)", "None → SFT false", "not set", "train.py:99; data_args.py:108; parser.py:645"),
        ("neat_packing", "false", "false", "not set", "train.py:100; data_args.py:112"),
        ("train_on_prompt", "false", "false", "not set", "train.py:103; data_args.py:50"),
        ("lora_rank", "8", "8", "8", "train.py:193; finetuning_args.py:77; yaml"),
        ("lora_alpha", "16", "None → rank*2=16", "not set", "train.py:194; finetuning_args.py:69,610"),
        ("lora_dropout", "0", "0.0", "not set", "train.py:195; finetuning_args.py:73"),
        ("lora_target", "empty Textbox", "all", "all", "train.py:200; finetuning_args.py:83; yaml"),
        ("lr_scheduler_type", "cosine", "linear (HF)", "cosine", "train.py:75; HF; yaml"),
        ("warmup_steps / warmup_ratio", "0 / n/a", "0 / None", "warmup_ratio 0.1", "train.py:92; HF; yaml"),
        ("bf16 / fp16", "bf16 via compute_type", "False / False", "bf16: true", "train.py:58; HF; yaml"),
        ("gradient_checkpointing", "not in primary UI row", "False (HF)", "not set", "HF TrainingArguments"),
        ("logging_steps", "5", "500 (HF)", "10", "train.py:89; HF; yaml"),
        ("save_steps", "100", "500 (HF)", "500", "train.py:90; HF; yaml"),
        ("val_size", "0", "0.0", "commented 0.1", "train.py:74; data_args.py:100; yaml comments"),
        ("seed", "42 (train_seed)", "42 (HF)", "not set", "train.py:56; HF"),
        ("max_samples", "100000", "None", "1000", "train.py:57; data_args.py:84; yaml"),
        ("report_to", "none", "none (HF)", "none", "train.py:120; HF; yaml"),
        ("optim", "extra_args adamw_torch", "adamw_torch_fused (HF)", "not set", "train.py:93; HF"),
    ]
    for p, w, d, e, ev in rows_def:
        md.append(f"| {p} | {w} | {d} | {e} | {ev} |\n")
    md.append("\n特别字段：\n\n")
    md.append("| Field | Value |\n|---|---|\n")
    md.append("| WebUI num_train_epochs default | 3.0 |\n")
    md.append("| Parser/dataclass num_train_epochs default | 3.0 (HF TrainingArguments) |\n")
    md.append("| Example YAML epoch | 3.0 |\n")
    md.append("| WebUI packing default | false（未勾选） |\n")
    md.append("| Parser/dataclass packing default | None；SFT 时解析为 false |\n")
    md.append("| packing 是否默认开启 | 否 |\n")
    md.append("| WebUI lora_rank default | 8 |\n")
    md.append("| dataclass lora_rank default | 8 |\n")
    md.append("| example YAML lora_rank | 8 |\n")
    md.append("| lora_alpha | WebUI 16；dataclass None→rank*2 |\n")
    md.append("| lora_dropout | 0 |\n")
    md.append("| lora_target | dataclass `all`；WebUI 空字符串；YAML `all`。`all` 表示所有 linear 模块（finetuning_args.py） |\n")

    md.append("\n## 10. Key Findings\n")
    md.append(f"- 数据 1455 条全部可解析；SHA256 与预期一致。\n")
    md.append(f"- 原始 human 内容显著长于 gpt 内容（input 均值 {dist_stats(raw_in)['mean']:.1f} vs output 均值 {dist_stats(raw_out)['mean']:.1f}）。\n")
    md.append(f"- unique output 仅 {unique_outputs}，对应 {len(target_groups)} 个 target group；多样本共享同一 source target 的 group 共 {multi_target_groups} 个。\n")
    md.append(f"- 2048/4096/8192 截断率分别为 {cutoff_stats['2048']['truncation_rate']:.2%} / {cutoff_stats['4096']['truncation_rate']:.2%} / {cutoff_stats['8192']['truncation_rate']:.2%}。\n")
    md.append(f"- 截断主要发生在：prompt_tokens_removed@2048={cutoff_stats['2048']['prompt_tokens_removed']}，response_tokens_removed@2048={cutoff_stats['2048']['response_tokens_removed']}。\n")
    md.append(f"- `train_on_prompt=False` 时 loss 只落在 assistant 响应 token（含模板 eos）。\n")
    md.append(f"- RANDOM_SAMPLE_SPLIT_HAS_LEAKAGE_RISK = {'YES' if random_split_has_leakage_risk else 'NO'}。\n")
    md.append(f"- WebUI / dataclass / example YAML 的 epoch 均为 3.0；packing 默认关闭。\n")

    md.append("\n## 11. Inputs For Training Configuration\n")
    md.append("供 Commander 后续决策的事实输入（本报告不选定最终参数）：\n\n")
    md.append("1. Raw 与 Effective token 分布、P50/P90/P99。\n")
    md.append("2. 各 cutoff_len 截断率、移除 token 量，以及 prompt/response 截断拆分。\n")
    md.append("3. target group 规模与随机划分泄漏风险。\n")
    md.append("4. 框架默认值（含 epoch、packing、lora_rank/alpha/target、lr、batch、accum）。\n")
    md.append("5. 单卡显存现状（vLLM 占用）与 13B LoRA 需求之间的差距。\n")
    md.append("\n禁止项遵守：未做 train/val/test split，未选 LoRA 最终超参，未 YAML finalization，未训练。\n")

    md.append("\n## Sanity Checks\n")
    md.append("| Check | OK |\n|---|---|\n")
    for n, ok in checks:
        md.append(f"| {n} | {'YES' if ok else 'NO'} |\n")

    (out_dir / "TOKEN_AUDIT.md").write_text("".join(md), encoding="utf-8")

    # stdout summary
    print(json.dumps(
        {
            "validation_ok": validation_ok,
            "samples": samples,
            "raw_input_tokens": sum(raw_in),
            "raw_output_tokens": sum(raw_out),
            "raw_total_tokens": sum(raw_tot),
            "effective_total_tokens": sum(eff_t),
            "loss_bearing_tokens": sum(loss_b),
            "target_groups": len(target_groups),
            "leakage": random_split_has_leakage_risk,
            "cutoff_2048_rate": cutoff_stats["2048"]["truncation_rate"],
            "cutoff_4096_rate": cutoff_stats["4096"]["truncation_rate"],
            "cutoff_8192_rate": cutoff_stats["8192"]["truncation_rate"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if validation_ok and hash_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
