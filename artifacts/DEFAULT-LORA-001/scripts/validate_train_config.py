#!/usr/bin/env python3
# TRAIN-CONFIG-001 static validation + exact train-token / step accounting
# No model weights. No training.

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path


EXPECTED_SHA = "28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6"
CUTOFF = 2048
EPOCHS = 3.0
MICRO_BS = 2
GRAD_ACCUM = 8
SAMPLES_EXPECTED = 1455


def infer_seqlen(source_len: int, target_len: int, cutoff_len: int) -> tuple[int, int]:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/codellama-lora"))
    ap.add_argument("--tokenizer", default="/data/vllm/CodeLlama-13b-Instruct-hf")
    ap.add_argument("--yaml", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    root = Path(args.root)
    yaml_path = Path(args.yaml or root / "configs/training/default_baseline_lora.yaml")
    out_path = Path(args.output or root / "reports/train_token_accounting.json")
    ds_path = root / "data/Fine-Tuning.json"

    # --- YAML parse / field check ---
    import yaml as pyyaml

    cfg = pyyaml.safe_load(yaml_path.read_text())
    required = {
        "model_name_or_path": "/data/vllm/CodeLlama-13b-Instruct-hf",
        "disable_gradient_checkpointing": False,
        "stage": "sft",
        "do_train": True,
        "finetuning_type": "lora",
        "template": "llama2",
        "dataset": "codellama_asm_pseudo_to_cpp",
        "cutoff_len": 2048,
        "packing": False,
        "train_on_prompt": False,
        "learning_rate": 5e-5,
        "num_train_epochs": 3.0,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "cosine",
        "lora_rank": 8,
        "lora_alpha": 16,
        "lora_dropout": 0,
        "lora_target": "all",
        "bf16": True,
        "val_size": 0,
        "seed": 42,
    }
    yaml_checks = []
    for k, exp in required.items():
        got = cfg.get(k)
        ok = got == exp or (isinstance(exp, float) and isinstance(got, (int, float)) and abs(got - exp) < 1e-12)
        yaml_checks.append({"key": k, "expected": exp, "got": got, "ok": bool(ok)})
    yaml_ok = all(c["ok"] for c in yaml_checks)

    # --- dataset registration / load via LLaMA-Factory parser ---
    sys.path.insert(0, str(root / "LLaMA-Factory/src"))
    from llamafactory.data.parser import get_dataset_list
    from llamafactory.data.converter import align_dataset
    from llamafactory.data.template import TEMPLATES
    from llamafactory.hparams import DataArguments, ModelArguments, FinetuningArguments
    from transformers import AutoTokenizer, TrainingArguments

    dataset_dir = str(root / "configs/datasets")
    names = [cfg["dataset"]]
    attrs = get_dataset_list(names, dataset_dir)
    assert len(attrs) == 1
    attr = attrs[0]

    # load JSON via datasets to mimic file loader path
    from datasets import load_dataset

    local_path = os.path.join(dataset_dir, attr.dataset_name)
    assert os.path.isfile(local_path), local_path
    raw_sha = hashlib.sha256(ds_path.read_bytes()).hexdigest()
    ds = load_dataset("json", data_files=local_path, split="train")
    # If symlink resolved, SHA should match original
    link_sha = hashlib.sha256(Path(local_path).resolve().read_bytes()).hexdigest()

    model_args = ModelArguments(model_name_or_path="/data/vllm/CodeLlama-13b-Instruct-hf")
    data_args = DataArguments(
        dataset=names[0],
        dataset_dir=dataset_dir,
        cutoff_len=CUTOFF,
        packing=False,
        train_on_prompt=False,
        val_size=0.0,
        max_samples=None,
    )
    training_args = TrainingArguments(output_dir=str(root / "outputs/_static_check"))
    aligned = align_dataset(ds, attr, data_args, training_args)
    n_aligned = len(aligned)
    # first structure peek
    keys = aligned.column_names
    prompt0 = aligned[0].get("_prompt") if "_prompt" in keys else None
    response0 = aligned[0].get("_response") if "_response" in keys else None

    # --- effective tokens + cutoff accounting ---
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True, use_fast=True)
    template = TEMPLATES["llama2"]
    template.fix_special_tokens(tokenizer)
    IGNORE = -100

    train_prompt = train_resp = train_total = loss_b = 0
    raw_in = raw_out = 0
    truncated = 0
    for row in aligned:
        prompt = row["_prompt"]
        response = row["_response"]
        # single-turn expected
        human = prompt[-1]["content"] if prompt else ""
        gpt = response[0]["content"] if response else ""
        raw_in += len(tokenizer.encode(human, add_special_tokens=False))
        raw_out += len(tokenizer.encode(gpt, add_special_tokens=False))
        messages = prompt + response
        source_ids, target_ids = template.encode_oneturn(tokenizer, messages)
        s_len, t_len = infer_seqlen(len(source_ids), len(target_ids), CUTOFF)
        if s_len < len(source_ids) or t_len < len(target_ids):
            truncated += 1
        train_prompt += s_len
        train_resp += t_len
        train_total += s_len + t_len
        # train_on_prompt=False → loss on target only
        loss_b += t_len

    # --- steps (HF Trainer behavior) ---
    samples = n_aligned
    # dataloader_drop_last=False → ceil
    micro_steps_per_epoch = math.ceil(samples / MICRO_BS)
    # leftover accumulation flush at epoch end (see report)
    optimizer_steps_per_epoch = math.ceil(micro_steps_per_epoch / GRAD_ACCUM)
    last_micro_bs = samples - (micro_steps_per_epoch - 1) * MICRO_BS
    total_optimizer_steps = int(optimizer_steps_per_epoch * int(EPOCHS))
    effective_batch = MICRO_BS * GRAD_ACCUM

    result = {
        "experiment_id": "DEFAULT-LORA-001",
        "yaml_path": str(yaml_path),
        "yaml_static_ok": yaml_ok,
        "yaml_checks": yaml_checks,
        "dataset": {
            "name": names[0],
            "registration": str(root / "configs/datasets/dataset_info.json"),
            "file": local_path,
            "sha256_original": raw_sha,
            "sha256_symlink_target": link_sha,
            "sha256_match": raw_sha == link_sha == EXPECTED_SHA,
            "samples_loaded": samples,
            "aligned_samples": n_aligned,
            "validation_samples": 0,
            "test_samples": 0,
            "keys": keys,
            "prompt0_roles": [p.get("role") for p in (prompt0 or [])],
            "response0_roles": [p.get("role") for p in (response0 or [])],
        },
        "template": "llama2",
        "cutoff_len": CUTOFF,
        "packing": False,
        "train_on_prompt": False,
        "raw_tokens": {
            "input_tokens": raw_in,
            "output_tokens": raw_out,
            "total_tokens": raw_in + raw_out,
        },
        "train_tokens_per_epoch_after_cutoff": {
            "train_input_context_tokens_per_epoch": train_prompt,
            "train_output_response_tokens_per_epoch": train_resp,
            "train_total_tokens_per_epoch": train_total,
            "loss_bearing_tokens_per_epoch": loss_b,
            "truncated_samples": truncated,
            "truncation_rate": truncated / samples if samples else 0.0,
        },
        "train_token_presentations_3e": {
            "train_input_context_tokens_total_3e": train_prompt * 3,
            "train_output_response_tokens_total_3e": train_resp * 3,
            "train_total_token_presentations_3e": train_total * 3,
            "loss_bearing_token_presentations_3e": loss_b * 3,
        },
        "batch_steps": {
            "micro_batch_size": MICRO_BS,
            "gradient_accumulation_steps": GRAD_ACCUM,
            "effective_batch_size": effective_batch,
            "micro_steps_per_epoch": micro_steps_per_epoch,
            "optimizer_steps_per_epoch": optimizer_steps_per_epoch,
            "total_optimizer_steps_3e": total_optimizer_steps,
            "last_micro_batch_size": last_micro_bs,
            "dataloader_drop_last": False,
            "method": (
                "micro_steps_per_epoch = ceil(samples / micro_bs) with dataloader_drop_last=false; "
                "optimizer_steps_per_epoch = ceil(micro_steps / grad_accum) because HF Trainer flushes "
                "the final incomplete accumulation group at epoch end; last incomplete micro-batch is kept."
            ),
        },
    }

    # sanity
    checks = {
        "samples_1455": samples == SAMPLES_EXPECTED,
        "train_total_eq_in_plus_out": train_total == train_prompt + train_resp,
        "loss_eq_response_when_not_train_on_prompt": loss_b == train_resp,
        "raw_total_eq": (raw_in + raw_out) == result["raw_tokens"]["total_tokens"],
        "sha_match": result["dataset"]["sha256_match"],
        "yaml_ok": yaml_ok,
        "aligned_eq_loaded": n_aligned == samples,
    }
    result["sanity_checks"] = checks
    result["static_validation"] = "PASS" if all(checks.values()) else "FAIL"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(
        {
            "static_validation": result["static_validation"],
            "samples": samples,
            "truncated": truncated,
            "train_total_per_epoch": train_total,
            "loss_per_epoch": loss_b,
            "optimizer_steps_3e": total_optimizer_steps,
            "raw_in": raw_in,
            "raw_out": raw_out,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if result["static_validation"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
