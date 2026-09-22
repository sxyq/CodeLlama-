from pathlib import Path

p = Path("/home/syy/codellama-lora/scripts/collect_training_metrics.py")
t = p.read_text()
if "peak_gpu_memory_used_mib" in t:
    print("ALREADY_ENHANCED")
else:
    inject = Path("/home/syy/codellama-lora/scripts/_gpu_summary_snippet.py").read_text()
    t = t.replace("def find_peak_gpu(", inject + "\ndef find_peak_gpu(", 1)
    old = '"peak_gpu_memory": find_peak_gpu(log_dir),'
    new = (
        '"peak_gpu_memory": find_peak_gpu(log_dir),\n'
        '        "gpu_monitor_summary": summarize_gpu_monitor(log_dir / "gpu_monitor.csv"),'
    )
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("ENHANCED")
