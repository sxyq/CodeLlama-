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

